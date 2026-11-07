"""LISA voice engine: the conversation loop.

Copyright (C) 2026 Sharat. All rights reserved.

Run with:  python -m lisa_voice

Everything that happens (key presses, typed lines, interrupt timers) becomes
an event on one asyncio queue, handled in order on one loop. The brain's
reply streams into the mouth sentence by sentence while it is still being
written, so she starts talking within a second or two.
"""
import asyncio
import re
import sys
import threading
import time

from lisa_voice import settings
from lisa_voice.ears import PREROLL_BLOCKS, BLOCK, RATE, Ears
from lisa_voice.face import Face
from lisa_voice.log import log
from lisa_voice.mind import Mind
from lisa_voice.mouth import Mouth, Sentences
from lisa_voice.talk_key import TalkKey


def time_of_day() -> str:
    hour = time.localtime().tm_hour
    return "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"


def _plain(text: str) -> str:
    return " ".join(re.findall(r"[a-z']+", text.lower()))


# After an interrupt the speakers keep playing for a moment (the audio
# device's own buffer); that tail is dropped so she doesn't hear herself.
SPEAKER_TAIL = 0.25


class Voice:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.tap = float(cfg["tap_seconds"])
        self.face = Face()
        self.ears = Ears(cfg)
        self.mouth = Mouth(cfg, self.face)
        self.mind = Mind(cfg)
        self.events = None
        self.loop = None
        self.key = None
        self.press = None            # the key press in progress, if any
        self.turn = None             # the brain turn in progress, if any
        self.turn_id = 0             # bumped to silence a superseded turn

    # ---- plumbing ----
    def _emit(self, *event) -> None:
        self.loop.call_soon_threadsafe(self.events.put_nowait, event)

    def _read_typing(self) -> None:
        for line in sys.stdin:
            if line.strip():
                self._emit("typed", line.strip())

    def _turn_running(self) -> bool:
        return self.turn is not None and not self.turn.done()

    def _say(self, text: str) -> None:
        log(f"[lisa]   {text}")
        self.mouth.say(text)

    # ---- startup and the main loop ----
    async def run(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.events = asyncio.Queue()
        self.face.state("idle")
        self.face.quiet()
        self.face.clear_alert()
        cfg = self.cfg
        log(f"[lisa-voice] up - agent={cfg['name']} dir={cfg['agent_dir']} "
            f"model={cfg['model']} talk key={cfg['talk_key']} "
            f"(say '{cfg['hangup_phrases'][0]}' to hang up)")

        await asyncio.gather(asyncio.to_thread(self.ears.load),
                             asyncio.to_thread(self.mouth.load),
                             self.mind.connect())
        self.ears.open_mic()
        self.key = TalkKey(cfg["talk_key"],
                           lambda: self._emit("down", time.monotonic()),
                           lambda: self._emit("up", time.monotonic()))
        self.key.start()
        threading.Thread(target=self._read_typing, daemon=True).start()
        log(f"[lisa-voice] ready - hold {cfg['talk_key']} to talk, or type here")
        self._say(cfg["greeting"].format(time_of_day=time_of_day()))

        try:
            while True:
                kind, value = await self.events.get()
                if kind == "down":
                    self._key_down(value)
                elif kind == "confirm":
                    await self._confirm_interrupt(value)
                elif kind == "up":
                    if await self._key_up(value):
                        break
                elif kind == "typed":
                    if await self._heard(value):
                        break
        finally:
            await self._shutdown()

    async def _shutdown(self) -> None:
        if self.key is not None:
            self.key.stop()
        self.ears.close()
        await self.mind.close()
        self.face.quiet()
        self.face.state("idle")
        log("[lisa-voice] voice line closed")

    # ---- the talk key ----
    def _key_down(self, at: float) -> None:
        busy = self.mouth.busy or self._turn_running()
        self.press = {"at": at, "busy": busy, "confirmed": not busy}
        self.ears.start()
        if busy:
            # Only a real hold interrupts her; a stray tap is ignored.
            press = self.press
            self.loop.call_later(self.tap, self.events.put_nowait,
                                 ("confirm", press))
        else:
            self.face.state("listening")

    async def _confirm_interrupt(self, press: dict) -> None:
        if self.press is press and not press["confirmed"]:
            press["confirmed"] = True
            await self._stop_talking()
            # Everything recorded so far is LISA's own voice off the speakers.
            self.ears.restart(SPEAKER_TAIL)
            self.face.state("listening")

    async def _key_up(self, at: float) -> bool:
        press, self.press = self.press, None
        if press is None:
            return False
        audio = self.ears.stop()
        if at - press["at"] < self.tap:
            log("[key] stray tap ignored")
            if not press["busy"]:
                self.face.state("idle")
            return False
        if not press["confirmed"]:
            # Released before the interrupt timer ran: she was talking for
            # the whole pre-roll and the first tap_seconds, so drop that.
            await self._stop_talking()
            drop = PREROLL_BLOCKS * BLOCK + int((self.tap + SPEAKER_TAIL) * RATE)
            audio = audio[drop:]
        self.face.state("thinking")
        text = await asyncio.to_thread(self.ears.transcribe, audio)
        if not text:
            log("[ears] heard nothing")
            self.face.state("idle")
            return False
        return await self._heard(text)

    # ---- a turn of conversation ----
    async def _heard(self, text: str) -> bool:
        """Handle one thing Sharat said or typed. True means hang up."""
        log(f"[you]    {text}")
        await self._stop_talking()
        said = _plain(text)
        if any(_plain(p) in said for p in self.cfg["hangup_phrases"]):
            self._say(self.cfg["signoff"])
            await asyncio.to_thread(self.mouth.wait, 20)
            return True
        self.turn_id += 1
        self.turn = asyncio.create_task(self._turn(text, self.turn_id))
        return False

    async def _stop_talking(self) -> None:
        self.mouth.interrupt()
        if not self._turn_running():
            return
        self.turn_id += 1
        try:
            await self.mind.interrupt()
            await asyncio.wait_for(asyncio.shield(self.turn), 8)
        except asyncio.TimeoutError:
            log("[mind] turn would not stop; restarting the brain")
            self.turn.cancel()
            await self.mind.reconnect()
        except Exception as e:
            log(f"[mind] interrupt: {e}")

    async def _turn(self, text: str, tid: int) -> None:
        self.face.state("thinking")
        cut = Sentences()

        def on_text(chunk):
            if tid != self.turn_id:
                return
            for sentence in (cut.flush() if chunk is None else cut.feed(chunk)):
                self._say(sentence)

        # Tell the face what she's really doing: "speaking" while her audio
        # is queued or playing, "thinking" when she goes quiet but is still
        # working (a tool call mid-reply). Without this the face guessed
        # from the waveform and re-chimed at every pause.
        asking = True

        async def show_state():
            shown = "thinking"
            while tid == self.turn_id:
                busy = self.mouth.busy
                want = "speaking" if busy else "thinking" if asking else None
                if want and want != shown and self.press is None:
                    shown = want
                    self.face.state(want)
                await asyncio.sleep(0.05)

        watcher = asyncio.create_task(show_state())
        try:
            await self.mind.ask(text, on_text)
            on_text(None)
            if tid == self.turn_id:
                self.face.clear_alert()
        except asyncio.CancelledError:
            watcher.cancel()
            raise
        except Exception as e:
            log(f"[mind] {e}")
            if tid == self.turn_id:
                self.face.alert(str(e)[:200])
                self._say("Sorry boss, my brain line just dropped. Say that again.")
                try:
                    await self.mind.reconnect()
                except Exception as e2:
                    log(f"[mind] reconnect failed: {e2}")
        asking = False
        while tid == self.turn_id and self.mouth.busy:
            await asyncio.sleep(0.05)
        watcher.cancel()
        if tid == self.turn_id and self.press is None:
            self.face.state("idle")


def main() -> None:
    voice = Voice(settings.load())
    try:
        asyncio.run(voice.run())
    except KeyboardInterrupt:
        voice.face.quiet()
        voice.face.state("idle")


if __name__ == "__main__":
    main()
