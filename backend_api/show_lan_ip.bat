@echo off
setlocal

set "NO_PAUSE="
if /I "%~1"=="--no-pause" set "NO_PAUSE=1"
set "RC=0"
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254*' } | Select-Object InterfaceAlias,IPAddress | Format-Table -AutoSize"
if errorlevel 1 set "RC=1"

popd >nul
if not defined NO_PAUSE pause
exit /b %RC%


