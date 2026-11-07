"""LISA voice engine: hearing.

Copyright (C) 2026 Sharat. All rights reserved.

The microphone stays open with a short rolling pre-roll, so the first word
isn't clipped when the talk key goes down. Audio is kept only in memory and
only while the key is held. Speech is transcribed locally by faster-whisper.
"""
import collections
import re
import threading

import numpy as np
import sounddevice as sd

from lisa_voice.log import log

RATE = 16000
BLOCK = 480                      # 30 ms
PREROLL_BLOCKS = 8               # ~0.25 s kept from before the key press
MIN_SECONDS = 0.3                # shorter than this isn't speech
NO_SPEECH_LIMIT = 0.6            # Whisper's own "this is not speech" score
_MARKERS = re.compile(r"[\[\(][^\]\)]*[\]\)]")   # [BLANK_AUDIO], (coughs)...


def _words(text: str) -> set:
    return set(re.findall(r"[a-z']+", text.lower()))


class Ears:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.model = None
        self._stream = None
        self._lock = threading.Lock()
        self._recording = False
        self._frames = []
        self._skip = 0                   # samples still to discard
        self._preroll = collections.deque(maxlen=PREROLL_BLOCKS)

    # ---- the model ----
    def load(self) -> None:
        from faster_whisper import WhisperModel
        path, compute = self.cfg["hearing_model"], self.cfg["hearing_compute"]
        device = self.cfg["hearing_device"]
        log(f"[ears] loading {path} ({device}/{compute})...")
        try:
            self.model = WhisperModel(path, device=device, compute_type=compute)
            self._run(np.zeros(RATE // 10, dtype=np.float32))
        except Exception as e:
            if device == "cpu":
                raise
            # "auto" can pick a GPU whose runtime won't actually load;
            # that only shows on the first real transcription, so prove it now.
            log(f"[ears] {device} failed ({str(e)[:80]}); using the CPU")
            self.model = WhisperModel(path, device="cpu", compute_type=compute)
            self._run(np.zeros(RATE // 10, dtype=np.float32))
        log("[ears] ready")

    def _run(self, audio: np.ndarray) -> str:
        hot = self.cfg.get("hotwords") or None
        # Greedy decoding: same transcript as the default 5-way beam search
        # on this laptop, minus the multi-second (once 74 s) stalls. The
        # built-in voice detector skips non-speech before decoding, so an
        # empty press costs under a second instead of ~6.
        segments, _ = self.model.transcribe(
            audio, language="en", temperature=0.0, hotwords=hot,
            beam_size=1, without_timestamps=True,
            condition_on_previous_text=False, vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300})
        # Hotwords prime the decoder, so on silence or noise Whisper hands
        # the hint back as if it had been said. Drop what it scores as
        # non-speech, and any result made only of hint words.
        text = "".join(s.text for s in segments
                       if s.no_speech_prob < NO_SPEECH_LIMIT)
        text = _MARKERS.sub("", text).strip()
        if hot and _words(text) and _words(text) <= _words(hot):
            return ""
        return text

    def transcribe(self, pcm: np.ndarray) -> str:
        if len(pcm) < RATE * MIN_SECONDS:
            return ""
        return self._run(pcm.astype(np.float32) / 32768.0)

    # ---- the microphone ----
    def _device(self):
        want = (self.cfg.get("mic_device") or "").strip().lower()
        if not want:
            return None
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0 and want in dev["name"].lower():
                return i
        log(f"[ears] mic '{want}' not found; using the default input")
        return None

    def _on_audio(self, block, _frames, _time, _status) -> None:
        chunk = block[:, 0].copy()
        with self._lock:
            if not self._recording:
                self._preroll.append(chunk)
            elif self._skip > 0:
                self._skip -= len(chunk)
            else:
                self._frames.append(chunk)

    def open_mic(self) -> None:
        if self._stream is not None and self._stream.active:
            return
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
        self._stream = sd.InputStream(samplerate=RATE, channels=1, dtype="int16",
                                      blocksize=BLOCK, device=self._device(),
                                      callback=self._on_audio)
        self._stream.start()

    def start(self) -> None:
        try:
            self.open_mic()          # reopens if the device dropped
        except Exception as e:
            log(f"[ears] microphone unavailable: {e}")
        with self._lock:
            self._frames = list(self._preroll)
            self._skip = 0
            self._recording = True

    def restart(self, skip_seconds: float = 0.0) -> None:
        """Throw away everything recorded so far, plus the next
        skip_seconds. Used when Sharat interrupts her: until then the mic
        was hearing LISA's own voice from the speakers, and the speakers
        keep playing a fraction of a second after she's told to stop."""
        with self._lock:
            self._frames = []
            self._skip = int(skip_seconds * RATE)

    def stop(self) -> np.ndarray:
        with self._lock:
            self._recording = False
            frames, self._frames = self._frames, []
        if not frames:
            return np.zeros(0, dtype=np.int16)
        return np.concatenate(frames)

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.close()
            except Exception:
                pass
