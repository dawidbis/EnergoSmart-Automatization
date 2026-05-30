@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   EnergoSmart - Demo (full guided run)
echo ============================================
echo Full run-through for a new machine:
echo   install -^> configure email -^> build database
echo           -^> generate documents -^> send to inbox
echo.
echo Press Enter (Y) to run a step, or type n to skip it.
echo Each step opens its own tool window; close it to continue.
echo.

set /p A1=STEP 1/5  Install (venv, dependencies, ODBC driver, .env)? [Y/n]:
if /i not "%A1%"=="n" call "%~dp0bat\install.bat"
cd /d "%~dp0"
echo.

set /p A2=STEP 2/5  Configure email / SMTP (.env wizard)? [Y/n]:
if /i not "%A2%"=="n" call "%~dp0bat\setup_env.bat"
cd /d "%~dp0"
echo.

set /p A3=STEP 3/5  Build the database (SQLite warehouse)? [Y/n]:
if /i not "%A3%"=="n" call "%~dp0bat\run_local_pipeline.bat"
cd /d "%~dp0"
echo.

set /p A4=STEP 4/5  Generate typed test documents (Green/Yellow/Red)? [Y/n]:
if /i not "%A4%"=="n" call "%~dp0bat\generate_invoices.bat"
cd /d "%~dp0"
echo.

set /p A5=STEP 5/5  Send documents to the monitored inbox? [Y/n]:
if /i not "%A5%"=="n" call "%~dp0bat\send_documents.bat"
cd /d "%~dp0"

echo.
echo ============================================
echo   Demo finished.
echo   Use monitor.bat to watch the flow and capture screenshots.
echo ============================================
pause
