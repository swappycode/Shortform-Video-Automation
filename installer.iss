; installer.iss - Inno Setup script for ShortsStudio
[Setup]
AppName=ShortsStudio
AppVersion=1.0
DefaultDirName={pf}\ShortsStudio
DefaultGroupName=ShortsStudio
OutputBaseFilename=ShortsStudioInstaller
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
SignTool= ; optional code signing tool

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "dist\ShortsStudio.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "bundled_tools\ffmpeg\bin\ffmpeg.exe"; DestDir: "{app}\ffmpeg\bin"; Flags: ignoreversion
Source: "bundled_tools\ffmpeg\bin\ffprobe.exe"; DestDir: "{app}\ffmpeg\bin"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "download_models.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "postinstall.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ShortsStudio"; Filename: "{app}\ShortsStudio.exe"
Name: "{commondesktop}\ShortsStudio"; Filename: "{app}\ShortsStudio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\postinstall.bat"; Description: "Download models (recommended)"; Flags: nowait postinstall skipifsilent
