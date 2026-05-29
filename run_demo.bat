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

python 1_Skrypty_Python\run_demo.py

echo.
pause
