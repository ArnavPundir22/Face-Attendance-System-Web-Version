@echo off
REM ============================================================
REM Windows Startup Script for BioSecure AI with Nginx Load Balancer
REM ============================================================

cd /d "%~dp0"

REM 1. Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call ".venv\Scripts\activate.bat"
)

REM 2. Ensure Waitress & RapidOCR dependencies are installed
python -c "import waitress" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing Waitress WSGI production server for Windows...
    pip install waitress
)

python -c "import rapidocr_onnxruntime" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing RapidOCR neural engine for ID card OCR...
    pip install rapidocr_onnxruntime
)

REM 3. Generate dynamic Nginx configuration & ensure portable Nginx is present
set "NGINX_PORT=8080"
set "BACKEND_PORT=8066"
python nginx\setup_nginx.py --os Windows

REM 4. Launch Nginx if available
set "NGINX_EXE=tools\nginx\nginx.exe"
if not exist "%NGINX_EXE%" goto :run_fallback

echo Starting Nginx Load Balancer on port %NGINX_PORT%...
taskkill /F /IM nginx.exe >nul 2>&1
start "" /B "%NGINX_EXE%" -p "%CD%\tools\nginx" -c "%CD%\nginx\nginx-runtime.conf"

echo ==========================================================
echo [INFO] BioSecure AI is LIVE!
echo [INFO] Frontend (Nginx Load Balancer): http://localhost:%NGINX_PORT%
echo [INFO] Backend WSGI Server:           http://127.0.0.1:%BACKEND_PORT%
echo [INFO] Load Balancing Algorithm:      Least Connections (least_conn)
echo ==========================================================

REM Run Waitress bound to localhost
waitress-serve --host=127.0.0.1 --port=%BACKEND_PORT% --threads=16 --channel-timeout=300 app:app

echo Shutting down Nginx...
"%NGINX_EXE%" -p "%CD%\tools\nginx" -s quit >nul 2>&1
taskkill /F /IM nginx.exe >nul 2>&1
goto :end

:run_fallback
REM 5. Fallback: Run Waitress directly on 0.0.0.0 so the app never breaks
echo ==========================================================
echo [INFO] Starting BioSecure AI with direct Waitress server...
echo [INFO] Access Application at: http://localhost:%BACKEND_PORT%
echo ==========================================================
waitress-serve --host=0.0.0.0 --port=%BACKEND_PORT% --threads=16 --channel-timeout=300 app:app

:end
pause
