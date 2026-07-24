#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION=$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo "1.2.0")
PACKAGE_NAME="yuoop-downloader_${VERSION}_amd64"
STAGE_DIR="$PROJECT_ROOT/build/deb_stage"
DIST_DIR="$PROJECT_ROOT/dist"

if [ -d "$PROJECT_ROOT/.venv" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

echo "=== Building PyInstaller binary with bundled FFmpeg ==="
cd "$PROJECT_ROOT"
"$PYTHON" build_exe.py --onedir --clean --bundle-ffmpeg

echo "=== Preparing Debian package directory structure ==="
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR/DEBIAN"
mkdir -p "$STAGE_DIR/opt/yuoop-downloader"
mkdir -p "$STAGE_DIR/usr/bin"
mkdir -p "$STAGE_DIR/usr/share/applications"
mkdir -p "$STAGE_DIR/usr/share/pixmaps"

# Copy DEBIAN control metadata
cp "$SCRIPT_DIR/deb/DEBIAN/control" "$STAGE_DIR/DEBIAN/control"
sed -i "s/Version: .*/Version: ${VERSION}/" "$STAGE_DIR/DEBIAN/control"

# Copy PyInstaller bundle to /opt/yuoop-downloader
cp -r "$DIST_DIR/yuoop/"* "$STAGE_DIR/opt/yuoop-downloader/"

# Desktop launcher & icons
cp "$SCRIPT_DIR/deb/usr/share/applications/yuoop.desktop" "$STAGE_DIR/usr/share/applications/yuoop.desktop"
if [ -f "$PROJECT_ROOT/assets/icon.png" ]; then
    cp "$PROJECT_ROOT/assets/icon.png" "$STAGE_DIR/usr/share/pixmaps/yuoop.png"
fi

# Fix file permissions before creating symlink
chmod -R 755 "$STAGE_DIR/opt/yuoop-downloader"
chmod 644 "$STAGE_DIR/usr/share/applications/yuoop.desktop"
chmod 755 "$STAGE_DIR/DEBIAN"
chmod 644 "$STAGE_DIR/DEBIAN/control"

# Symlink executable to /usr/bin/yuoop
ln -s "/opt/yuoop-downloader/yuoop" "$STAGE_DIR/usr/bin/yuoop"

echo "=== Building .deb package ==="
mkdir -p "$DIST_DIR"
dpkg-deb -Zgzip --root-owner-group --build "$STAGE_DIR" "$DIST_DIR/${PACKAGE_NAME}.deb"

echo "SUCCESS: Debian package created at $DIST_DIR/${PACKAGE_NAME}.deb"
