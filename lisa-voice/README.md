# lisa-voice

LISA's voice engine. Copyright (C) 2026 Sharat. All rights reserved.

Hold **Home** (or make a fist at the face's webcam, or long-press the core on the touchscreen), talk, let go. LISA hears you locally, thinks with a live Claude Code session running in her home folder (same CLAUDE.md, same vault, same LISA as a typed session), and answers out loud sentence by sentence while the reply is still being written. You can also type in the voice window; it's the same conversation.

## How it works

| File | Job |
|---|---|
| `lisa_voice/__main__.py` | The conversation loop. Key presses, typed lines and timers become events on one asyncio queue, handled in order. |
| `lisa_voice/talk_key.py` | Global push-to-talk hook (pynput). The face presses the same key for fist and touch. |
| `lisa_voice/ears.py` | Always-open mic with a 0.25 s pre-roll so first words aren't clipped; local faster-whisper transcription with name hotwords. |
| `lisa_voice/mind.py` | The Claude Code session (Claude agent SDK), streaming text back as it's written. |
| `lisa_voice/mouth.py` | Sentence splitter plus a two-thread render/play pipeline (Kokoro), interruptible at any moment. |
| `lisa_voice/face.py` | Writes the status files lisa-face watches (`.voice_state`, `.voice_waveform`, `.voice_alert`). |
| `lisa_voice/settings.py` | Defaults. Put overrides in `voice.json` beside this README. |

## Behaviour

- **Greeting** by time of day on start; **"goodbye lisa"** signs off and closes the line.
- **Interrupt** by holding the key while she talks or thinks. A tap under 0.35 s is a stray tap and is ignored.
- **Silence is silence.** A built-in voice detector skips non-speech before Whisper runs, and a guard drops the hotwords if Whisper echoes them back, so an empty press never sends words she didn't hear.
- **Speed.** Greedy decoding: same transcript as beam search on this laptop without the multi-second stalls.

## Settings (`voice.json`)

`name`, `agent_dir`, `extra_dirs`, `model`, `permission_mode`, `talk_key` (must match `talk_key` in `lisa-face/settings.json`), `tap_seconds`, `voice` (Kokoro voice; first letter = accent), `speed`, `hearing_model`, `hearing_device`, `hearing_compute`, `hotwords`, `mic_device` (matched by name), `greeting` (`{time_of_day}` allowed), `signoff`, `hangup_phrases`.

**Never edit the Whisper model's tokenizer to teach it names.** It breaks the model. Use `hotwords`.

## Setup

```
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```
The hearing model lives in `models/faster-whisper-small.en`. Kokoro's voice comes from the Hugging Face cache. eSpeak NG must be installed (`PHONEMIZER_ESPEAK_LIBRARY` is set by `Talk to LISA.bat`).

## Built on

Open-source libraries, each under its own license: faster-whisper (MIT), Kokoro (Apache-2.0), sounddevice (MIT), pynput (LGPL-3.0, used unmodified as a library), numpy (BSD), Claude agent SDK (MIT).
