@echo off
setlocal
chcp 65001 >nul

echo ============================================
echo   EnergoSmart - Warehouse Health-Check
echo ============================================
echo.
echo Read-only report on the local SQLite warehouse (via SQLite ODBC).
echo Confirms readings synced from the cloud by the RPA bridge.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp01_Skrypty_Python\healthcheck.ps1" %*

echo.
pause
