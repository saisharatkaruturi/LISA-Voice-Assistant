"""LISA voice engine: the link to her face.

Copyright (C) 2026 Sharat. All rights reserved.

lisa-face watches small files in this folder (its `bus` setting):
  .voice_state     idle | listening | thinking | speaking
  .voice_waveform  {"ts": epoch, "samples": [64 ints]} while audio plays
  .voice_alert     non-empty when something needs attention
Fresh waveform packets make the face show "speaking" on their own.
"""
import json
import os
import time

import numpy as np

from lisa_voice.settings import HOME

WAVE_POINTS = 64
WAVE_INTERVAL = 1 / 15


class Face:
    def __init__(self, folder=HOME):
        self.folder = folder
        self._last_wave = 0.0

    def _write(self, name: str, text: str) -> None:
        final = self.folder / name
        temp = self.folder / (name + ".tmp")
        try:
            temp.write_text(text, encoding="utf-8")
            os.replace(temp, final)
        except OSError:
            # The face may be mid-read on Windows; a direct write still lands.
            try:
                final.write_text(text, encoding="utf-8")
            except OSError:
                pass

    def _remove(self, name: str) -> None:
        try:
            (self.folder / name).unlink()
        except OSError:
            pass

    def state(self, mode: str) -> None:
        self._write(".voice_state", mode)

    def wave(self, block: np.ndarray) -> None:
        now = time.time()
        if now - self._last_wave < WAVE_INTERVAL or not len(block):
            return
        self._last_wave = now
        picks = np.linspace(0, len(block) - 1, WAVE_POINTS).astype(int)
        samples = (np.clip(block[picks], -1, 1) * 32767).astype(int).tolist()
        self._write(".voice_waveform", json.dumps({"ts": now, "samples": samples}))

    def quiet(self) -> None:
        self._remove(".voice_waveform")

    def alert(self, message: str) -> None:
        self._write(".voice_alert", message)

    def clear_alert(self) -> None:
        self._remove(".voice_alert")
