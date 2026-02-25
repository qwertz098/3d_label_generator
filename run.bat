@echo off
setlocal

echo ============================================
echo  3D Label Generator - Setup and Start
echo ============================================
echo.

:: Check if git is installed
where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed or not in PATH.
    echo Please install Git from https://git-scm.com/download/win
    pause
    exit /b 1
)

:: Check if Python is installed
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Clone repo into current directory if not already done
if not exist "app.py" (
    echo [1/5] Cloning repository...
    git clone https://github.com/qwertz098/3d_label_generator.git .
    if errorlevel 1 (
        echo [ERROR] Failed to clone repository.
        pause
        exit /b 1
    )
) else (
    echo [1/5] Repository already cloned, skipping.
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [2/5] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [2/5] Virtual environment already exists, skipping.
)

:: Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install requirements
echo [4/5] Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install requirements.
    pause
    exit /b 1
)

:: Download fonts if not already downloaded
if not exist "fonts" (
    echo [4b] Downloading fonts...
    python download_fonts.py
    if errorlevel 1 (
        echo [WARNING] Font download failed. The app may still work with system fonts.
    )
) else (
    echo [4b] Fonts already downloaded, skipping.
)

:: Start the server
echo [5/5] Starting server...
echo.
echo ============================================
echo  App running at: http://localhost:5000
echo  Press CTRL+C to stop the server
echo ============================================
echo.
python app.py

pause
