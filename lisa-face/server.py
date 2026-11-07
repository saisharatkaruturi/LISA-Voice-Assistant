#!/usr/bin/env python3
# LISA Face server.
# Copyright (C) 2026 Sharat. All rights reserved.
"""Serves LISA's face and streams her live status to it.

LISA's voice line writes a few small status files into its folder:

  .voice_state         idle | listening | thinking | speaking
  .voice_waveform      {"ts": <epoch>, "samples": [...]} while she talks
  .voice_loading_pid   present while the voice line plays its own sound
  .voice_alert         non-empty when something needs attention
  .voice_rate_limits   optional plan-usage readout

This server reads them and pushes one JSON status line to the browser
about fifteen times a second over a server-sent event stream (/stream),
so the face reacts the instant her state changes, without polling.

  python server.py             live, opens the face in the browser
  python server.py --no-open   live, no browser
  python server.py --fake MODE pretend LISA is in MODE (for testing)

It also plays LISA's sounds on each state change, and accepts POST /talk
{"hold": true|false} from the face to hold her push-to-talk key (fist or
long-touch to talk).

Python standard library only.
"""
import errno
import json
import math
import sys
import threading
import time
import urllib.request
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path(__file__).resolve().parent
WEB = HOME / "web"
MODES = ("idle", "listening", "thinking", "speaking")
TICK = 1 / 15            # seconds between status pushes
WAVE_FRESH = 0.6         # a waveform older than this means she stopped talking

DEFAULT_SETTINGS = {"name": "LISA", "credit": "Built by Sharat",
                    "port": 7420, "bus": "../lisa-voice", "sound": True,
                    "gestures": True, "talk_key": "home"}


def load_settings():
    settings = dict(DEFAULT_SETTINGS)
    path = HOME / "settings.json"
    if path.exists():
        try:
            settings.update(json.loads(path.read_text(encoding="utf-8")))
        except ValueError as err:
            print(f"settings.json is broken ({err}); using defaults", flush=True)
    return settings


SETTINGS = load_settings()
BUS = (HOME / SETTINGS["bus"]).resolve()


def arg_after(flag):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


FAKE = arg_after("--fake")
if FAKE is not None and FAKE not in MODES:
    FAKE = "speaking"


def read_text(name):
    try:
        return (BUS / name).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def fake_status():
    now = time.time()
    talking = FAKE == "speaking"
    wave = None
    if talking:
        wave = [(math.sin(i * 0.5 + now * 10) + 0.5 * math.sin(i * 1.9 - now * 15))
                * 6000 * (0.3 + 0.7 * abs(math.sin(now * 2.2))) for i in range(64)]
    return {"mode": FAKE, "loud": abs(math.sin(now * 5)) * 0.8 if talking else 0.0,
            "wave": wave, "alert": False, "voiceSound": False, "usage": {}}


def live_status():
    mode = read_text(".voice_state").lower()
    if mode not in MODES:
        mode = "idle"
    wave, loud = None, 0.0
    try:
        packet = json.loads(read_text(".voice_waveform") or "{}")
        samples = packet.get("samples") or []
        if samples and time.time() - float(packet.get("ts", 0)) < WAVE_FRESH:
            wave = [float(v) for v in samples[:64]]
            mode = "speaking"          # fresh audio wins over a stale state file
            loud = min(1.0, sum(abs(v) for v in wave) / len(wave) / 3000)
    except (ValueError, TypeError, AttributeError):
        pass
    try:
        usage = json.loads(read_text(".voice_rate_limits") or "{}")
    except ValueError:
        usage = {}
    return {"mode": mode, "loud": loud, "wave": wave,
            "alert": bool(read_text(".voice_alert")),
            "voiceSound": (BUS / ".voice_loading_pid").exists(),
            "usage": usage}


status = fake_status if FAKE else live_status


# ---------------- sound ----------------
# The server plays LISA's sounds itself, straight to the speakers, so they
# work whether or not the face tab is open (browsers also refuse to play
# audio on a page nobody has clicked). Needs numpy + sounddevice, which the
# voice line's Python has; without them the face simply stays silent.
SOUNDS = HOME / "sounds"
SR = 44100


