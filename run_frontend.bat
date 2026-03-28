@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%frontend" >nul
echo Frontend started:
echo - Local: http://localhost:5500
echo - LAN:   http://^<YOUR_PC_IP^>:5500
py -3 -m http.server 5500 --bind 0.0.0.0
popd >nul
endlocal
