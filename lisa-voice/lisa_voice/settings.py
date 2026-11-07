"""LISA voice engine: settings.

Copyright (C) 2026 Sharat. All rights reserved.

Defaults live here; `voice.json` beside the package overrides any of them.
"""
import json
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent

DEFAULTS = {
    # Who she is and where her brain runs.
    "name": "LISA",
    "agent_dir": "D:/Coding Projects/LISA",
    "extra_dirs": ["D:/Coding Projects/LISA Memory"],
    "model": "claude-sonnet-5",
    "permission_mode": "bypassPermissions",
    # Push-to-talk. Must match `talk_key` in lisa-face/settings.json.
    "talk_key": "home",
    # A press shorter than this is a stray tap: ignored, never interrupts.
    "tap_seconds": 0.35,
    # Her voice (Kokoro). The first letter picks the accent: a=US, b=UK.
    "voice": "af_bella",
    "speed": 1.0,
    # Her hearing (faster-whisper, local).
    "hearing_model": "models/faster-whisper-small.en",
    "hearing_device": "auto",
    "hearing_compute": "int8",
    # Names Whisper should favour. Never edit the model files to add names.
    "hotwords": "Sharat, Sharat Karuturi, LISA",
    # Microphone, matched by name. "" = the Windows default input.
    "mic_device": "",
    # What she says when she comes up and when she hangs up.
    "greeting": "Good {time_of_day}, boss. What's on our schedule today?",
    "signoff": "LISA signing off. I'll be here when you need me.",
    "hangup_phrases": ["goodbye lisa"],
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    path = HOME / "voice.json"
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    model = Path(cfg["hearing_model"])
    if not model.is_absolute():
        cfg["hearing_model"] = str(HOME / model)
    return cfg
