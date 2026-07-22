@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "PORT=%MVP_PORT%"
if defined PORT goto find_python
set "PORT=4181"

:find_python
py -3 -c "import sys" >nul 2>&1
if errorlevel 1 goto try_python
set "PYTHON_CMD=py -3"
goto start

:try_python
python -c "import sys" >nul 2>&1
if errorlevel 1 goto missing_python
set "PYTHON_CMD=python"
goto start

:missing_python
echo.
echo [Forge] Python 3 was not found.
echo Install Python 3.10 or newer and select Add Python to PATH.
echo See the startup guide in the repository root.
echo.
pause
exit /b 1

:start
echo.
echo [Forge] Starting the screenshot-to-MVP intake desk...
echo [Forge] Browser opens after the service is ready: http://127.0.0.1:%PORT%/
echo [Forge] Keep this window open. Closing it stops the local service.
echo.

%PYTHON_CMD% scripts\start_intake.py --port %PORT%

echo.
echo [Forge] Service stopped. See the startup guide in the repository root.
pause
