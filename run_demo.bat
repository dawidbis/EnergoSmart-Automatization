@echo off
setlocal
chcp 65001 >nul

echo ============================================
echo   EnergoSmart - Guided Demo Runner
echo ============================================
echo.
echo Walks the whole local pipeline in order and asks before each step
echo (data -^> documents -^> email -^> cloud -^> warehouse check).
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
set "ESRUNID="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp01_Skrypty_Python\monitor.ps1" -Begin "demo"`) do set "ESRUNID=%%i"

python 1_Skrypty_Python\run_demo.py
set "ESRC=%ERRORLEVEL%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp01_Skrypty_Python\monitor.ps1" -End "%ESRUNID%" -ExitCode %ESRC% >nul
echo.
pause
