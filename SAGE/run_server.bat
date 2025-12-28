@echo off
REM SAGE API Server Startup Script
REM ================================

echo.
echo  ====================================
echo   SAGE API Server
echo  ====================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Set default values
set HOST=0.0.0.0
set PORT=8000

REM Parse arguments
if not "%1"=="" set HOST=%1
if not "%2"=="" set PORT=%2

echo  Host: %HOST%
echo  Port: %PORT%
echo.
echo  Local:   http://localhost:%PORT%
echo  Network: http://%COMPUTERNAME%:%PORT%
echo  Docs:    http://localhost:%PORT%/docs
echo.
echo  Press Ctrl+C to stop the server
echo  ====================================
echo.

REM Start server
cd /d "%~dp0"
python -m src.api --host %HOST% --port %PORT%

pause
