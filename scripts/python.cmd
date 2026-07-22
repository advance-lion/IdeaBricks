@echo off
chcp 65001 >nul
set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PYTHON_EXE%" (
  echo [MVP Worker] Python 3.12 not found at "%PYTHON_EXE%" 1>&2
  exit /b 1
)
"%PYTHON_EXE%" %*
