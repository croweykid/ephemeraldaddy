# Linux packaging guide (AppImage + Flatpak)

This guide adds first-class Linux distribution targets for EphemeralDaddy.

## Prerequisites

- Build on Linux (native) for Linux users.
- Python 3.11 available.
- App dependencies installed in a clean virtualenv.

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

## 1) Build Linux app bundle with PyInstaller

Use the existing build helper:

```bash
python tools/build_desktop_app.py --icon ephemeraldaddy/graphics/ephemeraldaddy1.png
```

Expected output for Linux folder build:

- `dist/EphemeralDaddy/`

## 2) Build AppImage

We provide a helper that:

1. Creates an AppDir from `dist/EphemeralDaddy/`.
2. Writes a launcher `AppRun` script.
3. Copies desktop entry and icon into standard AppImage paths.
4. Invokes `appimagetool` to generate an `.AppImage`.

### One-time dependency install

```bash
sudo apt-get install -y appstream file fuse libfuse2
wget -O tools/appimagetool-x86_64.AppImage \
  https://github.com/AppImage/AppImageKit/releases/latest/download/appimagetool-x86_64.AppImage
chmod +x tools/appimagetool-x86_64.AppImage
```

### Package

```bash
bash tools/build_appimage.sh
```

Expected output:

- `dist/EphemeralDaddy-x86_64.AppImage`

## 3) Build Flatpak

Flatpak build is intentionally split into two stages:

1. Build artifacts in `dist/EphemeralDaddy/`.
2. Flatpak manifest packages that folder into `/app/lib/ephemeraldaddy` and installs a wrapper script to launch the app.

### One-time dependency install (Debian/Ubuntu)

```bash
sudo apt-get install -y flatpak flatpak-builder
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub org.kde.Platform//6.7 org.kde.Sdk//6.7
```

### Package locally

```bash
flatpak-builder --force-clean --user --install-deps-from=flathub \
  build-flatpak flatpak/io.github.ephemeraldaddy.EphemeralDaddy.yml
```

Then build/install repo bundle:

```bash
flatpak-builder --user --install --force-clean build-flatpak \
  flatpak/io.github.ephemeraldaddy.EphemeralDaddy.yml
```

Run:

```bash
flatpak run io.github.ephemeraldaddy.EphemeralDaddy
```

## Notes

- Keep Linux app metadata in `packaging/linux/`.
- If the icon path changes, update both AppImage and Flatpak metadata.
- For releases, run AppImage and Flatpak jobs in Linux CI on tag pushes.
