@echo off
title PDF Suite Setup
setlocal
cd /d "%~dp0"

:: 1. CHECK FOR VIRTUAL ENVIRONMENT
:: If venv exists, we skip Step 1 and 2 to avoid file-locking conflicts
if exist "venv" goto LAUNCH

echo --------------------------------------------------
echo  FIRST-TIME SETUP: Initializing PDF Suite...
echo --------------------------------------------------
echo  [Step 1/2] Creating private environment...
echo  (This may take up to 60 seconds)
echo.
python -m venv venv
if %errorlevel% neq 0 goto ERROR

echo.
echo  [Step 2/2] Installing required libraries...
venv\Scripts\python -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 goto ERROR

:LAUNCH
:: 2. SUCCESS & LAUNCH
:: Start the app silently and exit the console immediately
:: Using pythonw.exe ensures no console window stays open for the app itself
start "" /b venv\Scripts\pythonw.exe "app.pyw" "%*"
exit

:ERROR
echo.
echo  --------------------------------------------------
echo  [SYSTEM ERROR] Setup failed.
echo  Please ensure you have Python installed and 
echo  an active internet connection for the first run.
echo  --------------------------------------------------
pause
exit