class Mixer:
    """A tiny mixer: one-shots and loops, each with its own fade."""

    def __init__(self):
        import numpy as np
        import sounddevice as sd
        self.np = np
        self.voices = []
        self.lock = threading.Lock()
        self.clips = {name: self.load(name) for name in ("listen", "ack", "think")}
        self.stream = sd.OutputStream(samplerate=SR, channels=2, dtype="float32",
                                      callback=self.fill)
        self.stream.start()

    def load(self, name):
        import wave
        with wave.open(str(SOUNDS / f"{name}.wav")) as w:
            raw = w.readframes(w.getnframes())
        return (self.np.frombuffer(raw, "<i2").reshape(-1, 2) / 32768).astype("float32")

    def play(self, name, gain=1.0, loop=False, fade_in=0.0):
        with self.lock:
            self.voices.append({"name": name, "data": self.clips[name], "pos": 0,
                                "loop": loop, "gain": 0.0 if fade_in else gain,
                                "target": gain, "speed": gain / max(fade_in * SR, 1)})

    def fade_out(self, name, seconds):
        with self.lock:
            for v in self.voices:
                if v["name"] == name:
                    v["target"] = 0.0
                    v["speed"] = max(v["gain"], 1e-6) / max(seconds * SR, 1)

    def fill(self, out, frames, _time, _status):
        np = self.np
        out.fill(0)
        with self.lock:
            alive = []
            for v in self.voices:
                data, pos = v["data"], v["pos"]
                if v["loop"]:
                    idx = (pos + np.arange(frames)) % len(data)
                    chunk = data[idx]
                else:
                    chunk = data[pos:pos + frames]
                g0 = v["gain"]
                step = v["speed"] * frames
                g1 = min(v["target"], g0 + step) if v["target"] > g0 else max(v["target"], g0 - step)
                ramp = np.linspace(g0, g1, len(chunk), dtype="float32")[:, None]
                out[:len(chunk)] += chunk * ramp
                v["gain"], v["pos"] = g1, pos + frames
                done = (not v["loop"] and v["pos"] >= len(data)) or (v["target"] == 0 and g1 == 0)
                if not done:
                    alive.append(v)
            self.voices = alive
        np.clip(out, -1, 1, out=out)


# ---------------- talk key ----------------
# A closed fist (or a long touch on the core) holds LISA's push-to-talk key
# down for you. The face re-sends "hold" every few hundred ms while the fist
# stays closed; if those stop (tab closed, camera lost) the watchdog lets the
# key go, so it can never stick down and leave her recording forever.
# The same key names lisa-voice accepts (lisa_voice/talk_key.py).
VK = {"home": 0x24, "end": 0x23, "insert": 0x2D, "pause": 0x13,
      "scroll_lock": 0x91, "page_up": 0x21, "page_down": 0x22,
      "right_ctrl": 0xA3, "right_alt": 0xA5, "right_shift": 0xA1,
      **{f"f{n}": 0x6F + n for n in range(1, 21)}}
_KEY = str(SETTINGS.get("talk_key", "home")).lower()
if _KEY not in VK:
    print(f"talk_key '{_KEY}' is not one I can press; using home", flush=True)
TALK_VK = VK.get(_KEY, 0x24)
# nav-cluster keys and the right-hand modifiers need the extended flag
EXTENDED = {0x24, 0x23, 0x2D, 0x21, 0x22, 0xA3, 0xA5}
talk = {"held": False, "beat": 0.0, "lock": threading.Lock()}


def press_talk(down):
    if sys.platform != "win32":
        return
    import ctypes
    flags = (0x1 if TALK_VK in EXTENDED else 0) | (0 if down else 0x2)
    ctypes.windll.user32.keybd_event(TALK_VK, 0, flags, 0)


def set_talk(hold):
    with talk["lock"]:
        if hold:
            talk["beat"] = time.monotonic()
        if hold != talk["held"]:
            talk["held"] = hold
            press_talk(hold)


def talk_watchdog():
    while True:
        time.sleep(0.2)
        if talk["held"] and time.monotonic() - talk["beat"] > 0.9:
            set_talk(False)


