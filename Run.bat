@echo off
chcp 65001 > nul
echo ===============================
echo    S3 Cloud Manager Launcher
echo ===============================
echo.

REM بررسی وجود Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM بررسی وجود pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: pip is not installed
    echo Please install pip and try again
    pause
    exit /b 1
)

REM بررسی وجود virtualenv
pip show virtualenv >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing virtualenv...
    pip install virtualenv
)

REM ایجاد محیط مجازی اگر وجود ندارد
if not exist "venv" (
    echo Creating virtual environment...
    virtualenv venv
)

REM فعال کردن محیط مجازی
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM نصب یا به روزرسانی requirements
echo Installing/updating required packages...
pip install -r requirements.txt

REM اجرای برنامه
echo Starting S3 Cloud Manager...
echo.
echo The application will open in your default browser shortly...
echo.
streamlit run app.py

pause