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
  goto :port_check_done
)
:port_check_done

if defined PORT_PID (
  echo [ERROR] Port 8000 is already in use by PID %PORT_PID%.
  echo [ERROR] Stop that process or change API port in run_api.bat/config.
  set "RC=1"
  goto :end
)

py -3 -m uvicorn server.main:app --host 0.0.0.0 --port 8000
set "RC=%errorlevel%"

:end
popd >nul
if not defined NO_PAUSE pause
exit /b %RC%


