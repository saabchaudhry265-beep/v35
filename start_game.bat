@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (where python >nul 2>nul && (set PY=python) || (echo Python 3.10+ not found. Install it from https://www.python.org/downloads/windows/ & pause & exit /b 1))
if not exist assets\hero_down.png (echo Folder assets is missing next to game.py. Unpack the whole archive. & pause & exit /b 1)
%PY% -c "import pygame" >nul 2>nul || %PY% -m pip install -r requirements.txt
%PY% game.py
if errorlevel 1 pause
