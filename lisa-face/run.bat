@echo off
rem LISA Face launcher. Copyright (C) 2026 Sharat. All rights reserved.
rem Starts the face server (standard-library Python) and opens the face.
title LISA face
cd /d "%~dp0"

rem LISA's voice engine Python always exists on this machine; fall back to
rem the Windows launcher only if it ever goes missing.
set "VENV_PY=%~dp0..\lisa-voice\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
  "%VENV_PY%" server.py %*
) else (
  py -3 server.py %*
)
if errorlevel 1 (
  echo.
  echo   LISA's face stopped with an error. The message is above.
  pause
)
