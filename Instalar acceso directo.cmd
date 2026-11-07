@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\windows\New-VayxerShortcut.ps1"
set "exitCode=%errorlevel%"
pause
exit /b %exitCode%
