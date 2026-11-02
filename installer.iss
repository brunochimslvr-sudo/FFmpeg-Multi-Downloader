; Script de Instalação do Inno Setup 6
; Cria o instalador oficial para Windows do FFmpeg Multi Downloader

#define MyAppName "FFmpeg Multi Downloader"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "FFmpeg Tools"
#define MyAppExeName "FFmpeg_Downloader.exe"

[Setup]
AppId={{C6186412-D0F8-4A1B-94E7-8FE29D1789B1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=D:\Meus Programas e Alterações IA\FFmpeg\dist
OutputBaseFilename=Instalador_FFmpeg_Downloader
SetupIconFile=D:\Meus Programas e Alterações IA\FFmpeg\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Arquivos do aplicativo compilado
Source: "D:\Meus Programas e Alterações IA\FFmpeg\dist\FFmpeg_Downloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Binários do FFmpeg e yt-dlp
Source: "D:\Meus Programas e Alterações IA\FFmpeg\bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs createallsubdirs
; Ícone do aplicativo
Source: "D:\Meus Programas e Alterações IA\FFmpeg\app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
