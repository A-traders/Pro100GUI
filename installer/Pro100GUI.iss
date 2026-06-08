; Inno Setup script for Pro100GUI.
;
; Bakes the bundled embedded Python + app source into a single
; per-user installer. No admin rights required.
;
; Macro inputs (passed via /D from installer/build.py):
;   AppVersion  -- e.g. "0.0.1"
;   AppSrcDir   -- staged source tree (Pro100GUI.pyw, pro100gui\, ...)
;   EmbedDir    -- ready Python embed folder with pip + deps already in
;   OutputDir   -- where to drop the produced Setup .exe

#ifndef AppVersion
  #define AppVersion "0.0.1"
#endif

#ifndef AppSrcDir
  #error "Define AppSrcDir via /DAppSrcDir=..."
#endif

#ifndef EmbedDir
  #error "Define EmbedDir via /DEmbedDir=..."
#endif

#ifndef OutputDir
  #define OutputDir "dist"
#endif

[Setup]
AppId={{8C9D2C77-2F40-4F4A-B27E-3D9D3A22A001}
AppName=Pro100GUI
AppVersion={#AppVersion}
AppVerName=Pro100GUI {#AppVersion}
AppPublisher=atradersteam
AppPublisherURL=https://github.com/A-traders/Pro100GUI
AppSupportURL=https://github.com/A-traders/Pro100GUI/issues
DefaultDirName={localappdata}\Pro100GUI
DefaultGroupName=Pro100GUI
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=Pro100GUI-Setup-{#AppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Pro100GUI
UninstallDisplayIcon={app}\python\pythonw.exe

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Embedded Python interpreter + deps live under {app}\python\
Source: "{#EmbedDir}\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; The Pro100GUI app source itself sits at {app}\
Source: "{#AppSrcDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Pro100GUI"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\Pro100GUI.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\python\pythonw.exe"; Comment: "Pro100 MT5 Strategy Tester orchestrator"
Name: "{group}\User Guide (PDF)"; Filename: "{app}\docs\UserGuide.pdf"; WorkingDir: "{app}\docs"; Comment: "Pro100GUI -- user guide"
Name: "{group}\Uninstall Pro100GUI"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Pro100GUI"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\Pro100GUI.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\python\pythonw.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\Pro100GUI.pyw"""; Description: "Запустить Pro100GUI"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\pro100gui"
Type: filesandordirs; Name: "{app}\docs"
Type: filesandordirs; Name: "{app}\__pycache__"
