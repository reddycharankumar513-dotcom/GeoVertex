@echo off
echo ===================================================
echo Starting GeoVertex Cadastral Intelligence Platform
echo ===================================================

start "GeoVertex Backend (FastAPI)" cmd /k "cd /d %~dp0backend && ..\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

start "GeoVertex Frontend (React + Vite)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ===================================================
echo Services Started:
echo  - Frontend Web App: http://localhost:5173
echo  - Backend API:      http://127.0.0.1:8000
echo  - Interactive Docs: http://127.0.0.1:8000/docs
echo.
echo Default Admin Login:
echo  - Email:    admin@geovertex.local
echo  - Password: GeoVertexAdmin2026!
echo ===================================================
echo.
pause
