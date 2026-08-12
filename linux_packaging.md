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
python tools/check_release_readiness.py --target linux
```

Missing `appimagetool` or `flatpak-builder` is reported as a warning because
each tool is required only for its respective packaging target. Missing bundled
application data or Python freezer dependencies is a blocking failure.

The host used for an AppImage build determines its minimum glibc compatibility;
produce public AppImages in the oldest supported Linux CI/container image, not
an arbitrary current developer workstation. Install the standard Qt/X11/OpenGL
build dependencies there and smoke-test the frozen executable before invoking
`appimagetool`. Flatpak instead receives its native libraries from the selected
runtime.

```bash
python tools/build_desktop_app.py --icon ephemeraldaddy/graphics/ephemeraldaddy.png
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
- The Flatpak build copies `dist/EphemeralDaddy` from the manifest source root.
  Keep that onedir build in place before invoking `flatpak-builder`.
- Flatpak receives only the persistent `~/.ephemeraldaddy` data-directory
  filesystem permission rather than unrestricted access to the user's home.
- Taskbar matching comes from the shared application/desktop ID
  `io.github.ephemeraldaddy.EphemeralDaddy`. Install and launch the provided
  `.desktop` entry for consistent naming and icon grouping. Flatpak or AppImage
  packaging is not required for this; it merely installs that integration in a
  convenient form.



# =================issues
## Probably need to update the requirements file?
python -m ephemeraldaddy.gui.bootstrap
[EphemeralDaddy UID migration] Chart UID finalization complete: 0 chart(s) verified, 0 relationship row(s) rewritten, 0 legacy duplicate-exclusion row(s) migrated.
^CError calling Python override of QObject::eventFilter(): Traceback (most recent call last):
  File "/media/anonymous/R2/_PROJECTS/Apps/git/ephemeraldaddy/ephemeraldaddy/gui/emoji_render.py", line 112, in eventFilter
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:

========================
another issue:
Settings>Dev Tools> "Toggle Size Checker" is returning this error on Linux:
Traceback (most recent call last):
  File "/media/anonymous/R2/_PROJECTS/Apps/git/ephemeraldaddy/ephemeraldaddy/gui/app.py", line 24278, in _toggle_size_checker
    popup = SizeCheckerPopup(
            ^^^^^^^^^^^^^^^^^
  File "/media/anonymous/R2/_PROJECTS/Apps/git/ephemeraldaddy/ephemeraldaddy/gui/dev_tools.py", line 1194, in __init__
    apply_button_cursor(self._copy_button)
    ^^^^^^^^^^^^^^^^^^^
NameError: name 'apply_button_cursor' is not defined

========================
another issue: Settings>Predictions>OCEAN Predictor scoring percentiles need to max out at a combined total of 100%. This is already handled well in Setting>Astro Twin Calculator>Scoring Methods>"Use Custom", so just reuse that same format.

=================
another issue: The Linux taskbar onhover label says "bootstrap.py" rather than "EphemeralDaddy" as it should.
