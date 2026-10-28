; Inno Setup 6 script. Build after PyInstaller: ISCC installer\\tropy_eldorii.iss
#define AppName "Тропы Эльдории"
#define AppVersion "35.0.0"

[Setup]
AppId={{BFCC8595-EFA8-435B-B9FA-DD49D8F9768E}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=ЗАПОЛНИТЕ: студия
DefaultDirName={autopf}\Tropy Eldorii
DefaultGroupName={#AppName}
OutputDir=..\dist
OutputBaseFilename=TropyEldorii_Setup_v35
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\Tropy Eldorii.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
LicenseFile=..\EULA_TEMPLATE_RU.txt

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"

[Files]
Source: "..\dist\Tropy Eldorii\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Tropy Eldorii.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Tropy Eldorii.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Tropy Eldorii.exe"; Description: "Запустить игру"; Flags: nowait postinstall skipifsilent
