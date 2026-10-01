@echo off
REM Price Analyst - one-click launcher for Windows (Persian web UI + backend).
REM Requires only Python 3.11+ from https://www.python.org (tick "Add python.exe to PATH").
REM First run creates .venv and installs the backend; later runs start immediately.
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [!] Python 3.11 or newer was not found.
    echo     Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [*] Creating virtual environment in .venv ...
    %PY% -m venv .venv || goto :fail
)

if not exist ".venv\.installed" (
    echo [*] Installing backend dependencies - first run only, needs internet ...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :fail
    ".venv\Scripts\python.exe" -m pip install -e backend || goto :fail
    echo ok> ".venv\.installed"
)

if not exist ".env" (
    echo [*] Creating .env from .env.example - all marketplace sources stay disabled until you enable them.
    copy /y ".env.example" ".env" >nul
)

echo [*] Starting backend and Persian UI. Close this window or press Ctrl+C to stop.
".venv\Scripts\python.exe" webui\serve.py --start-backend --open %*
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo [!] Something went wrong. See the messages above.
echo     To force a clean reinstall, delete the .venv folder and run this file again.
pause
exit /b 1
