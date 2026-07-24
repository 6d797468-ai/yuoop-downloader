#!/usr/bin/env python3
"""
Bootstrap helper for local users.
Creates a virtual environment, installs runtime dependencies, and checks tools.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run the local bootstrap workflow."""
    print("=" * 60)
    print("Yuoop YouTube Downloader - Bootstrap")
    print("=" * 60)

    py_version = sys.version_info
    print(f"\nPython version: {py_version.major}.{py_version.minor}.{py_version.micro}")

    if py_version.major < 3 or py_version.minor < 11:
        print("Error: Python 3.11+ required")
        return 1

    print("Python version OK")

    venv_path = Path(".venv") if Path(".venv").exists() else Path("venv")
    if not venv_path.exists():
        venv_path = Path(".venv")
        print("\nCreating virtual environment...")
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            cwd=Path(__file__).parent
        )
        if result.returncode != 0:
            print("Failed to create virtual environment")
            return 1
        print("Virtual environment created")
    else:
        print("Virtual environment already exists")

    if os.name == "nt":
        py_cmd = venv_path / "Scripts" / "python.exe"
    else:
        py_cmd = venv_path / "bin" / "python"

    print("\nInstalling dependencies...")
    result = subprocess.run(
        [str(py_cmd), "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=Path(__file__).parent
    )

    if result.returncode != 0:
        print("Failed to install dependencies")
        return 1

    print("Dependencies installed")

    print("\nChecking FFmpeg...")
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    except FileNotFoundError:
        result = subprocess.CompletedProcess(["ffmpeg"], returncode=1)

    if result.returncode == 0:
        print("FFmpeg is installed")
    else:
        print("FFmpeg not found; audio conversion needs FFmpeg on PATH")

    print("\nChecking yt-dlp...")
    result = subprocess.run([str(py_cmd), "-m", "yt_dlp", "--version"], capture_output=True)

    if result.returncode == 0:
        print("yt-dlp is installed")
    else:
        print("yt-dlp not found")
        return 1

    print("\n" + "=" * 60)
    print("Bootstrap complete")
    print("=" * 60)
    print("\nStart the application with:")
    print("  bash run.sh" if os.name != "nt" else "  run.bat")
    print("  or: python main.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
