@echo off
setlocal

set "NO_PAUSE="
if /I "%~1"=="--no-pause" set "NO_PAUSE=1"
set "RC=0"
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

set PORT_PID=
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
  set PORT_PID=%%P
  goto :found
)

echo [INFO] No listening process found on port 8000.
goto :end

:found
echo [INFO] Stopping PID %PORT_PID% on port 8000...
taskkill /PID %PORT_PID% /F >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Failed to stop PID %PORT_PID%.
  set "RC=1"
  goto :end
)

echo [OK] Process %PORT_PID% stopped.

:end
popd >nul
if not defined NO_PAUSE pause
exit /b %RC%


