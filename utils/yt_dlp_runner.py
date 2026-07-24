"""
Helpers for locating yt-dlp consistently in development and packaged runs.

Search order:
  1. Bundled binary next to the frozen executable or in _MEIPASS (packaged app)
  2. System PATH (``yt-dlp`` on PATH)
  3. Binary next to the Python executable (venv installs)
  4. Python module via ``sys.executable -m yt_dlp`` (dev mode only)
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path


def _bundled_yt_dlp_executable() -> Path | None:
    """Find yt-dlp bundled alongside the frozen app (PyInstaller)."""
    binary_name = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
    candidates: list[Path] = []

    # PyInstaller _MEIPASS (onefile) or _internal directory
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            meipass = Path(sys._MEIPASS)
            candidates += [meipass / binary_name, meipass / "bin" / binary_name]

        # Next to the frozen executable itself
        exe_dir = Path(sys.executable).parent
        candidates += [
            exe_dir / binary_name,
            exe_dir / "bin" / binary_name,
        ]

    # Development: project root bin/
    proj_root = Path(__file__).resolve().parent.parent
    candidates += [proj_root / "bin" / binary_name, proj_root / binary_name]

    for cand in candidates:
        if cand.is_file() and cand.stat().st_size > 0:
            return cand

    return None


def build_yt_dlp_command(*args: str) -> list[str]:
    """Return a subprocess command that runs yt-dlp with the given arguments."""
    # 1. Bundled binary (frozen app)
    bundled = _bundled_yt_dlp_executable()
    if bundled:
        return [str(bundled), *args]

    # 2. System PATH
    executable = shutil.which("yt-dlp")
    if executable:
        return [executable, *args]

    # 3. Next to Python executable (venv)
    local_executable = _local_yt_dlp_executable()
    if local_executable:
        return [str(local_executable), *args]

    # 4. Python module (dev mode only — not available when frozen)
    if not getattr(sys, "frozen", False) and importlib.util.find_spec("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp", *args]

    return ["yt-dlp", *args]


def is_yt_dlp_available() -> bool:
    """Return True when yt-dlp can be run by the current interpreter/session."""
    return (
        _bundled_yt_dlp_executable() is not None
        or shutil.which("yt-dlp") is not None
        or _local_yt_dlp_executable() is not None
        or (not getattr(sys, "frozen", False) and importlib.util.find_spec("yt_dlp") is not None)
    )


def _local_yt_dlp_executable() -> Path | None:
    """Find yt-dlp next to the current Python executable, typical for venvs."""
    executable_dir = Path(sys.executable).parent
    candidates = ["yt-dlp.exe", "yt-dlp"] if sys.platform == "win32" else ["yt-dlp", "yt-dlp.exe"]
    for name in candidates:
        candidate = executable_dir / name
        if candidate.exists() and candidate.is_file():
            return candidate
    return None
