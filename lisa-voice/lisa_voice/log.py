"""LISA voice engine: one log line to the console and to logs/lisa-voice.log.

Copyright (C) 2026 Sharat. All rights reserved.
"""
import threading
import time

from lisa_voice.settings import HOME

LOG_FILE = HOME / "logs" / "lisa-voice.log"
_lock = threading.Lock()


def log(message: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}"
    with _lock:
        try:
            print(message, flush=True)
        except (UnicodeEncodeError, OSError):
            pass
        LOG_FILE.parent.mkdir(exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
