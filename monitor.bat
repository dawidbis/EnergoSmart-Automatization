@echo off
setlocal
chcp 65001 >nul

REM EnergoSmart control panel / monitor.
REM No args  -> interactive control panel (launch tasks, see history, run PAD)
REM -Watch   -> live read-only dashboard
REM -LaunchPad / -Dashboard / -ClearHistory also supported.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp01_Scripts\ps\monitor.ps1" %*

echo.
pause
