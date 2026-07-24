#!/usr/bin/env python3
"""
Build a distributable Yuoop executable with PyInstaller.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def _add_data_arg(source: Path, target: str) -> str:
    """Return a cross-platform PyInstaller --add-data value."""
    return f"{source}{os.pathsep}{target}"


def build_args(onefile: bool = False, console: bool = False, clean: bool = False, bundle_ffmpeg: bool = False) -> list[str]:
    """Build PyInstaller arguments."""
    main_script = PROJECT_ROOT / "main.py"
    icon_path = PROJECT_ROOT / "assets" / "icon.ico"

    if bundle_ffmpeg:
        from utils.ffmpeg_helper import download_static_ffmpeg, download_static_ytdlp
        bin_dir = PROJECT_ROOT / "bin"
        download_static_ffmpeg(bin_dir)
        download_static_ytdlp(bin_dir)

    args = [
        str(main_script),
        "--name=yuoop",
        "--noupx",
        "--noconfirm",
        "--collect-all=customtkinter",
        "--collect-all=yt_dlp",
        "--hidden-import=PIL",
        "--hidden-import=tkinter",
        f"--distpath={PROJECT_ROOT / 'dist'}",
        f"--workpath={PROJECT_ROOT / 'build'}",
        f"--specpath={PROJECT_ROOT}",
        "--add-data",
        _add_data_arg(PROJECT_ROOT / "config" / "default_config.json", "config"),
    ]

    assets_dir = PROJECT_ROOT / "assets"
    if assets_dir.exists():
        args.extend(["--add-data", _add_data_arg(assets_dir, "assets")])

    bin_dir = PROJECT_ROOT / "bin"
    ffmpeg_binary = bin_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if ffmpeg_binary.exists():
        args.extend(["--add-data", _add_data_arg(ffmpeg_binary, ".")])

    ytdlp_binary = bin_dir / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
    if ytdlp_binary.exists():
        args.extend(["--add-data", _add_data_arg(ytdlp_binary, ".")])

    if icon_path.exists():
        args.append(f"--icon={icon_path}")

    args.append("--onefile" if onefile else "--onedir")
    args.append("--console" if console else "--windowed")

    if clean:
        args.append("--clean")

    return args



def ensure_pyinstaller_available() -> None:
    """Fail early with a clear message when PyInstaller is missing."""
    if shutil.which("pyinstaller") is None:
        print("PyInstaller command not found. Install package extras with:")
        print("  python -m pip install -e .[package]")
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build Yuoop executable")
    parser.add_argument("--onefile", action="store_true", help="Build a single executable file")
    parser.add_argument("--onedir", action="store_true", help="Build a directory output (default)")
    parser.add_argument("--console", action="store_true", help="Keep console output visible")
    parser.add_argument("--clean", action="store_true", help="Clean PyInstaller cache before building")
    parser.add_argument("--bundle-ffmpeg", action="store_true", help="Download static FFmpeg and bundle into application package")
    parser.add_argument("--dry-run", action="store_true", help="Print PyInstaller args without building")
    args = parser.parse_args(argv)

    pyinstaller_args = build_args(
        onefile=args.onefile,
        console=args.console,
        clean=args.clean,
        bundle_ffmpeg=args.bundle_ffmpeg
    )

    print("PyInstaller arguments:")
    print(" ".join(pyinstaller_args))

    if args.dry_run:
        return 0

    ensure_pyinstaller_available()
    import PyInstaller.__main__

    PyInstaller.__main__.run(pyinstaller_args)

    output = PROJECT_ROOT / "dist" / ("yuoop.exe" if args.onefile and os.name == "nt" else "yuoop")
    print(f"\nBuild complete: {output}")
    print("Audio conversion requires FFmpeg on PATH or next to the executable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
