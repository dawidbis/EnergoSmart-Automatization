@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0..\.."

echo ============================================
echo   EnergoSmart - .env Setup Wizard
echo ============================================
echo.
echo Configures email/SMTP settings used to send test documents.
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
set "ESRUNID="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -Begin "configure"`) do set "ESRUNID=%%i"
cd 1_Scripts\py

python setup_env.py
set "ESRC=%ERRORLEVEL%"

cd ..
powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -End "%ESRUNID%" -ExitCode %ESRC% >nul
echo.
pause
