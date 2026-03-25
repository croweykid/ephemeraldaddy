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
; 1) one-file build (default)
Source: "dist\EphemeralDaddy.exe"; DestDir: "{app}"; Flags: ignoreversion
; 2) folder build
; Source: "dist\EphemeralDaddy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\EphemeralDaddy"; Filename: "{app}\EphemeralDaddy.exe"
Name: "{commondesktop}\EphemeralDaddy"; Filename: "{app}\EphemeralDaddy.exe"

[Run]
Filename: "{app}\EphemeralDaddy.exe"; Description: "Launch EphemeralDaddy"; Flags: nowait postinstall skipifsilent
