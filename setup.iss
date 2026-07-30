; Inno Setup Script for Payment Management System
; Download Inno Setup from: https://jrsoftware.org/isinfo.php
; After building with build.bat, compile this file with Inno Setup

[Setup]
AppName=Payment Management System
AppVersion=1.0
AppPublisher=Your Company Name
AppPublisherURL=https://yourcompany.com
DefaultDirName={autopf}\PaymentManagementSystem
DefaultGroupName=Payment Management System
OutputDir=installer_output
OutputBaseFilename=PMS_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=
SetupIconFile=
UninstallDisplayIcon={app}\PaymentManagementSystem.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\PaymentManagementSystem.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Payment Management System"; Filename: "{app}\PaymentManagementSystem.exe"
Name: "{group}\Uninstall Payment Management System"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Payment Management System"; Filename: "{app}\PaymentManagementSystem.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PaymentManagementSystem.exe"; Description: "{cm:LaunchProgram,Payment Management System}"; Flags: nowait postinstall skipifsilent
