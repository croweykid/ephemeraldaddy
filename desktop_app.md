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

## 4) Turnkey installer (recommended for non-technical users)

A raw `.exe` works, but a true installer gives the most "double-click and done" experience.

### Option A: Inno Setup (simple + reliable)

1. Install Inno Setup from `https://jrsoftware.org/isinfo.php`.
2. Use the included `installer.iss` file in the repo root (already valid Inno syntax).
   - If you previously copy/pasted from Markdown, make sure your `installer.iss` does **not** include code-fence lines like `````ini`` or ``````, which cause `Text is not inside a section.` errors.
   - Edit `AppVersion` as needed, and choose one-file vs folder line in `[Files]`.

3. Build with Inno Setup Compiler (GUI), or command line. **Run this from the repo root** (the same folder that contains `installer.iss` and `dist/`):

```powershell
cd C:\path\to\ephemeraldaddy
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" .\installer.iss
```

PowerShell needs the `&` call operator when launching a quoted executable path.

If you run it from another directory, pass an absolute path to the script instead:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "C:\path\to\ephemeraldaddy\installer.iss"
```

4. Distribute the generated file: `dist/EphemeralDaddy-Setup.exe`.

### Option B: MSIX (better enterprise trust/deployment)

MSIX is excellent for managed Windows fleets, but requires extra signing/setup overhead.
For first release, most indie apps start with Inno Setup + code signing.

## 5) Smoke-test the packaged app

Run the generated installer/EXE on a machine that does **not** have your dev environment active.

Checklist:
- App opens with no missing-module errors.
- Start Menu/Desktop shortcut launches correctly (installer build).
- Location search works (bundled `tools/cities15000.txt`).
- Chart generation works (bundled `de421.bsp`).
- Export/save flows work and DB writes succeed.

## 6) Signing + SmartScreen reality check

Unsigned binaries often trigger Microsoft SmartScreen.

- For private/internal testing: "More info" → "Run anyway".
- For public release: sign your installer and EXE with an Authenticode code-signing certificate.
- Reputation improves over time when signed installers are consistently downloaded/run.

## Troubleshooting

- If you see missing imports at runtime, rebuild in a clean venv and ensure step (2) works first.
- Use `python tools/build_desktop_app.py --dry-run` to inspect the exact PyInstaller command.
- If antivirus quarantines one-file EXEs, try folder build first and then sign releases.
