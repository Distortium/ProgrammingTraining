@echo off
setlocal

set "NO_PAUSE="
if /I "%~1"=="--no-pause" set "NO_PAUSE=1"
set "RC=0"
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul

net session >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Run this script as Administrator.
  set "RC=1"
  goto :end
)

set RULE_IN=CodeRunner API 8000 Inbound
set RULE_OUT=CodeRunner API 8000 Outbound

netsh advfirewall firewall delete rule name="%RULE_IN%" >nul 2>&1
netsh advfirewall firewall delete rule name="%RULE_OUT%" >nul 2>&1

netsh advfirewall firewall add rule name="%RULE_IN%" dir=in action=allow protocol=TCP localport=8000 profile=private
if errorlevel 1 (
  echo [ERROR] Failed to add inbound firewall rule.
  set "RC=1"
  goto :end
)

netsh advfirewall firewall add rule name="%RULE_OUT%" dir=out action=allow protocol=TCP localport=8000 profile=private
if errorlevel 1 (
  echo [ERROR] Failed to add outbound firewall rule.
  set "RC=1"
  goto :end
)

echo [OK] Firewall rules for TCP 8000 were added.

:end
popd >nul
if not defined NO_PAUSE pause
exit /b %RC%


