#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
APP_NAME="EphemeralDaddy"
APPDIR="$DIST_DIR/${APP_NAME}.AppDir"
APP_BIN_DIR="$DIST_DIR/${APP_NAME}"
DESKTOP_FILE_SRC="$ROOT_DIR/packaging/linux/io.github.ephemeraldaddy.EphemeralDaddy.desktop"
ICON_SRC="$ROOT_DIR/ephemeraldaddy/graphics/ephemeraldaddy1.png"
APPIMAGETOOL_BIN="${APPIMAGETOOL_BIN:-$ROOT_DIR/tools/appimagetool-x86_64.AppImage}"

if [[ ! -d "$APP_BIN_DIR" ]]; then
  echo "Missing $APP_BIN_DIR. Build first:" >&2
  echo "  python tools/build_desktop_app.py --icon ephemeraldaddy/graphics/ephemeraldaddy1.png" >&2
  exit 1
fi

if [[ ! -x "$APPIMAGETOOL_BIN" ]]; then
  echo "appimagetool not found/executable at: $APPIMAGETOOL_BIN" >&2
  echo "Set APPIMAGETOOL_BIN or place it at tools/appimagetool-x86_64.AppImage" >&2
  exit 1
fi

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/512x512/apps"
cp -a "$APP_BIN_DIR/." "$APPDIR/usr/bin/"
cp "$DESKTOP_FILE_SRC" "$APPDIR/"
cp "$DESKTOP_FILE_SRC" "$APPDIR/usr/share/applications/"
cp "$ICON_SRC" "$APPDIR/io.github.ephemeraldaddy.EphemeralDaddy.png"
cp "$ICON_SRC" "$APPDIR/usr/share/icons/hicolor/512x512/apps/io.github.ephemeraldaddy.EphemeralDaddy.png"

cat > "$APPDIR/AppRun" <<'APP_RUN'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$HERE/usr/bin/EphemeralDaddy" "$@"
APP_RUN
chmod +x "$APPDIR/AppRun"

( cd "$DIST_DIR" && ARCH=x86_64 "$APPIMAGETOOL_BIN" "${APP_NAME}.AppDir" "${APP_NAME}-x86_64.AppImage" )

echo "Created: $DIST_DIR/${APP_NAME}-x86_64.AppImage"
