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

:: Run using Flask development server (Gunicorn is not supported natively on Windows)
echo Starting BioSecure AI server...
flask --app app:app run --debug
pause
