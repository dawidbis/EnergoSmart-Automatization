@echo off
setlocal
chcp 65001 >nul

echo ============================================
echo   EnergoSmart - Clean Test Documents
echo ============================================
echo.
echo Removes generated *.pdf / *.xlsx from 3_Dokumenty_Testowe.
echo The database and source code are NOT touched.
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
cd 1_Skrypty_Python

echo Preview of files that would be removed:
echo.
python clean_test_documents.py --type all
echo.
set /p CONFIRM="Delete ALL the files listed above? (y/N): "
echo.
if /i "%CONFIRM%"=="y" (
    python clean_test_documents.py --type all --yes
) else (
    echo [SKIP] Nothing deleted.
)

cd ..
echo.
pause
