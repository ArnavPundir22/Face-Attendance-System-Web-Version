@echo off
REM BioSecure AI — Interactive Licensing Console Launcher (Windows)
REM Delegates to self-contained license_kit\run_console.bat
cd /d "%~dp0license_kit"
call run_console.bat %*
