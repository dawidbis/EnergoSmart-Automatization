@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0..\.."

echo ============================================
echo   EnergoSmart - Send Test Documents (email)
echo ============================================
echo.
echo Emails prepared PDFs to the monitored inbox (SMTP from .env).
echo Recognises typed docs (GREEN_/YELLOW_/RED_) and pipeline meter
echo readings (*_MeterReading_*.pdf, counted as GREEN).
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
set "ESRUNID="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -Begin "send"`) do set "ESRUNID=%%i"
cd 1_Scripts\py

REM Interactive mode: asks which paths, how many of each (number or "all").
python send_documents.py --interactive
set "ESRC=%ERRORLEVEL%"

cd ..
powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -End "%ESRUNID%" -ExitCode %ESRC% >nul
echo.
pause
