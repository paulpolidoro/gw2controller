@echo off
title GW2Controller
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "run.py"
) else (
    python "run.py"
)

if errorlevel 1 (
    echo.
    echo Nao foi possivel abrir o GW2Controller.
    echo Instale o Python 3.11+ e rode: pip install -r requirements.txt
    pause
)
