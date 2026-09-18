@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    echo [1/3] Creating build virtual environment (.venv)...
    py -3 -m venv --system-site-packages .venv
) else (
    echo [1/3] Using existing .venv
)

echo [2/3] Installing/updating PyInstaller...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pyinstaller

echo [3/3] Building TopDownShooter.exe...
".venv\Scripts\python.exe" -m PyInstaller --onefile --noconfirm --name TopDownShooter --icon app_icon.ico --add-data "images;images" main.py

echo.
echo Done. The executable is at dist\TopDownShooter.exe
pause
