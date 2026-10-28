@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (where python >nul 2>nul && (set PY=python) || (echo Python 3.10+ not found. Install it from https://www.python.org/downloads/windows/ & pause & exit /b 1))
if not exist assets\hero_down.png (echo Folder assets is missing next to game.py. & pause & exit /b 1)
%PY% -m pip install -r requirements.txt pyinstaller || (echo pip failed & pause & exit /b 1)
%PY% -m PyInstaller --noconfirm --clean tropy_eldorii.spec || (echo Build failed & pause & exit /b 1)
echo.
echo Done: dist\Tropy Eldorii\Tropy Eldorii.exe
pause
