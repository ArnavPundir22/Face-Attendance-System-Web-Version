@echo off
REM BioSecure AI — Standalone License Kit Launcher (Windows)
setlocal enabledelayedexpansion

cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
    set "PYTHON_EXEC=..\.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXEC=python"
)

"%PYTHON_EXEC%" license_console.py %*
pause
