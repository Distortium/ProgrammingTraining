@echo off
setlocal

set "NO_PAUSE="
if /I "%~1"=="--no-pause" set "NO_PAUSE=1"
set "RC=0"
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-RestMethod -Uri 'http://localhost:8000/health' -TimeoutSec 5; $r | ConvertTo-Json -Compress; exit 0 } catch { Write-Host '[ERROR] API is not reachable on http://localhost:8000/health'; exit 1 }"
set "RC=%errorlevel%"

popd >nul
if not defined NO_PAUSE pause
exit /b %RC%

