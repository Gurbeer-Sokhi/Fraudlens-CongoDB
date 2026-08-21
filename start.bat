@echo off
REM Start FraudLens backend and frontend (Windows)
echo Starting FraudLens...

start "FraudLens API" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
timeout /t 3 /nobreak > nul
start "FraudLens UI" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo API:  http://localhost:8000/docs
echo UI:   http://localhost:5173
