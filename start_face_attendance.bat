@echo off
REM ============================================================
REM Windows Startup Script for BioSecure AI with Nginx Load Balancer
REM ============================================================

cd /d "%~dp0"

REM Disable QuickEdit mode early so mouse clicks inside console never freeze server stdout
powershell -NoProfile -ExecutionPolicy Bypass -Command "$h = (Add-Type -MemberDefinition '[DllImport(\"kernel32.dll\")] public static extern IntPtr GetStdHandle(int n); [DllImport(\"kernel32.dll\")] public static extern bool GetConsoleMode(IntPtr h, out uint m); [DllImport(\"kernel32.dll\")] public static extern bool SetConsoleMode(IntPtr h, uint m);' -Name 'K32' -Namespace 'Win' -PassThru)::GetStdHandle(-10); $m = 0; if ([Win.K32]::GetConsoleMode($h, [ref]$m)) { [Win.K32]::SetConsoleMode($h, ($m -band -bnot 0x40) -bor 0x80) }" >nul 2>&1

REM 1. Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call ".venv\Scripts\activate.bat"
)

REM 1.1 Auto-expose NVIDIA CUDA/cuDNN DLL paths & install missing GPU dependencies
set "NVIDIA_DIR="
if defined VIRTUAL_ENV if exist "%VIRTUAL_ENV%\Lib\site-packages\nvidia" set "NVIDIA_DIR=%VIRTUAL_ENV%\Lib\site-packages\nvidia"
if not defined NVIDIA_DIR if exist ".venv\Lib\site-packages\nvidia" set "NVIDIA_DIR=.venv\Lib\site-packages\nvidia"

if defined NVIDIA_DIR (
    REM Auto-install missing cuFFT dependency if CUDA 12 packages are present
    if exist "%NVIDIA_DIR%\cublas" (
        if not exist "%NVIDIA_DIR%\cufft" (
            echo [INFO] Installing missing NVIDIA cuFFT GPU dependency for RTX GPU...
            pip install nvidia-cufft-cu12 nvidia-curand-cu12
        )
    )
    for /d %%D in ("%NVIDIA_DIR%\*") do (
        if exist "%%D\bin" call set "PATH=%%D\bin;%%PATH%%"
    )
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