# ---------------- hand-tracking log ----------------
# The face reports once a second what the camera saw (gestures, finger bends,
# pinch gap, actions fired), so gesture trouble can be diagnosed from facts.
HANDS_LOG = HOME / "logs" / "hands.log"


def log_hands(entry):
    HANDS_LOG.parent.mkdir(exist_ok=True)
    if HANDS_LOG.exists() and HANDS_LOG.stat().st_size > 2_000_000:
        HANDS_LOG.replace(HANDS_LOG.with_suffix(".old.log"))      # keep it small
    with HANDS_LOG.open("a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + json.dumps(entry) + "\n")


def sound_director():
    """Watches LISA's state and plays the right sound on each change."""
    try:
        mixer = Mixer()
    except Exception as err:            # no audio libraries or no output device
        print(f"(sound off: {err})", flush=True)
        return
    prev = status()["mode"]             # a stale state at startup is not an event
    while True:
        time.sleep(0.04)
        now = status()
        mode = now["mode"]
        if mode == prev:
            continue
        quiet = now["voiceSound"]       # the voice line is playing its own sound
        if prev == "thinking":
            mixer.fade_out("think", 0.45)
        if mode == "listening" and not quiet:
            mixer.play("listen", gain=0.55)
        if mode == "thinking" and not quiet:
            # The "got it" chime is for a new command only; a pause in the
            # middle of a reply (speaking -> thinking) just brings the
            # thinking loop back.
            if prev in ("idle", "listening"):
                mixer.play("ack", gain=0.6)
            mixer.play("think", gain=0.38, loop=True, fade_in=1.4)
        prev = mode


class FaceHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        route = self.path.split("?", 1)[0]
        if route == "/stream":
            return self.stream()
        if route == "/settings":
            body = json.dumps({k: SETTINGS.get(k) for k in
                               ("name", "credit", "sound", "gestures")})
            return self.reply(body.encode(), "application/json")
        return super().do_GET()

    def do_POST(self):
        # Only the face may post here. The custom header forces a CORS
        # preflight, which a page from any other origin cannot pass.
        if self.path not in ("/talk", "/hands-log") or self.headers.get("X-Lisa-Face") != "1":
            self.send_error(403)
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            self.send_error(400)
            return
        if self.path == "/talk":
            set_talk(bool(body.get("hold")))
        else:
            log_hands(body)
        self.reply(b'{"ok": true}', "application/json")

    def stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            while True:
                self.wfile.write(f"data: {json.dumps(status())}\n\n".encode())
                self.wfile.flush()
                time.sleep(TICK)
        except (ConnectionError, OSError):
            pass                       # the tab closed; nothing to clean up

    def reply(self, body, kind):
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def already_ours(url):
    try:
        with urllib.request.urlopen(url + "settings", timeout=2) as r:
            return r.status == 200 and "credit" in json.loads(r.read())
    except Exception:
        return False


def main():
    port = int(arg_after("--port") or SETTINGS["port"])
    url = f"http://127.0.0.1:{port}/"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port),
                                     partial(FaceHandler, directory=str(WEB)))
    except OSError as err:
        if err.errno not in (errno.EADDRINUSE, errno.EACCES) and \
                getattr(err, "winerror", None) != 10048:
            raise
        if already_ours(url):
            # Closing the tab leaves the server running; just reopen the face.
            print(f"LISA's face is already running at {url}", flush=True)
            if "--no-open" not in sys.argv:
                webbrowser.open(url)
            return
        print(f"Port {port} is in use by another program. Change \"port\" in "
              f"settings.json.", flush=True)
        sys.exit(1)
    server.daemon_threads = True
    print(f"LISA face at {url}  (status from {'fake ' + FAKE if FAKE else BUS})"
          f"  Ctrl-C stops", flush=True)
    if "--no-open" not in sys.argv:
        threading.Timer(0.5, webbrowser.open, (url,)).start()
    if SETTINGS.get("sound", True):
        threading.Thread(target=sound_director, daemon=True).start()
    threading.Thread(target=talk_watchdog, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
