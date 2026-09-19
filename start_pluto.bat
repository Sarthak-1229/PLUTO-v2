@echo off
title PLUTO v2 - AI Research Assistant
cd /d "%~dp0"

:: Check if Ollama is already running
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | findstr /i ollama.exe >nul
if %errorlevel% neq 0 (
    echo Starting Ollama server...
    start "" "C:\Users\Sarthak\AppData\Local\Programs\Ollama\ollama.exe" serve
    timeout /t 5 /nobreak >nul
) else (
    echo Ollama is already running.
)

:: Ensure model is loaded
echo Loading qwen2.5:7b model...
"C:\Users\Sarthak\AppData\Local\Programs\Ollama\ollama.exe" ps >nul 2>&1
if %errorlevel% neq 0 (
    echo Pulling/ensuring model...
    start "" /min "C:\Users\Sarthak\AppData\Local\Programs\Ollama\ollama.exe" pull qwen2.5:7b
)

:: Start FastAPI server
echo Starting PLUTO v2 server...
start "" /min cmd /c "python -m uvicorn app:app --host 127.0.0.1 --port 8000"

:: Wait for server to start
timeout /t 3 /nobreak >nul

:: Open browser
echo Opening PLUTO v2 in browser...
start "" http://127.0.0.1:8000

echo.
echo ========================================
echo PLUTO v2 is starting up!
echo ========================================
echo.
echo Server: http://127.0.0.1:8000
echo Model: qwen2.5:7b
echo.
echo This window will close in 5 seconds...
echo.
timeout /t 5 /nobreak >nul
exit
