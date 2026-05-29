@echo off
setlocal
chcp 65001 >nul

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
cd 1_Skrypty_Python

python setup_env.py

cd ..
echo.
pause
