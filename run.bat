@echo off
REM Quick start script for Yuoop downloader on Windows

echo Checking Python...
python --version

REM Create virtual environment if it doesn't exist
if exist ".venv" (
    set VENV_DIR=.venv
) else if exist "venv" (
    set VENV_DIR=venv
) else (
    set VENV_DIR=.venv
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
)

REM Activate virtual environment
call %VENV_DIR%\Scripts\activate.bat

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

REM Run the application
echo Starting Yuoop downloader...
python main.py
pause
