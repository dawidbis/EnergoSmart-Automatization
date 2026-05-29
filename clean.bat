@echo off
setlocal
chcp 65001 >nul

echo ============================================
echo   EnergoSmart - Clean Test Artifacts
echo ============================================
echo   files   - generated PDFs/XLSX in 3_Dokumenty_Testowe
echo   outlook - test emails in the M365 inbox (classic Outlook, COM)
echo   gmail   - test emails in Gmail (Sent + bounced) via IMAP -^> Trash
echo   logs    - monitor run-history (logs\run_history.jsonl)
echo   all     - files + outlook + gmail + logs
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
set "ESRUNID="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp01_Skrypty_Python\monitor.ps1" -Begin "clean"`) do set "ESRUNID=%%i"
cd 1_Skrypty_Python

set "TARGET="
set /p TARGET=What to clean? [files/outlook/gmail/logs/all] (default files):
if "%TARGET%"=="" set TARGET=files

echo.
echo [DRY RUN] Listing what would be cleaned...
echo.
python clean.py --target %TARGET%
echo.

set /p CONFIRM=Delete the above? (y/N):
if /i "%CONFIRM%"=="y" (
    python clean.py --target %TARGET% --yes
) else (
    echo Aborted. Nothing deleted.
)
set "ESRC=%ERRORLEVEL%"

cd ..
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp01_Skrypty_Python\monitor.ps1" -End "%ESRUNID%" -ExitCode %ESRC% >nul
echo.
pause
