#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

VERSION=$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo "1.2.0")
DIST_DIR="$PROJECT_ROOT/dist"
APP_NAME="Yuoop Downloader.app"
DMG_NAME="Yuoop-Downloader-${VERSION}.dmg"

if [ -d "$PROJECT_ROOT/.venv" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

echo "=== Building macOS PyInstaller bundle with static FFmpeg ==="
cd "$PROJECT_ROOT"
"$PYTHON" build_exe.py --onedir --clean --bundle-ffmpeg

# PyInstaller creates dist/yuoop.app because of --name=yuoop
if [ ! -d "$DIST_DIR/yuoop.app" ]; then
    echo "ERROR: $DIST_DIR/yuoop.app not found. Make sure PyInstaller completed successfully."
    exit 1
fi

# Rename to the final app name
echo "Renaming yuoop.app to $APP_NAME"
mv "$DIST_DIR/yuoop.app" "$DIST_DIR/$APP_NAME"

echo "=== Creating DMG image ==="
if command -v create-dmg &> /dev/null; then
    create-dmg \
      --volname "Yuoop Downloader" \
      --window-pos 200 120 \
      --window-size 600 400 \
      --icon-size 100 \
      --icon "$APP_NAME" 175 120 \
      --hide-extension "$APP_NAME" \
      --app-drop-link 425 120 \
      "$DIST_DIR/$DMG_NAME" \
      "$DIST_DIR/$APP_NAME"
else
    echo "create-dmg not installed, using fallback hdiutil..."
    STAGE_DMG="$PROJECT_ROOT/build/dmg_stage"
    rm -rf "$STAGE_DMG"
    mkdir -p "$STAGE_DMG"
    cp -R "$DIST_DIR/$APP_NAME" "$STAGE_DMG/"
    ln -s /Applications "$STAGE_DMG/Applications"

    hdiutil create -volname "Yuoop Downloader" \
      -srcfolder "$STAGE_DMG" \
      -ov -format UDZO \
      "$DIST_DIR/$DMG_NAME"
fi

echo "SUCCESS: macOS DMG created at $DIST_DIR/$DMG_NAME"
