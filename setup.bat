@echo off
setlocal
chcp 65001 >nul

echo ============================================
echo   EnergoSmart - RPA Bridge Setup
echo ============================================
echo Ensures the SQLite ODBC driver and sets ENERGOSMART_DB_PATH
echo (the warehouse path the Power Automate Desktop flow reads).
echo A UAC prompt may appear if the driver needs installing.
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat

python 1_Skrypty_Python\setup.py

echo.
pause
