@echo off
REM ============================================================
REM Windows Startup Script for BioSecure AI with Nginx Load Balancer
REM ============================================================

cd /d "%~dp0"

REM 1. Activate virtual environment if it exists
if not exist ".venv\Scripts\activate.bat" goto :no_venv
echo Activating virtual environment...
call ".venv\Scripts\activate.bat"
goto :venv_done

:no_venv
echo [WARNING] .venv virtual environment not found. Running using system Python.

:venv_done

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

REM 3. Generate dynamic Nginx configuration for Windows
set "NGINX_PORT="
set "BACKEND_PORT="
if exist "%TEMP%\nginx_setup_env.txt" del /f /q "%TEMP%\nginx_setup_env.txt" >nul 2>&1
python nginx\setup_nginx.py --os Windows > "%TEMP%\nginx_setup_env.txt" 2>nul
if %errorlevel% equ 0 (
    if exist "%TEMP%\nginx_setup_env.txt" (
        for /f "usebackq tokens=1,2 delims==" %%A in ("%TEMP%\nginx_setup_env.txt") do (
            if "%%A"=="NGINX_PORT" set "NGINX_PORT=%%B"
            if "%%A"=="BACKEND_PORT" set "BACKEND_PORT=%%B"
        )
    )
)
if "%NGINX_PORT%"=="" set "NGINX_PORT=8080"
if "%BACKEND_PORT%"=="" set "BACKEND_PORT=8066"

REM 4. Check for portable Nginx (tools\nginx\nginx.exe) or download it automatically
set "NGINX_EXE=tools\nginx\nginx.exe"
if exist "%NGINX_EXE%" goto :nginx_ready

echo ==========================================================
echo [INFO] Portable Nginx for Windows not detected.
echo Downloading portable Nginx from official nginx.org mirror...
echo ==========================================================
if not exist tools mkdir tools

REM Attempt fast download with curl and tar if available on Windows 10/11
curl.exe -Lo tools\nginx.zip https://nginx.org/download/nginx-1.26.2.zip >nul 2>&1
if %errorlevel% equ 0 (
    tar.exe -xf tools\nginx.zip -C tools >nul 2>&1
    if exist tools\nginx-1.26.2 (
        move tools\nginx-1.26.2 tools\nginx >nul 2>&1
        del /f /q tools\nginx.zip >nul 2>&1
    )
)

REM Fallback to PowerShell download if curl/tar was not available
if not exist "%NGINX_EXE%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference = 'SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri 'https://nginx.org/download/nginx-1.26.2.zip' -OutFile 'tools\nginx.zip'; Expand-Archive -Path 'tools\nginx.zip' -DestinationPath 'tools' -Force; if (Test-Path 'tools\nginx-1.26.2') { Move-Item -Path 'tools\nginx-1.26.2' -Destination 'tools\nginx' -Force }; if (Test-Path 'tools\nginx.zip') { Remove-Item 'tools\nginx.zip' -Force } } catch {}"
)

if not exist "%NGINX_EXE%" (
    echo [WARNING] Automatic Nginx download failed (offline or blocked).
)

:nginx_ready

REM 5. Launch Nginx if available
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
REM 6. Fallback: Run Waitress directly on 0.0.0.0 so the app never breaks
echo ==========================================================
echo [INFO] Starting BioSecure AI with direct Waitress server...
echo [INFO] Access Application at: http://localhost:%BACKEND_PORT%
echo ==========================================================
waitress-serve --host=0.0.0.0 --port=%BACKEND_PORT% --threads=16 --channel-timeout=300 app:app

:end
pause
