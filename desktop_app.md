# Desktop app builds (Windows + macOS)

This is the practical "first EXE build" guide for EphemeralDaddy.

## Important build rule

**Build the Windows EXE on Windows** (same major OS family as your target users). PyInstaller is not a cross-compiler.

## 1) Prepare a clean build environment (Windows)

From PowerShell in the repo root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt
python -m pip install pyinstaller pillow
```

## 2) Sanity-check app before packaging

```powershell
python -m ephemeraldaddy.gui.app
```

If this fails in Python, fix that first before trying to package.

## 3) Build EXE

### Single-file EXE (easy to share)

```powershell
python tools/build_desktop_app.py --onefile --icon ephemeraldaddy/graphics/ephemeraldaddy1.png
```

Notes:
- On Windows, if `--icon` points to PNG, the helper auto-converts it to `.ico` (requires Pillow).
- Output: `dist/EphemeralDaddy.exe`.

### Folder build (faster startup, easier troubleshooting)

```powershell
python tools/build_desktop_app.py --icon ephemeraldaddy/graphics/ephemeraldaddy1.png
```

Output: `dist/EphemeralDaddy/`.

## 4) Smoke-test the packaged app

Run the generated EXE on a machine that does **not** have your dev environment active.

Checklist:
- App opens with no missing-module errors.
- Location search works (bundled `tools/cities15000.txt`).
- Chart generation works (bundled `de421.bsp`).
- Export/save flows work and DB writes succeed.

## 5) If Windows SmartScreen blocks the EXE

This is normal for unsigned first-time binaries.
- For internal testing: "More info" → "Run anyway".
- For wider distribution: code-sign the EXE with an Authenticode certificate.

## Troubleshooting

- If you see missing imports at runtime, rebuild in a clean venv and ensure step (2) works first.
- Use `python tools/build_desktop_app.py --dry-run` to inspect the exact PyInstaller command.
- If antivirus quarantines one-file EXEs, try folder build first and then sign releases.
