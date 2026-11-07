"""LISA voice engine: one log line to the console and to logs/lisa-voice.log.

Copyright (C) 2026 Sharat. All rights reserved.
"""
import threading
import time

from lisa_voice.settings import HOME

LOG_FILE = HOME / "logs" / "lisa-voice.log"
MAX_BYTES = 2_000_000            # then it rolls over to lisa-voice.old.log
_lock = threading.Lock()


def log(message: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}"
    with _lock:
        try:
            print(message, flush=True)
        except (UnicodeEncodeError, OSError):
            pass
        LOG_FILE.parent.mkdir(exist_ok=True)
        try:
            if LOG_FILE.stat().st_size > MAX_BYTES:
                LOG_FILE.replace(LOG_FILE.with_suffix(".old.log"))
        except OSError:
            pass
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
