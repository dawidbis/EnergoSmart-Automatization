@echo off
setlocal
chcp 65001 >nul

echo ============================================
echo   EnergoSmart - RPA Bridge Setup
echo ============================================
echo Ensures the SQLite ODBC driver and sets ENERGOSMART_DB_PATH
echo (the warehouse path the Power Automate Desktop flow reads).
echo A UAC prompt may appear if the driver needs installing.
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
set "ESRUNID="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp01_Skrypty_Python\monitor.ps1" -Begin "setup"`) do set "ESRUNID=%%i"

python 1_Skrypty_Python\setup.py
set "ESRC=%ERRORLEVEL%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp01_Skrypty_Python\monitor.ps1" -End "%ESRUNID%" -ExitCode %ESRC% >nul
echo.
pause
