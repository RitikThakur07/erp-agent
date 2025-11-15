@echo off
echo ====================================
echo   ERP Builder - Local AI System
echo ====================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Creating .env from template...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please edit .env and add your API keys!
    echo Press any key to open .env file...
    pause > nul
    notepad .env
    echo.
)

REM Install/upgrade dependencies
echo Checking dependencies...
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo.
echo ====================================
echo   Starting ERP Builder...
echo ====================================
echo.
echo Application will be available at:
echo   http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo ====================================
echo.

REM Start the application
python main.py

pause
