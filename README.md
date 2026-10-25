# LISA

**A personal AI chief of staff, designed and built by Sharat.**

LISA is a voice-first AI assistant that runs on my own computer. I hold a key, talk to her, and she answers out loud in a real voice — with hands on my real files and apps, a long-term memory that survives between conversations, and a live animated face that shows what she's doing at every moment.

She runs my student life: planning my day, reading my timetable, prepping for exams, telling me straight whether I can afford to skip a class, drafting my emails, and opening whatever I need.

## What makes LISA different

- **She works, she doesn't just chat.** LISA takes real actions on my machine and hands back finished work, not advice.
- **Unlimited, structured memory.** Everything she knows lives in an Obsidian vault (`LISA Memory`) — my profile, my studies, my priorities, a daily log of every session. She loads exactly what a job needs, when it needs it, so she remembers everything without drowning in it.
- **A personality, on purpose.** LISA has one identity across typing and talking: a sharp-witted, foul-mouthed butler who pushes back when I'm wrong instead of agreeing with everything.
- **A face that's alive.** The LISA Core visualizer — a living neural sphere of ~700 neurons firing synapse chains around a plasma core — breathes cyan on standby, turns green while listening, storms violet while thinking, and ripples with her voice when she speaks.
- **Her own sound.** A custom-synthesized acknowledgment chirp and processing tone play the moment she takes a command.

## How it's put together

| Part | What it does | Where |
|---|---|---|
| Brain + identity | LISA's personality, rules, and operating manual | `CLAUDE.md` |
| Memory | Obsidian vault: profile, studies, daily notes, Jobs | `D:/Coding Projects/LISA Memory` |
| Voice | Push-to-talk → local speech recognition → Claude → spoken reply | `backtalk/` |
| Face | LISA Core: my own server and engine, streaming her live state to the browser | `lisa-face/` |
| Launch | One click, starts automatically at login | `Talk to LISA.bat` |

## Running LISA

Double-click **Talk to LISA** on the Desktop (it also starts by itself at login). Hold **Home** to talk. The face opens in the browser; press **F** for fullscreen.

## Credits

LISA — her design, identity, memory system, study workflows, the LISA Core face and her sound — is my project.

She runs on Claude, and her voice line uses an open-source component under its own license (see `backtalk/LICENSE`).

© 2026 Sharat
