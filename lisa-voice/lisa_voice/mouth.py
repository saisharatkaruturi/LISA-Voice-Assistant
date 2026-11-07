"""LISA voice engine: speech.

Copyright (C) 2026 Sharat. All rights reserved.

Two worker threads form a pipeline: one renders sentences with Kokoro while
the other plays the previous one, so she speaks continuously as the reply
streams in. Every queued item carries a generation number; an interrupt
bumps the generation, and anything from an older one is thrown away.
"""
import queue
import re
import threading
import time

import numpy as np
import sounddevice as sd

from lisa_voice.log import log

RATE = 24000
BLOCK = RATE // 15               # one face waveform frame per block
_END = object()                  # marks the end of one sentence's audio


def speakable(text: str) -> str:
    """Strip the things that read badly aloud."""
    text = re.sub(r"https?://\S+", "a link", text)
    text = re.sub(r"`+", "", text)
    text = re.sub(r"^\s*(#+|[-*+•]|\d+[.)])\s+", "", text, flags=re.M)
    text = re.sub(r"[*_~|>#]", "", text)
    return re.sub(r"\s+", " ", text).strip()


class Sentences:
    """Cuts streaming text into whole sentences as soon as each one ends."""
    _BOUNDARY = re.compile(r"(.+?[.!?…:;]+[\"')\]]*)(\s+|$)|(.+?)\n+")

    def __init__(self):
        self._buf = ""

    def feed(self, text: str) -> list:
        self._buf += text
        out = []
        while True:
            self._buf = self._buf.lstrip()
            m = self._BOUNDARY.match(self._buf)
            # Need text after the boundary to know it really is one,
            # e.g. "3." in "3.5" or "Dr." mid-word streaming.
            if not m or m.end() >= len(self._buf):
                break
            sentence = (m.group(1) or m.group(3) or "").strip()
            self._buf = self._buf[m.end():]
            if sentence:
                out.append(sentence)
        return out

    def flush(self) -> list:
        rest, self._buf = self._buf.strip(), ""
        return [rest] if rest else []


class Mouth:
    def __init__(self, cfg: dict, face):
        self.cfg = cfg
        self.face = face
        self.pipe = None
        self._gen = 0
        self._pending = 0                # sentences queued but not yet heard
        self._lock = threading.Lock()
        self._text_q = queue.Queue()
        self._audio_q = queue.Queue(maxsize=64)
        self._out = None

    def load(self) -> None:
        from kokoro import KPipeline
        voice = self.cfg["voice"]
        log(f"[mouth] loading kokoro (voice {voice})...")
        self.pipe = KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M")
        for _ in self.pipe("Ready.", voice=voice):       # warm the voice
            pass
        threading.Thread(target=self._render_loop, daemon=True).start()
        threading.Thread(target=self._play_loop, daemon=True).start()
        log("[mouth] ready")

    # ---- control ----
    def say(self, text: str) -> None:
        text = speakable(text)
        if not text:
            return
        with self._lock:
            self._pending += 1
            self._text_q.put((self._gen, text))

    def interrupt(self) -> None:
        with self._lock:
            self._gen += 1
            self._pending = 0
            for q in (self._text_q, self._audio_q):
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break
        self.face.quiet()

    @property
    def busy(self) -> bool:
        return self._pending > 0

    def wait(self, timeout: float = 60.0) -> None:
        end = time.monotonic() + timeout
        while self.busy and time.monotonic() < end:
            time.sleep(0.05)

    def _current(self, gen: int) -> bool:
        return gen == self._gen

    # ---- workers ----
    def _render_loop(self) -> None:
        while True:
            gen, text = self._text_q.get()
            if not self._current(gen):
                continue
            try:
                for result in self.pipe(text, voice=self.cfg["voice"],
                                        speed=self.cfg["speed"]):
                    if not self._current(gen):
                        break
                    if result.audio is not None:
                        audio = np.asarray(result.audio, dtype=np.float32)
                        self._audio_q.put((gen, audio))
            except Exception as e:
                log(f"[mouth] could not render '{text[:40]}': {e}")
            self._audio_q.put((gen, _END))

    def _play_loop(self) -> None:
        while True:
            try:
                gen, audio = self._audio_q.get(timeout=0.5)
            except queue.Empty:
                self._idle_output()
                continue
            if not self._current(gen):
                continue
            if audio is _END:
                with self._lock:
                    if self._current(gen) and self._pending > 0:
                        self._pending -= 1
                continue
            self._play(gen, audio)

    def _play(self, gen: int, audio: np.ndarray) -> None:
        try:
            if self._out is None:
                self._out = sd.OutputStream(samplerate=RATE, channels=1,
                                            dtype="float32")
            if not self._out.active:
                self._out.start()
            for start in range(0, len(audio), BLOCK):
                if not self._current(gen):
                    return
                block = audio[start:start + BLOCK]
                self.face.wave(block)
                self._out.write(block.reshape(-1, 1))
        except Exception as e:
            log(f"[mouth] speaker error: {e}")
            if self._out is not None:
                try:
                    self._out.close()
                except Exception:
                    pass
            self._out = None             # reopened on the next sentence

    def _idle_output(self) -> None:
        # Release the speaker between replies.
        if self._out is not None and self._out.active and not self.busy:
            try:
                self._out.stop()
            except Exception:
                self._out = None
            self.face.quiet()
