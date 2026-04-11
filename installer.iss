; EphemeralDaddy Windows installer script for Inno Setup 6+
; Run from repo root:
;   & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" .\installer.iss

[Setup]
AppName=EphemeralDaddy
AppVersion=1.2.3
DefaultDirName={autopf}\EphemeralDaddy
DefaultGroupName=EphemeralDaddy
OutputDir=dist
OutputBaseFilename=EphemeralDaddy-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\EphemeralDaddy.exe

[Files]
Source: "dist\EphemeralDaddy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\EphemeralDaddy"; Filename: "{app}\EphemeralDaddy.exe"
Name: "{commondesktop}\EphemeralDaddy"; Filename: "{app}\EphemeralDaddy.exe"

[Run]
Filename: "{app}\EphemeralDaddy.exe"; Description: "Launch EphemeralDaddy"; Flags: nowait postinstall skipifsilent
