@echo off
setlocal
cd /d "%~dp0"
title ReconDeck

where wsl.exe >nul 2>nul
if errorlevel 1 goto native

echo Starting ReconDeck in WSL...
echo Keep this window open while using ReconDeck.
echo.
wsl.exe --cd "%CD%" bash ./start.sh
if errorlevel 1 goto failed
goto stopped

:native
echo WSL was not found. Trying the native Windows Python setup...
echo.

where py.exe >nul 2>nul
if errorlevel 1 (
    echo Python 3 was not found. Install Python 3.10 or newer, or install WSL Ubuntu.
    goto failed
)

where dig.exe >nul 2>nul
if errorlevel 1 (
    echo The dig command was not found.
    echo Install WSL Ubuntu with dnsutils and whois, or install those tools on Windows.
    goto failed
)

where whois.exe >nul 2>nul
if errorlevel 1 (
    echo The whois command was not found.
    echo Install WSL Ubuntu with dnsutils and whois, or install those tools on Windows.
    goto failed
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating the Python virtual environment...
    py.exe -3 -m venv .venv
    if errorlevel 1 goto failed
)

echo Installing or checking Python dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed

echo Starting ReconDeck...
echo Keep this window open while using ReconDeck.
echo.
".venv\Scripts\python.exe" app.py --port 5000
if errorlevel 1 goto failed
goto stopped

:stopped
echo.
echo ReconDeck has stopped.
pause
exit /b 0

:failed
echo.
echo ReconDeck could not start. Review the message above, then press any key to close.
pause
exit /b 1
