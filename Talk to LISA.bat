@echo off
rem Talk to LISA: starts LISA's face and voice.
rem Copyright (C) 2026 Sharat. All rights reserved.
title LISA
set "LISA_HOME=D:\Coding Projects\LISA"
set "PHONEMIZER_ESPEAK_LIBRARY=C:/Program Files/eSpeak NG/libespeak-ng.dll"
set "HF_HUB_DISABLE_XET=1"
set "PYTHONUNBUFFERED=1"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

echo   LISA: starting her face
start "LISA face" /min cmd /c ""%LISA_HOME%\lisa-face\run.bat""

echo   LISA: checking her voice packages (first run after an update can take a while)
cd /d "%LISA_HOME%\backtalk"
uv sync --inexact
if errorlevel 1 (
  echo.
  echo   LISA's voice packages could not be installed. The reason is above.
  pause
  exit /b 1
)

echo   LISA: voice starting in this window. Close it to hang up.
uv run python -m backtalk.main 2> "%LISA_HOME%\backtalk\logs\console-errors.txt"
echo.
echo   LISA's voice line has stopped. Exit code: %errorlevel%
echo   Details: backtalk\logs\backtalk.log and backtalk\logs\console-errors.txt
pause
