@echo off
rem Talk to LISA: starts LISA's face and voice.
rem Copyright (C) 2026 Sharat. All rights reserved.
title LISA
set "LISA_HOME=D:\Coding Projects\LISA"
set "PHONEMIZER_ESPEAK_LIBRARY=C:/Program Files/eSpeak NG/libespeak-ng.dll"
set "HF_HUB_DISABLE_XET=1"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

echo   LISA: starting her face
start "LISA face" /min cmd /c ""%LISA_HOME%\lisa-face\run.bat""

echo   LISA: voice starting in this window. Close it to hang up.
cd /d "%LISA_HOME%\lisa-voice"
if not exist logs mkdir logs
".venv\Scripts\python.exe" -m lisa_voice 2> "logs\console-errors.txt"
echo.
echo   LISA's voice line has stopped. Exit code: %errorlevel%
echo   Details: lisa-voice\logs\lisa-voice.log and lisa-voice\logs\console-errors.txt
pause
