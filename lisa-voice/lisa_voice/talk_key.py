"""LISA voice engine: the push-to-talk key.

Copyright (C) 2026 Sharat. All rights reserved.

A global keyboard hook, so the key works whichever window has focus. The
face's fist gesture and long touch press this same key (lisa-face injects
it), so all three routes arrive here. Held-key auto-repeat is ignored.
"""
from pynput import keyboard

K = keyboard.Key
KEYS = {
    "home": K.home, "end": K.end, "insert": K.insert, "pause": K.pause,
    "scroll_lock": K.scroll_lock, "page_up": K.page_up, "page_down": K.page_down,
    "right_ctrl": K.ctrl_r, "right_alt": K.alt_r, "right_shift": K.shift_r,
    **{f"f{n}": getattr(K, f"f{n}") for n in range(1, 21)},
}


class TalkKey:
    def __init__(self, name: str, on_down, on_up):
        if name.lower() not in KEYS:
            raise ValueError(f"unknown talk key '{name}'; use one of {sorted(KEYS)}")
        self.key = KEYS[name.lower()]
        self.on_down, self.on_up = on_down, on_up
        self.held = False
        self._listener = keyboard.Listener(on_press=self._press,
                                           on_release=self._release)

    def _press(self, key) -> None:
        if key == self.key and not self.held:
            self.held = True
            self.on_down()

    def _release(self, key) -> None:
        if key == self.key and self.held:
            self.held = False
            self.on_up()

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()
