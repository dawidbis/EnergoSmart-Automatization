@echo off
setlocal
chcp 65001 >nul

echo ============================================
echo   EnergoSmart - Send Test Documents (email)
echo ============================================
echo.
echo Emails prepared PDFs to the monitored inbox (SMTP from .env).
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
cd 1_Skrypty_Python

set /p STYPE="Type to send (green/yellow/red/all) [all]: "
set /p SCOUNT="How many?                         [1]: "
set /p SDELAY="Delay between emails (seconds)    [0]: "
if "%STYPE%"==""  set STYPE=all
if "%SCOUNT%"=="" set SCOUNT=1
if "%SDELAY%"=="" set SDELAY=0

set /p SDRY="Dry run (list only, do NOT send)? (y/N): "
echo.
if /i "%SDRY%"=="y" (
    python send_documents.py --type %STYPE% --count %SCOUNT% --delay %SDELAY% --dry-run
) else (
    python send_documents.py --type %STYPE% --count %SCOUNT% --delay %SDELAY%
)

cd ..
echo.
pause
