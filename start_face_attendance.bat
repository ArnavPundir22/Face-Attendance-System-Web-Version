@echo off
:: Windows Startup Script for BioSecure AI with Nginx Load Balancer
setlocal enabledelayedexpansion

cd /d "%~dp0"

:: 1. Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] .venv virtual environment not found. Running using system Python.
)

:: 2. Ensure Waitress & RapidOCR dependencies are installed
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

:: 3. Generate dynamic Nginx configuration for Windows
python nginx\setup_nginx.py --os Windows > "%TEMP%\nginx_setup_env.txt" 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=1,2 delims==" %%A in (%TEMP%\nginx_setup_env.txt) do (
        if "%%A"=="NGINX_PORT" set NGINX_PORT=%%B
        if "%%A"=="BACKEND_PORT" set BACKEND_PORT=%%B
    )
)
if "%NGINX_PORT%"=="" set NGINX_PORT=8080
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8066

:: 4. Check for portable Nginx (tools\nginx\nginx.exe) or download it automatically
set NGINX_EXE=tools\nginx\nginx.exe
if not exist "%NGINX_EXE%" (
    echo ==========================================================
    echo [INFO] Portable Nginx for Windows not detected.
    echo Downloading portable Nginx from official nginx.org mirror...
    echo ==========================================================
    if not exist tools mkdir tools
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { (New-Object Net.WebClient).DownloadFile('https://nginx.org/download/nginx-1.26.2.zip', 'tools\nginx.zip'); Expand-Archive -Path 'tools\nginx.zip' -DestinationPath 'tools'; Rename-Item -Path 'tools\nginx-1.26.2' -NewName 'nginx'; Remove-Item 'tools\nginx.zip'; exit 0 } catch { exit 1 }"
    if %errorlevel% neq 0 (
        echo [WARNING] Automatic Nginx download failed (offline or blocked).
    )
)

:: 5. Launch Nginx if available
if exist "%NGINX_EXE%" (
    echo Starting Nginx Load Balancer on port %NGINX_PORT%...
    taskkill /F /IM nginx.exe >nul 2>&1
    start "" /B "%NGINX_EXE%" -p "%CD%\tools\nginx" -c "%CD%\nginx\nginx-runtime.conf"

    echo ==========================================================
    echo 🚀 BioSecure AI is LIVE!
    echo 🌐 Frontend (Nginx Load Balancer): http://localhost:%NGINX_PORT%
    echo ⚙️ Backend WSGI Server:          http://127.0.0.1:%BACKEND_PORT%
    echo ⚖️ Load Balancing Algorithm:     Least Connections (least_conn)
    echo ==========================================================

    :: Run Waitress bound to localhost
    waitress-serve --host=127.0.0.1 --port=%BACKEND_PORT% --threads=16 --channel-timeout=300 app:app

    echo Shutting down Nginx...
    "%NGINX_EXE%" -p "%CD%\tools\nginx" -s quit >nul 2>&1
    taskkill /F /IM nginx.exe >nul 2>&1
    goto :end
)

:: 6. Fallback: Run Waitress directly on 0.0.0.0 so the app never breaks
echo ==========================================================
echo [INFO] Starting BioSecure AI with direct Waitress server...
echo 🌐 Access Application at: http://localhost:%BACKEND_PORT%
echo ==========================================================
waitress-serve --host=0.0.0.0 --port=%BACKEND_PORT% --threads=16 --channel-timeout=300 app:app

:end
pause
