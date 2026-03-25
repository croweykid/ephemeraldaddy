; EphemeralDaddy Windows installer script for Inno Setup 6+
; Run from repo root:
;   & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" .\installer.iss

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
; 1) folder build (DEFAULT build mode; safest for Qt/PySide6)
Source: "dist\EphemeralDaddy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 2) one-file build (only when built with: python tools/build_desktop_app.py --onefile)
; Source: "dist\EphemeralDaddy.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\EphemeralDaddy"; Filename: "{app}\EphemeralDaddy.exe"
Name: "{commondesktop}\EphemeralDaddy"; Filename: "{app}\EphemeralDaddy.exe"

[Run]
Filename: "{app}\EphemeralDaddy.exe"; Description: "Launch EphemeralDaddy"; Flags: nowait postinstall skipifsilent
