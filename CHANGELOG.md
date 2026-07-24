# Yuoop Changelog

## [1.2.0] - 2026-05-09

### Added
- Modern packaging metadata with `pyproject.toml`
- Pytest test suite under `tests/`
- GitHub Actions CI workflow for compile, tests, UI smoke test, and build argument validation
- Application icon assets in PNG and ICO formats
- `requirements-dev.txt` for development and CI dependencies

### Improved
- PyInstaller build script now supports `--dry-run`, `--onefile`, `--console`, and `--clean`
- PyInstaller spec now uses relative project paths and bundles config/assets
- Window icon is loaded from bundled assets when available

### Fixed
- Version metadata aligned to `1.2.0`

## [1.1.0] - 2026-05-09

### Fixed
- **Timeout issue when analyzing large playlists** - Increased timeout from 30s to 120s
- Added `--flat-playlist` option to yt-dlp for faster metadata extraction
- Improved error messages to guide users on timeout issues

### Improved
- **UI feedback** - Show loading message with time expectation when analyzing playlists
- **Network reliability** - Added socket timeout configuration (10s) for better network handling
- **Error handling** - Better error messages explaining what went wrong and how to fix it

### Added
- `TROUBLESHOOTING.py` - Interactive troubleshooting guide for common issues
- `CHANGELOG.md` - This changelog document

### Performance
- Faster playlist analysis with `--flat-playlist` optimization (~30-50% faster)
- Reduced network timeout from system default to explicit 10s for better error handling

---

## [1.0.0] - 2026-05-09

### Initial Release
- Complete application with YouTube playlist analysis
- Support for multiple download formats (MP4, MP3, WAV)
- Parallel download support (2-3 workers)
- Built-in video preview with thumbnail display
- User preferences persistence
- Real-time logging console
- Error handling for common issues
- Dark mode UI with CustomTkinter
- Thread-safe operations with proper UI updates
