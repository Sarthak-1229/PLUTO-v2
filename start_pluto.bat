@echo off
echo Starting PLUTO v2 AI Agent...

:: Wait a few seconds for server to start before opening browser
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8080"

:: Start the Python backend (assuming dependencies are installed in current env)
python app.py
