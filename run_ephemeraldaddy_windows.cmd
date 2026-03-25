@echo off
setlocal enableextensions enabledelayedexpansion

REM Stable Windows launcher for EphemeralDaddy.
REM - Reuses the same venv across runs (no forced recreation)
REM - Creates a startup log in .logs\startup-YYYYMMDD-HHMMSS.log
REM - Uses the lightweight bootstrap entrypoint for visible startup progress

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
cd /d "%ROOT_DIR%"

set "VENV_DIR="
set "PYTHON_EXE="

if exist "%ROOT_DIR%\venv\Scripts\python.exe" (
    set "VENV_DIR=%ROOT_DIR%\venv"
    set "PYTHON_EXE=%ROOT_DIR%\venv\Scripts\python.exe"
) else (
    set "VENV_DIR=%ROOT_DIR%\venv"
    set "PYTHON_EXE=%ROOT_DIR%\venv\Scripts\python.exe"
    echo [EphemeralDaddy] No venv found. Creating one with py -3.11 at "%VENV_DIR%"...
    py -3.11 -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [EphemeralDaddy] Failed to create venv with py -3.11.
        echo [EphemeralDaddy] Install Python 3.11 and ensure the Python launcher ^(py^) is available.
        exit /b 1
    )

    echo [EphemeralDaddy] Installing dependencies into "%VENV_DIR%"...
    "%PYTHON_EXE%" -m pip install --upgrade pip
    if errorlevel 1 exit /b 1
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if errorlevel 1 exit /b 1
)

if not exist ".logs" mkdir ".logs"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%I"
set "LOG_PATH=%ROOT_DIR%\.logs\startup-%STAMP%.log"

echo [EphemeralDaddy] Writing startup log to "%LOG_PATH%"

set "PYTHONUNBUFFERED=1"
set "EPHEMERALDADDY_STARTUP_LOG=%LOG_PATH%"

"%PYTHON_EXE%" -m ephemeraldaddy.gui.bootstrap 1>"%LOG_PATH%" 2>&1
set "APP_EXIT=%ERRORLEVEL%"

if not "%APP_EXIT%"=="0" (
    echo [EphemeralDaddy] App exited with code %APP_EXIT%.
    echo [EphemeralDaddy] Last 40 log lines:
    powershell -NoProfile -Command "if (Test-Path '%LOG_PATH%') { Get-Content -Path '%LOG_PATH%' -Tail 40 }"
)

exit /b %APP_EXIT%
