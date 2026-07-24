"""
Utility to download static FFmpeg and yt-dlp binaries for distribution/packaging.
"""

from __future__ import annotations

import os
import sys
import shutil
import zipfile
import urllib.request
import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)

FFBINARIES_VERSION = "v4.4.1"
FFMPEG_URLS = {
    "linux": f"https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/{FFBINARIES_VERSION}/ffmpeg-4.4.1-linux-64.zip",
    "windows": f"https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/{FFBINARIES_VERSION}/ffmpeg-4.4.1-win-64.zip",
    "macos": f"https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/{FFBINARIES_VERSION}/ffmpeg-4.4.1-osx-64.zip",
}

# yt-dlp GitHub releases — single static binary per platform
YTDLP_URLS = {
    "linux": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp",
    "windows": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
    "macos": "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos",
}


def _detect_platform() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    elif sys.platform.startswith("win"):
        return "windows"
    elif sys.platform.startswith("darwin"):
        return "macos"
    return "linux"


def download_static_ffmpeg(target_dir: Path | str, platform_name: str | None = None) -> Path | None:
    """
    Download static FFmpeg binary for target platform into target_dir.

    Args:
        target_dir: Directory where binary will be saved
        platform_name: 'linux', 'windows', or 'macos' (defaults to current system)

    Returns:
        Path to downloaded ffmpeg binary or None if error
    """
    target_path = Path(target_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    if not platform_name:
        platform_name = _detect_platform()

    binary_name = "ffmpeg.exe" if platform_name == "windows" else "ffmpeg"
    final_binary = target_path / binary_name

    if final_binary.exists() and os.access(final_binary, os.X_OK):
        LOGGER.info("FFmpeg binary already exists at %s", final_binary)
        return final_binary

    url = FFMPEG_URLS.get(platform_name)
    if not url:
        LOGGER.error("Unsupported platform for automatic FFmpeg download: %s", platform_name)
        return None

    archive_path = target_path / f"ffmpeg_download_{platform_name}.zip"

    try:
        LOGGER.info("Downloading FFmpeg for %s from %s...", platform_name, url)
        urllib.request.urlretrieve(url, archive_path)

        LOGGER.info("Extracting %s...", archive_path.name)
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(target_path)

        if archive_path.exists():
            archive_path.unlink()

        if final_binary.exists():
            os.chmod(final_binary, 0o755)
            LOGGER.info("FFmpeg successfully set up at %s", final_binary)
            return final_binary
        else:
            LOGGER.error("Extracted archive did not contain %s", binary_name)
            return None

    except Exception as exc:
        LOGGER.error("Failed to download static FFmpeg: %s", exc)
        if archive_path.exists():
            archive_path.unlink()
        return None


def download_static_ytdlp(target_dir: Path | str, platform_name: str | None = None) -> Path | None:
    """
    Download static yt-dlp binary for target platform into target_dir.

    Args:
        target_dir: Directory where binary will be saved
        platform_name: 'linux', 'windows', or 'macos' (defaults to current system)

    Returns:
        Path to downloaded yt-dlp binary or None if error
    """
    target_path = Path(target_dir).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    if not platform_name:
        platform_name = _detect_platform()

    binary_name = "yt-dlp.exe" if platform_name == "windows" else "yt-dlp"
    final_binary = target_path / binary_name

    if final_binary.exists() and os.access(final_binary, os.X_OK) and final_binary.stat().st_size > 0:
        LOGGER.info("yt-dlp binary already exists at %s", final_binary)
        return final_binary

    url = YTDLP_URLS.get(platform_name)
    if not url:
        LOGGER.error("Unsupported platform for automatic yt-dlp download: %s", platform_name)
        return None

    try:
        LOGGER.info("Downloading yt-dlp for %s from %s...", platform_name, url)
        urllib.request.urlretrieve(url, final_binary)
        os.chmod(final_binary, 0o755)
        LOGGER.info("yt-dlp successfully set up at %s", final_binary)
        return final_binary

    except Exception as exc:
        LOGGER.error("Failed to download static yt-dlp: %s", exc)
        if final_binary.exists():
            final_binary.unlink()
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out_dir = Path(__file__).resolve().parent.parent / "bin"
    download_static_ffmpeg(out_dir)
    download_static_ytdlp(out_dir)
