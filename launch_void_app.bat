@echo off
title V.O.I.D. Desktop App
cd /d "%~dp0"
echo ======================================================
echo       V.O.I.D. Advanced Neural Interface
echo           Launching Native Desktop App...
echo ======================================================
echo.

python desktop_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Error] Python launcher encountered an issue. Starting web server directly...
    start http://127.0.0.1:5000
    python app.py
)

pause

