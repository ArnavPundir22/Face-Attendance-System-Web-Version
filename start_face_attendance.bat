@echo off
:: Windows Startup Script for BioSecure AI

cd /d "%~dp0"

:: Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] .venv virtual environment not found. Running using system Python.
)
:: Run using Waitress WSGI server (Production multi-threaded server for Windows)
python -c "import waitress" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing Waitress WSGI production server for Windows...
    pip install waitress
)

echo Starting BioSecure AI server with Waitress on http://0.0.0.0:5000 ...
waitress-serve --host=0.0.0.0 --port=5000 app:app
pause
