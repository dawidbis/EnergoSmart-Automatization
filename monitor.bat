@echo off
setlocal
chcp 65001 >nul

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
cd 1_Skrypty_Python

REM Live dashboard - refreshes every 3s. Press Ctrl+C to stop.
python monitor_company.py --watch --interval 3

cd ..
echo.
pause
