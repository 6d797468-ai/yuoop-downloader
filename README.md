# Yuoop — YouTube Downloader

> **Simple preview‑first downloads, crafted with care.**
> A polished desktop application for downloading YouTube playlists, videos, mixes, and channels — with built‑in media preview and audio conversion, no manual dependency setup required.

---

## ✨ Features

| Feature | Details |
| :--- | :--- |
| 📋 **Playlist & Mix Analysis** | Detect and queue all videos from any YouTube URL |
| 📹 **Flexible Formats** | MP4 720p/1080p, MP3 320kbps/192kbps, WAV |
| 👁️ **Built‑in Preview** | Thumbnail display and video preview player |
| ⚡ **Parallel Downloads** | Up to 3 simultaneous downloads |
| 🎨 **Modern UI** | Dark mode with CustomTkinter |
| 🔋 **Fully Standalone** | FFmpeg and yt‑dlp bundled — no extra installs |
| 💾 **Persistent Config** | Remembers folder, format and window size |
| 📊 **Real‑time Logging** | Live progress and status in the console |

---

## 🖥️ Installation — Native Packages (Recommended)

> **No Python or FFmpeg needed.** All dependencies are included in the installers.

### Debian / Ubuntu (`.deb`)

```bash
# Download the latest release
wget https://github.com/6d797468-ai/yuoop-downloader/releases/latest/download/yuoop-downloader_1.2.0_amd64.deb

# Install
sudo dpkg -i yuoop-downloader_1.2.0_amd64.deb

# Launch
yuoop
```

The application appears in your application menu under **Internet** / **Multimedia**.

### Linux (AppImage — universal)

```bash
wget https://github.com/6d797468-ai/yuoop-downloader/releases/latest/download/yuoop-downloader-1.2.0-x86_64.AppImage
chmod +x yuoop-downloader-1.2.0-x86_64.AppImage
./yuoop-downloader-1.2.0-x86_64.AppImage
```

### Windows (Installer)

