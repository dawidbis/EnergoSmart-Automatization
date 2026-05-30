@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0..\.."

echo ============================================
echo   EnergoSmart - Test Suite
echo ============================================
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo         Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
set "ESRUNID="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -Begin "tests"`) do set "ESRUNID=%%i"

REM --- Ensure pytest available ---
python -c "import pytest" >nul 2>&1
if errorlevel 1 (
    echo [..] Installing dev dependencies ...
    pip install -r 1_Scripts\py\requirements-dev.txt --quiet
)

echo [..] Running pytest ...
echo.
python -m pytest 1_Scripts\py\tests -v
set "RESULT=%errorlevel%"

echo.
if "%RESULT%"=="0" (
    echo [OK] All tests passed.
) else (
    echo [FAIL] Some tests failed. See output above.
)
powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -End "%ESRUNID%" -ExitCode %RESULT% >nul
pause
exit /b %RESULT%
