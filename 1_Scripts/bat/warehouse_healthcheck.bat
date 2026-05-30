@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0..\.."

echo ============================================
echo   EnergoSmart - Warehouse Health-Check
echo ============================================
echo.
echo Read-only report on the local SQLite warehouse (via SQLite ODBC).
echo Confirms readings synced from the cloud by the RPA bridge.
echo.

set "ESRUNID="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -Begin "healthcheck"`) do set "ESRUNID=%%i"

powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\healthcheck.ps1" %*
set "ESRC=%ERRORLEVEL%"

powershell -NoProfile -ExecutionPolicy Bypass -File "1_Scripts\ps\monitor.ps1" -End "%ESRUNID%" -ExitCode %ESRC% >nul
echo.
pause
