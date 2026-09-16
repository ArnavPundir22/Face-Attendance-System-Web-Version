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

echo Starting BioSecure AI server with Waitress (16 Threads, High-Performance Multi-Core Optimized) on http://0.0.0.0:8066 ...
waitress-serve --host=0.0.0.0 --port=8066 --threads=16 --channel-timeout=120 app:app
pause

