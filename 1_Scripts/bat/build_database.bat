@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0..\.."

echo ============================================
echo   EnergoSmart - Local Data Pipeline
echo ============================================
echo.

REM --- Ensure venv exists ---
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo         Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
set "ESRUNID="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -Begin "database"`) do set "ESRUNID=%%i"

cd 1_Scripts\py

echo [1/1] Generating historical database (SQLite) ...
python generate_history_db.py
if errorlevel 1 (
    echo [ERROR] Database generation failed.
    cd ..
    powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -End "%ESRUNID%" -ExitCode 1 >nul
    pause
    exit /b 1
)

cd ..
echo.
echo ============================================
echo   Pipeline complete!
echo ============================================
echo   Database: 2_Database\energosmart_history.db
echo   Test documents: generate them with generate_documents.bat
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -End "%ESRUNID%" -ExitCode 0 >nul
pause
