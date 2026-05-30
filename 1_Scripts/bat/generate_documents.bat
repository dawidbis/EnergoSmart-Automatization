@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0..\.."

echo ============================================
echo   EnergoSmart - Generate Test Invoices
echo ============================================
echo.
echo Paths: GREEN = valid (auto-accept), YELLOW = needs review,
echo        RED = rejected (no client data).
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
set "ESRUNID="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -Begin "generate"`) do set "ESRUNID=%%i"
cd 1_Scripts\py

set /p GREEN="GREEN (valid, auto-accept) count [0]: "
set /p YELLOW="YELLOW (needs review)        count [0]: "
set /p RED="RED (rejected)               count [0]: "
if "%GREEN%"==""  set GREEN=0
if "%YELLOW%"=="" set YELLOW=0
if "%RED%"==""    set RED=0

echo.
python generate_invoices.py --green %GREEN% --yellow %YELLOW% --red %RED%
set "ESRC=%ERRORLEVEL%"

cd ..
powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -End "%ESRUNID%" -ExitCode %ESRC% >nul
echo.
pause
