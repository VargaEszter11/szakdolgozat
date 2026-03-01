@echo off
cd /d "%~dp0"

echo ========================================
echo        Starting TravelApp
echo ========================================
echo.

start "TravelApp" cmd /c "cd /d backend && python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"

echo Waiting for server to start...
timeout /t 3 /nobreak >nul

start http://localhost:8000

echo.
echo TravelApp is running at http://localhost:8000
echo Close the "TravelApp" window to stop.
echo.
pause
