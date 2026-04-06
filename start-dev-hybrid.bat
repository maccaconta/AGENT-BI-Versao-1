@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo Agent-BI - Dev Hybrid Startup
echo Infra via Docker / Backend local / Frontend local
echo ==========================================

if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Nao encontrei .venv\Scripts\python.exe
  pause
  exit /b 1
)

echo.
echo [1/3] Subindo infra local: Postgres, Redis e MinIO...
docker compose up -d db redis minio
if errorlevel 1 (
  echo [ERRO] Falha ao subir a infra Docker.
  pause
  exit /b 1
)

echo.
echo [2/3] Abrindo backend Django local...
start "Agent-BI Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\activate.bat && python manage.py runserver 0.0.0.0:8000 --settings=config.settings.development"

echo.
echo [3/3] Abrindo frontend Next.js local...
start "Agent-BI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo URLs:
echo - Frontend: http://127.0.0.1:3000
echo - Backend:  http://127.0.0.1:8000
echo - API Docs: http://127.0.0.1:8000/api/docs/
echo - MinIO:    http://127.0.0.1:19001
echo.

endlocal
