@echo off
REM Setup script for RAG Healthcare Chat Application on Windows



echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║   RAG Healthcare Chat Application - Setup Script       ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Check Python
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)
echo ✓ Python found
echo.

REM Create virtual environment
echo [2/4] Setting up virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping creation
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)
echo ✓ Virtual environment ready
echo.

REM Activate virtual environment
echo [3/4] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo ✓ Virtual environment activated
echo.

REM Install dependencies
echo [4/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo ✓ Dependencies installed
echo.

REM Create necessary directories
echo Creating required directories...
if not exist data mkdir data
if not exist chroma_store mkdir chroma_store
echo ✓ Directories created
echo.

REM Create .env if not exists
if not exist .env (
    echo Creating .env file from defaults...
    copy /Y .env .env >nul 2>&1
)
echo ✓ Configuration ready
echo.

echo ╔════════════════════════════════════════════════════════╗
echo ║         Setup Complete! Next Steps:                   ║
echo ║                                                        ║
echo ║  1. Run the quick verification:                       ║
echo ║     python quickstart.py                              ║
echo ║                                                        ║
echo ║  2. Start the application:                            ║
echo ║     python main.py                                    ║
echo ║                                                        ║
echo ║  3. Access the API docs:                              ║
echo ║     http://localhost:8000/docs                        ║
echo ║                                                        ║
echo ║  4. Upload a PDF document to test                     ║
echo ║                                                        ║
echo ╚════════════════════════════════════════════════════════╝
echo.

pause
