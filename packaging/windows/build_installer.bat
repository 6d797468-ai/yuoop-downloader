@echo off
echo === Building Yuoop Downloader for Windows ===

cd /d "%~dp0..\.."

echo Step 1: Building PyInstaller executable with bundled FFmpeg...
python build_exe.py --onedir --clean --bundle-ffmpeg

echo Step 2: Compiling Inno Setup installer...
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\yuoop_setup.iss
    echo SUCCESS: Windows Setup installer created in dist\
) else (
    echo WARNING: Inno Setup (ISCC.exe) not found on standard PATH.
    echo Dist folder dist\yuoop contains standalone binary.
)

pause
