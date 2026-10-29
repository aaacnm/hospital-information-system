@echo off
chcp 65001 >nul
setlocal
title HeXu HIS - Start
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0demo-control.ps1" -Action Start %*
if errorlevel 1 (
    echo.
    echo 启动遇到问题，请把上面的提示发给组员。
    pause
    exit /b 1
)
if "%~1"=="" timeout /t 3 /nobreak >nul
endlocal
