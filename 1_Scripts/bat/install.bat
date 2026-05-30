@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0..\.."

echo ============================================
echo   EnergoSmart Automatization - Installer
echo ============================================
echo.

REM --- Check Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo         Install Python 3.10+ from https://python.org and re-run.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYVER=%%i"
echo [OK] Python !PYVER! detected
echo.

REM --- Create virtual environment ---
if not exist ".venv" (
    echo [..] Creating virtual environment .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

REM --- Activate venv ---
call .venv\Scripts\activate.bat
set "ESRUNID="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -Begin "install"`) do set "ESRUNID=%%i"

REM --- Install dependencies ---
echo [..] Upgrading pip ...
python -m pip install --upgrade pip --quiet
echo [..] Installing runtime dependencies ...
pip install -r 1_Scripts\py\requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -End "%ESRUNID%" -ExitCode 1 >nul
    pause
    exit /b 1
)
echo [OK] Runtime dependencies installed
echo [..] Installing dev dependencies (tests, linting) ...
pip install -r 1_Scripts\py\requirements-dev.txt --quiet
echo [OK] Dev dependencies installed
echo.

REM --- RPA bridge setup (SQLite ODBC driver + ENERGOSMART_DB_PATH) ---
echo [..] Setting up the RPA bridge (ODBC driver + DB path env var) ...
python 1_Scripts\py\setup.py
echo.

REM --- Setup .env from template ---
if not exist "1_Scripts\py\.env" (
    copy "1_Scripts\py\.env.example" "1_Scripts\py\.env" >nul
    echo [OK] Created .env from template
    echo      ^>^> Run configure_email.bat to configure your email/SMTP settings
) else (
    echo [OK] .env already present
)

REM --- Ensure data folders exist ---
if not exist "2_Database"      mkdir "2_Database"
if not exist "3_Test_Documents" mkdir "3_Test_Documents"
echo [OK] Data folders ready
echo.

echo ============================================
echo   Installation complete!
echo ============================================
echo Next steps:
echo   - Full guided run:            demo.bat       (repo root)
echo   - Control panel / monitor:    monitor.bat    (repo root)
echo   - Individual tools live in:   1_Scripts\bat\
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -End "%ESRUNID%" -ExitCode 0 >nul
pause
