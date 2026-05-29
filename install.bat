@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

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
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp01_Skrypty_Python\monitor.ps1" -Begin "install"`) do set "ESRUNID=%%i"

REM --- Install dependencies ---
echo [..] Upgrading pip ...
python -m pip install --upgrade pip --quiet
echo [..] Installing runtime dependencies ...
pip install -r 1_Skrypty_Python\requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp01_Skrypty_Python\monitor.ps1" -End "%ESRUNID%" -ExitCode 1 >nul
    pause
    exit /b 1
)
echo [OK] Runtime dependencies installed
echo [..] Installing dev dependencies (tests, linting) ...
pip install -r 1_Skrypty_Python\requirements-dev.txt --quiet
echo [OK] Dev dependencies installed
echo.

REM --- RPA bridge setup (SQLite ODBC driver + ENERGOSMART_DB_PATH) ---
echo [..] Setting up the RPA bridge (ODBC driver + DB path env var) ...
python 1_Skrypty_Python\setup.py
echo.

REM --- Setup .env from template ---
if not exist "1_Skrypty_Python\.env" (
    copy "1_Skrypty_Python\.env.example" "1_Skrypty_Python\.env" >nul
    echo [OK] Created .env from template
    echo      ^>^> Run setup_env.bat to configure your email/SMTP settings
) else (
    echo [OK] .env already present
)

REM --- Ensure data folders exist ---
if not exist "2_Baza_Danych"      mkdir "2_Baza_Danych"
if not exist "3_Dokumenty_Testowe" mkdir "3_Dokumenty_Testowe"
echo [OK] Data folders ready
echo.

echo ============================================
echo   Installation complete!
echo ============================================
echo Next steps:
echo   1. Configure email/SMTP:      setup_env.bat
echo   2. Generate data + reports:   run_local_pipeline.bat
echo   3. Run the test suite:        run_tests.bat
echo   4. Control panel / monitor:   monitor.bat
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp01_Skrypty_Python\monitor.ps1" -End "%ESRUNID%" -ExitCode 0 >nul
pause
