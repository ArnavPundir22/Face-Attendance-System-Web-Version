@echo off
:: Batch file to launch Cloudflare HTTPS Tunnel for BioSecure AI on Windows
:: Download cloudflared.exe from https://github.com/cloudflare/cloudflared/releases

cd /d "%~dp0"

if not exist cloudflared.exe (
    echo [INFO] cloudflared.exe not found in current directory.
    echo Please download cloudflared-windows-amd64.exe, rename it to cloudflared.exe and place it in this folder.
    echo Download URL: https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
    echo.
    pause
    exit /b
)

echo Starting Cloudflare HTTPS Tunnel for http://localhost:5000 ...
echo Share the generated https://*.trycloudflare.com link with remote users for camera access!
echo.
cloudflared.exe tunnel --url http://localhost:5000
pause
