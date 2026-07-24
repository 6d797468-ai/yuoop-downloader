#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION=$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo "1.2.0")
APPDIR="$PROJECT_ROOT/build/yuoop.AppDir"
DIST_DIR="$PROJECT_ROOT/dist"

if [ -d "$PROJECT_ROOT/.venv" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

echo "=== Building PyInstaller executable ==="
cd "$PROJECT_ROOT"
"$PYTHON" build_exe.py --onedir --clean --bundle-ffmpeg

echo "=== Creating AppDir structure ==="
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

cp -r "$DIST_DIR/yuoop/"* "$APPDIR/usr/bin/"
cp "$SCRIPT_DIR/deb/usr/share/applications/yuoop.desktop" "$APPDIR/yuoop.desktop"
if [ -f "$PROJECT_ROOT/assets/icon.png" ]; then
    cp "$PROJECT_ROOT/assets/icon.png" "$APPDIR/yuoop.png"
    cp "$PROJECT_ROOT/assets/icon.png" "$APPDIR/.DirIcon"
fi

# Create AppRun entrypoint
cat << 'EOF' > "$APPDIR/AppRun"
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="$HERE/usr/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/bin:$LD_LIBRARY_PATH"
exec "$HERE/usr/bin/yuoop" "$@"
EOF

chmod +x "$APPDIR/AppRun"

echo "=== Generating AppImage ==="
APPIMAGETOOL="$PROJECT_ROOT/build/appimagetool"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "Downloading appimagetool..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/13/appimagetool-x86_64.AppImage" -O "$APPIMAGETOOL"
    chmod +x "$APPIMAGETOOL"
fi

ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$DIST_DIR/yuoop-downloader-${VERSION}-x86_64.AppImage"

echo "SUCCESS: AppImage created at $DIST_DIR/yuoop-downloader-${VERSION}-x86_64.AppImage"
