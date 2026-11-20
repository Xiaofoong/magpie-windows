#ifndef Arch
  #error Arch must be amd64 or arm64
#endif
#if Arch == "amd64"
  #define PlatformName "x64"
  #define AllowedArchitecture "x64compatible"
#else
  #define PlatformName "ARM64"
  #define AllowedArchitecture "arm64"
#endif

[Setup]
AppId={{69643378-45DE-4CE6-B4EE-D114D5547D35}
AppName=Magpie
AppVersion={#AppVersion}
VersionInfoVersion={#WindowsVersion}
AppPublisher=Magpie Windows
AppPublisherURL=https://github.com/Xiaofoong/magpie-windows
AppUpdatesURL=https://github.com/Xiaofoong/magpie-windows/releases
DefaultDirName={reg:HKCU\Software\magpie,InstallLocation|{localappdata}\Programs\magpie}
DefaultGroupName=Magpie
PrivilegesRequired=lowest
ArchitecturesAllowed={#AllowedArchitecture}
ArchitecturesInstallIn64BitMode={#AllowedArchitecture}
OutputDir=..\dist
OutputBaseFilename=Magpie-Windows-{#PlatformName}-Setup
UninstallDisplayIcon={app}\magpie.exe
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE

[Languages]
Name: "zh"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
zh.DesktopShortcut=创建桌面快捷方式
zh.LaunchMagpie=打开 Magpie
en.DesktopShortcut=Create a desktop shortcut
en.LaunchMagpie=Open Magpie

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopShortcut}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\magpie-windows-{#Arch}.exe"; DestDir: "{app}"; DestName: "magpie.exe"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Magpie"; Filename: "{app}\magpie.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Magpie"; Filename: "{app}\magpie.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\magpie"; ValueType: string; ValueName: "InstallLocation"; ValueData: "{app}"; Flags: uninsdeletevalue uninsdeletekeyifempty

[Run]
Filename: "{app}\magpie.exe"; Description: "{cm:LaunchMagpie}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  Note, Profile: String;
begin
  if CurStep <> ssPostInstall then
    Exit;
  Note := ExpandConstant('{app}\webview-profile');
  if FileExists(Note) then
    Exit;
  // WebView2 defaults to a folder named after the executable. Carry the
  // old download's profile into the fixed magpie.exe installation.
  Profile := ExpandConstant('{userappdata}\magpie.exe');
  if not DirExists(Profile) then
    Profile := ExpandConstant('{userappdata}\magpie-windows-{#Arch}.exe');
  if DirExists(Profile) then
    if not SaveStringToFile(Note, Utf8Encode(Profile + #13#10), False) then
      RaiseException('Could not preserve the existing Magpie WebView2 profile.');
end;
