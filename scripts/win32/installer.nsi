!ifndef VERSION
  !define VERSION 'DEV'
!endif
!addplugindir "nsisPlugins"

; The name of the installer
Name "Cura ${VERSION}"

; The file to write
OutFile "Cura_${VERSION}.exe"

; The default installation directory
InstallDir $PROGRAMFILES\Cura_${VERSION}

; Registry key to check for directory (so if you install again, it will 
; overwrite the old one automatically)
InstallDirRegKey HKLM "Software\Cura_${VERSION}" "Install_Dir"

; Request application privileges for Windows Vista
RequestExecutionLevel admin

; Set the LZMA compressor to reduce size.
SetCompressor /SOLID lzma
;--------------------------------

!include "MUI2.nsh"
!include Library.nsh

!define MUI_ICON "dist/Cura/cura.ico"
!define MUI_BGCOLOR FFFFFF

; Directory page defines
!define MUI_DIRECTORYPAGE_VERIFYONLEAVE

; Header
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "header.bmp"
!define MUI_HEADERIMAGE_BITMAP_NOSTRETCH 
; Don't show the component description box
!define MUI_COMPONENTSPAGE_NODESC

;Do not leave (Un)Installer page automaticly
!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_UNFINISHPAGE_NOAUTOCLOSE

;Run Cura after installing
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Start Cura ${VERSION}"
!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink"

; Pages
;!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Reserve Files
!insertmacro MUI_RESERVEFILE_LANGDLL
ReserveFile '${NSISDIR}\Plugins\InstallOptions.dll'
ReserveFile "header.bmp"

;--------------------------------

; The stuff to install
Section "Cura ${VERSION}"

  SectionIn RO
  
  ; Set output path to the installation directory.
  SetOutPath $INSTDIR
  
  ; Put file there
  File /r "dist\"
  
  ; Write the installation path into the registry
  WriteRegStr HKLM "SOFTWARE\Cura_${VERSION}" "Install_Dir" "$INSTDIR"
  
  ; Write the uninstall keys for Windows
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Cura_${VERSION}" "DisplayName" "Cura ${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Cura_${VERSION}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Cura_${VERSION}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Cura_${VERSION}" "NoRepair" 1
  WriteUninstaller "uninstall.exe"
  
  CreateDirectory "$SMPROGRAMS\Cura ${VERSION}"
  CreateShortCut "$SMPROGRAMS\Cura ${VERSION}\Uninstall Cura ${VERSION}.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
  CreateShortCut "$SMPROGRAMS\Cura ${VERSION}\Cura ${VERSION}.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\Cura\cura.py"' "$INSTDIR\Cura\cura.ico" 0
  
  ; Give all users write permissions in the install directory, so they can read/write profile and preferences files.
  AccessControl::GrantOnFile "$INSTDIR" "(S-1-5-32-545)" "FullAccess"
  
SectionEnd

Function LaunchLink
  ExecShell "" "$SMPROGRAMS\Cura ${VERSION}\Cura ${VERSION}.lnk"
FunctionEnd

Section "Install Arduino Drivers"
  ; Set output path to the driver directory.
  SetOutPath "$INSTDIR\drivers\"
  File /r "drivers\"
  
  ${If} ${RunningX64}
    ExecWait '"$INSTDIR\drivers\dpinst64.exe" /lm'
  ${Else}
    ExecWait '"$INSTDIR\drivers\dpinst32.exe" /lm'
  ${EndIf}
SectionEnd

Section "Open STL files with Cura"
	WriteRegStr HKCR .stl "" "Cura STL model file"
	DeleteRegValue HKCR .stl "Content Type"
	WriteRegStr HKCR "Cura STL model file\DefaultIcon" "" "$INSTDIR\Cura\stl.ico,0"
	WriteRegStr HKCR "Cura STL model file\shell" "" "open"
	WriteRegStr HKCR "Cura STL model file\shell\open\command" "" '"$INSTDIR\python\pythonw.exe" "$INSTDIR\Cura\cura.py" "%1"'
SectionEnd

Section /o "Open OBJ files with Cura"
	WriteRegStr HKCR .obj "" "Cura OBJ model file"
	DeleteRegValue HKCR .obj "Content Type"
	WriteRegStr HKCR "Cura OBJ model file\DefaultIcon" "" "$INSTDIR\Cura\stl.ico,0"
	WriteRegStr HKCR "Cura OBJ model file\shell" "" "open"
	WriteRegStr HKCR "Cura OBJ model file\shell\open\command" "" '"$INSTDIR\python\pythonw.exe" "$INSTDIR\Cura\cura.py" "%1"'
SectionEnd

;--------------------------------

; Uninstaller

Section "Uninstall"
  
  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Cura_${VERSION}"
  DeleteRegKey HKLM "SOFTWARE\Cura_${VERSION}"

  ; Remove directories used
  RMDir /r "$SMPROGRAMS\Cura ${VERSION}"
  RMDir /r "$INSTDIR"

SectionEnd

