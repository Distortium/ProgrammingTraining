@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend_api"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend"
set "NO_FRONTEND="
if /I "%~1"=="--no-frontend" set "NO_FRONTEND=1"

if not exist "%BACKEND_DIR%\docker-compose.yml" (
  echo [ERROR] backend_api\docker-compose.yml not found.
  exit /b 1
)
if not exist "%FRONTEND_DIR%\index.html" (
  echo [ERROR] frontend\index.html not found.
  exit /b 1
)

echo [1/5] Checking Docker CLI...
docker version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker CLI not found. Install Docker Desktop and retry.
  exit /b 1
)

echo [2/5] Checking Docker daemon...
docker info >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker daemon is not available. Start Docker Desktop and retry.
  exit /b 1
)

pushd "%BACKEND_DIR%" >nul

echo [3/5] Ensuring runner images...
call :ensure_image local-code-runner-python:latest runners\python
if errorlevel 1 goto :backend_fail
call :ensure_image local-code-runner-javascript:latest runners\javascript
if errorlevel 1 goto :backend_fail
call :ensure_image local-code-runner-csharp:latest runners\csharp
if errorlevel 1 goto :backend_fail

echo [4/5] Starting PostgreSQL + backend...
docker compose up -d --build
if errorlevel 1 (
  echo [WARN] Build step failed, trying to start existing images...
  docker compose up -d
  if errorlevel 1 goto :backend_fail
)

echo [4/5] Waiting for backend health...
set "HEALTH_OK=0"
for /L %%I in (1,1,40) do (
  curl -fsS http://localhost:8000/health >nul 2>nul
  if not errorlevel 1 (
    set "HEALTH_OK=1"
    goto :health_ready
  )
  ping 127.0.0.1 -n 2 >nul
)

:health_ready
if "%HEALTH_OK%"=="1" (
  echo [OK] Backend health: http://localhost:8000/health
) else (
  echo [WARN] Backend health check timed out. Check: docker compose logs backend
)

echo.
echo Containers:
docker compose ps

popd >nul

call :detect_lan_ip

if defined NO_FRONTEND (
  echo.
  echo [OK] Backend and database are up. Frontend launch skipped: --no-frontend
  exit /b 0
)

echo.
echo [5/5] Starting frontend HTTP server...
echo - Local URL: http://localhost:5500
if defined LAN_IP echo - Phone URL: http://%LAN_IP%:5500
echo - Admin login: admin
echo - Admin password: admin12345
echo.

pushd "%FRONTEND_DIR%" >nul
py -3 -m http.server 5500 --bind 0.0.0.0
set "RC=%ERRORLEVEL%"
popd >nul
exit /b %RC%

:ensure_image
set "IMAGE=%~1"
set "CONTEXT=%~2"
docker image inspect "%IMAGE%" >nul 2>nul
if not errorlevel 1 (
  echo [OK] %IMAGE%
  exit /b 0
)
echo [BUILD] %IMAGE% from %CONTEXT%
docker build -t "%IMAGE%" "%CONTEXT%"
if errorlevel 1 (
  echo [ERROR] Failed to build %IMAGE%.
  exit /b 1
)
exit /b 0

:detect_lan_ip
set "LAN_IP="
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /I "IPv4"') do (
  set "IP=%%A"
  for /f "tokens=1 delims=(" %%B in ("!IP!") do set "IP=%%B"
  set "IP=!IP: =!"
  if not "!IP!"=="" if not "!IP!"=="127.0.0.1" if /I not "!IP:~0,8!"=="169.254." (
    if not defined LAN_IP set "LAN_IP=!IP!"
    if "!IP:~0,8!"=="192.168." if /I not "!IP:~-2!"==".1" (
      set "LAN_IP=!IP!"
      goto :detect_lan_ip_done
    )
    if "!IP:~0,3!"=="10." if /I not "!IP:~-2!"==".1" (
      set "LAN_IP=!IP!"
      goto :detect_lan_ip_done
    )
  )
)
:detect_lan_ip_done
exit /b 0

:backend_fail
set "RC=%ERRORLEVEL%"
popd >nul
echo [ERROR] Backend startup failed. See logs above.
exit /b %RC%
