@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: --- CONFIGURATION: Set to "true" to see errors, "false" for silent mode ---
set "DEBUG=true"

:: --- Always run from this script's folder
set "PROJECT_DIR=%~dp0"
pushd "%PROJECT_DIR%"

:: --- Pick a Python (prefer the launcher)
set "PYEXE="
where /q py  && set "PYEXE=py -3"
if not defined PYEXE (
  where /q python && set "PYEXE=python"
)
if not defined PYEXE (
  echo [TunnelTray] ERROR: Python 3 not found in PATH.
  popd & exit /b 1
)

:: --- Paths
set "VENV_DIR=%PROJECT_DIR%venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PYW=%VENV_DIR%\Scripts\pythonw.exe"
set "STAMP_FILE=%VENV_DIR%\.req_hash"
set "REQ_FILE=%PROJECT_DIR%requirements.txt"

:: --- Create venv if missing
if not exist "%VENV_PY%" (
  echo [TunnelTray] Creating virtual environment...
  %PYEXE% -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [TunnelTray] ERROR: venv creation failed.
    popd & exit /b 1
  )
)

:: --- Activate venv
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo [TunnelTray] ERROR: failed to activate venv.
  popd & exit /b 1
)

:: --- Keep packaging tools fresh (quietly)
python -m pip install --upgrade pip setuptools wheel >nul 2>&1

:: --- Compute a stamp: python/pip versions + requirements content
set "NEWHASH="
for /f "usebackq delims=" %%H in (`
  python -c "import hashlib,os,subprocess as sp; v=lambda *c: sp.check_output(c,stderr=sp.STDOUT).decode().strip(); d=(v('python','-V')+'\n'+v('python','-m','pip','-V')+'\n').encode(); p=r'%REQ_FILE%'; d+=open(p,'rb').read() if os.path.isfile(p) else b''; print(hashlib.sha256(d).hexdigest())"
`) do set "NEWHASH=%%H"

set "OLDHASH="
if exist "%STAMP_FILE%" set /p "OLDHASH="<"%STAMP_FILE%"

set "NEED_INSTALL="
if not exist "%STAMP_FILE%" (
  set "NEED_INSTALL=1"
) else if /i not "%NEWHASH%"=="%OLDHASH%" (
  set "NEED_INSTALL=1"
)

if defined NEED_INSTALL (
  if exist "%REQ_FILE%" (
    echo [TunnelTray] Installing / verifying dependencies...
    python -m pip install -r "%REQ_FILE%"
    if errorlevel 1 (
      echo [TunnelTray] ERROR: dependency install failed.
      if exist "%STAMP_FILE%" del /q "%STAMP_FILE%" >nul 2>&1
      goto :ERROR_EXIT
    )
  )
  >"%STAMP_FILE%" echo %NEWHASH%
) else (
  echo [TunnelTray] Dependencies satisfied.
)

:RUNAPP
if /i "%DEBUG%"=="true" (
    echo [TunnelTray] DEBUG MODE ENABLED
    echo [TunnelTray] Running with console output. Any errors will appear below:
    echo ---------------------------------------------------------------------
    
    :: Run with python.exe (Visible Console) and wait for it to finish/crash
    "%VENV_PY%" "%PROJECT_DIR%main.pyw"
    
    echo.
    echo ---------------------------------------------------------------------
    echo [TunnelTray] App crashed or closed. See errors above.
    echo Press any key to close this window...
    pause
    goto :EXIT
) else (
    echo [TunnelTray] Launching silently...
    :: Run with pythonw.exe (No Window) and exit batch immediately
    start "" "%VENV_PYW%" "%PROJECT_DIR%main.pyw"
    goto :EXIT
)

:ERROR_EXIT
echo.
echo [TunnelTray] Startup failed.
pause
exit /b 1

:EXIT
deactivate >nul 2>&1
popd
exit /b 0