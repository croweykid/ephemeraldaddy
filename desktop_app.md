# Desktop app builds (Windows + macOS)

To make EphemeralDaddy start from an icon (without the terminal), build a desktop bundle. The
bundled app includes the GUI and an embedded icon for each platform.

## Icon formats & sizes

- **PNG is great as a source**, but OS-level app icons need platform-specific formats:
  - **Windows** expects a multi-size **`.ico`** file (16–256 px).
  - **macOS** expects a multi-size **`.icns`** file (16–1024 px).
- Start from a **1024×1024 PNG**; the build helper will generate `.ico` and `.icns`.

## Build steps

1. Install build tools:
   ```bash
   python -m pip install pyinstaller pillow
   ```
2. Build the app with all dependencies bundled:
   ```bash
   python tools/build_desktop_app.py --onefile --icon icons/ephemeraldaddy1.png
   ```

The helper collects hidden imports and package data (including astrology assets and bundled datasets) so the resulting binary can run offline.

The bundled app will be in `dist/EphemeralDaddy.exe` on Windows (for `--onefile`) or `dist/EphemeralDaddy`/`dist/EphemeralDaddy.app` for folder-based builds.

## Custom icon

If you want a different icon, point `--icon` at another **1024×1024 PNG**. The build helper will
generate the required `.ico`/`.icns` automatically.