Download **`yuoop-downloader-1.2.0-windows-setup.exe`** from the [Releases page](https://github.com/6d797468-ai/yuoop-downloader/releases) and run it.  
The installer adds Yuoop to Start Menu and Desktop.

### macOS (Disk Image)

Download **`Yuoop-Downloader-1.2.0.dmg`**, open it and drag **Yuoop Downloader.app** to your Applications folder.

---

## 🛠️ Installation — From Source (Development)

**Requirements**: Python 3.11 or later, `git`.

```bash
git clone https://github.com/6d797468-ai/yuoop-downloader.git
cd yuoop-downloader

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python main.py
```

For development tooling (linting, tests):

```bash
pip install -r requirements-dev.txt
pytest
```

---

## 📦 Build Your Own Installer

All installers embed FFmpeg and yt‑dlp automatically.

### Debian / Ubuntu

```bash
./packaging/build_deb.sh
# → dist/yuoop-downloader_1.2.0_amd64.deb
```

### Linux AppImage

```bash
./packaging/build_appimage.sh
# → dist/yuoop-downloader-1.2.0-x86_64.AppImage
```

### Windows *(run on Windows)*

```bat
packaging\windows\build_installer.bat
rem → dist\yuoop-downloader-1.2.0-windows-setup.exe
```

### macOS *(run on macOS)*

```bash
./packaging/macos/build_dmg.sh
# → dist/Yuoop-Downloader-1.2.0.dmg
```

### Standalone Executable (without packaging)

```bash
python build_exe.py --onedir --bundle-ffmpeg
# Result: dist/yuoop/
```

Options:

| Flag | Description |
| :--- | :--- |
| `--bundle-ffmpeg` | Download and embed static FFmpeg + yt‑dlp binaries |
| `--onefile` | Single‑file executable (slower startup) |
| `--console` | Keep terminal output visible |
| `--clean` | Clear PyInstaller cache before building |
| `--dry-run` | Print PyInstaller args without building |

---

## 🚀 Usage

1. **Paste a URL** — playlist, video, mix or channel.
2. Click **Analyze** and wait 1–2 minutes for metadata.
3. **Select** videos to download (individually or via *Select All*).
4. Choose a **Format** and **Folder**.
5. Click **Download Selected** and monitor progress.
6. Click **Stop** to cancel at any time.

---

## 📁 Project Structure

```
yuoop-downloader/
├── main.py                    # Application entry point
├── build_exe.py               # PyInstaller build script
├── yuoop.spec                 # PyInstaller spec (auto-generated)
├── config/
│   ├── settings.py            # Configuration manager + binary detection
│   └── default_config.json    # Default settings
├── downloader/
│   ├── youtube.py             # YouTube extraction via yt-dlp
│   ├── formats.py             # Format definitions
│   └── queue_manager.py       # Threaded download queue
├── ui/
│   ├── app.py                 # Main window
│   └── components.py          # Reusable UI widgets
├── player/
│   └── video_player.py        # Built-in preview player
├── utils/
│   ├── yt_dlp_runner.py       # yt-dlp binary locator (frozen-aware)
│   ├── ffmpeg_helper.py       # FFmpeg + yt-dlp static binary downloader
│   ├── validators.py          # URL and input validation
│   ├── thumbnail_cache.py     # Thumbnail caching
│   └── logger.py              # Logging setup
├── packaging/
│   ├── build_deb.sh           # Debian/Ubuntu .deb builder
│   ├── build_appimage.sh      # Linux AppImage builder
│   ├── deb/                   # Debian metadata and .desktop file
│   ├── windows/
│   │   ├── yuoop_setup.iss    # Inno Setup script
│   │   └── build_installer.bat
│   └── macos/
│       └── build_dmg.sh       # macOS .dmg builder
├── .github/workflows/
│   ├── ci.yml                 # Test matrix (Python 3.11–3.13)
│   └── release.yml            # Multi-OS release automation
├── tests/                     # Pytest test suite (9 tests)
└── assets/                    # Icons and images
```

---

## 🎞️ Supported Formats

### Video
- MP4 1080p
- MP4 720p
- MP4 480p

### Audio
- MP3 320 kbps
- MP3 192 kbps
- WAV (lossless)

---

## 🔧 Troubleshooting

### "yt‑dlp not found"
The installer bundles yt‑dlp. If you see this error, reinstall using the latest `.deb` / `.exe` / `.dmg`.  
For source installs: `pip install yt-dlp`.

### "FFmpeg not found"
Native installers include a static FFmpeg binary — no manual install needed.  
For source installs:
- Linux: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: download from [ffmpeg.org](https://ffmpeg.org)

### Playlist Analysis Slow / Timeout
Analysis of large playlists (200+ videos) can take 1–2 minutes. This is normal.

### Downloads Failing
- Check your internet connection.
- Some videos may be region‑restricted or have been removed.
- Update yt‑dlp: `pip install -U yt-dlp` (source) or reinstall the package.

### Config Not Saving
Verify the app has write permissions to:
- **Linux/macOS**: `~/.config/yuoop-downloader/`
- **Windows**: `%APPDATA%\yuoop-downloader\`

### Interactive Troubleshooting Guide
```bash
python TROUBLESHOOTING.py
python TROUBLESHOOTING.py "ffmpeg"
python TROUBLESHOOTING.py "timeout"
```

---

## 🧑‍💻 Development

### Running Tests
```bash
pytest                     # All 9 unit tests
pytest -v                  # Verbose output
```

### Adding Features
- **New format** → `downloader/formats.py`
- **New UI widget** → `ui/components.py`
- **New validation** → `utils/validators.py`

### CI / CD
Push a version tag to trigger the full release pipeline:
```bash
git tag v1.2.0
git push origin v1.2.0
```
GitHub Actions builds `.deb`, AppImage, `.exe`, and `.dmg` automatically and attaches them to the release.

---

## 📄 License

MIT License — Free for personal and commercial use.

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8.
- New features include proper error handling.
- UI components remain responsive.

---
**Nawfel Reghai**
**Version**: 1.2.0 | **Last Updated**: 2026-07-24
