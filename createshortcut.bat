@echo off
setlocal

:: --- Configuration ---
set "TARGET_BATCH=%~dp0run.bat"
set "VBS_SCRIPT=%~dp0hideWindowsTerminal.vbs"
set "SHORTCUT_NAME=TunnelTray"
set "SHORTCUT_PATH=%~dp0%SHORTCUT_NAME%.lnk"

:: --- Validation ---
if not exist "%VBS_SCRIPT%" (
    echo [ERROR] File missing: %VBS_SCRIPT%
    echo Please ensure hideWindowsTerminal.vbs exists in this folder.
    pause
    exit /b 1
)

:: --- Creation ---
echo [TunnelTray] Creating invisible shortcut...

powershell -command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%VBS_SCRIPT%\" \"%TARGET_BATCH%\"'; $s.WorkingDirectory = '%~dp0'; $s.Save()"

:: --- Confirmation ---
if exist "%SHORTCUT_PATH%" (
    echo.
    echo [SUCCESS] Shortcut created: "%SHORTCUT_PATH%"
    echo.
    echo -----------------------------------------------------------
    echo NOW: Move "%SHORTCUT_NAME%.lnk" to your Startup folder.
    echo Press Win+R, type 'shell:startup', and drag the file there.
    echo -----------------------------------------------------------
) else (
    echo [ERROR] Failed to create shortcut.
)

endlocal
pause