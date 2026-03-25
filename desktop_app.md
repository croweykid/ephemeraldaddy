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
2. Create `installer.iss` in the repo root with this starter config:

```ini
[Setup]
AppName=EphemeralDaddy
AppVersion=1.0.0
DefaultDirName={autopf}\EphemeralDaddy
DefaultGroupName=EphemeralDaddy
OutputDir=dist
OutputBaseFilename=EphemeralDaddy-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Files]
; Use ONE of the next two lines depending on your build type:
; 1) one-file build
Source: "dist\EphemeralDaddy.exe"; DestDir: "{app}"; Flags: ignoreversion
; 2) folder build
; Source: "dist\EphemeralDaddy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\EphemeralDaddy"; Filename: "{app}\EphemeralDaddy.exe"
Name: "{commondesktop}\EphemeralDaddy"; Filename: "{app}\EphemeralDaddy.exe"

[Run]
Filename: "{app}\EphemeralDaddy.exe"; Description: "Launch EphemeralDaddy"; Flags: nowait postinstall skipifsilent
```

3. Build with Inno Setup Compiler (GUI), or command line:

```powershell
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
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
