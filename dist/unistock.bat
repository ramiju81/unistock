@echo off
cd /d "%~dp0"
start "" "app.exe"
timeout /t 3 >nul
start "" "http://localhost:8000"
exit