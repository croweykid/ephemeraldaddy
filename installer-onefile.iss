; EphemeralDaddy Windows installer script for Inno Setup 6+
; Run from repo root:
;   & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" .\installer.iss

#include "packaging\windows\version.iss"

[Setup]
AppId=io.github.ephemeraldaddy.EphemeralDaddy
AppName=EphemeralDaddy
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\EphemeralDaddy
DefaultGroupName=EphemeralDaddy
OutputDir=dist
OutputBaseFilename=EphemeralDaddy-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\EphemeralDaddy.exe
CloseApplications=yes
RestartApplications=no

[Files]
Source: "dist\EphemeralDaddy.exe"; DestDir: "{app}"; DestName: "EphemeralDaddy.exe"

[Icons]
Name: "{group}\EphemeralDaddy"; Filename: "{app}\EphemeralDaddy.exe"
Name: "{commondesktop}\EphemeralDaddy"; Filename: "{app}\EphemeralDaddy.exe"

[Run]
Filename: "{app}\EphemeralDaddy.exe"; Description: "Launch EphemeralDaddy"; Flags: nowait postinstall skipifsilent
