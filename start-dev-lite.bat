@echo off
setlocal

cd /d "%~dp0"

echo ==============================================================
echo [INFO] Agent-BI - Lite Startup (No Migrations / No Seed)
echo [INFO] Apenas subindo os servidores...
echo ==============================================================

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Nao encontrei .venv\Scripts\python.exe
  pause
  exit /b 1
)

if not exist "frontend\package.json" (
  echo [ERROR] Nao encontrei o frontend em frontend\package.json
  pause
  exit /b 1
)

echo.
echo [INFO] Subindo backend Django (porta 8000)...
start "Agent-BI Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\activate.bat && python manage.py runserver 0.0.0.0:8000 --settings=config.settings.local_fast"

echo.
echo [INFO] Subindo frontend Next.js (porta 3000)...
:: Usando dev mode para velocidade, se preferir build+start use o start-dev.bat original
start "Agent-BI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ==============================================================
echo [SUCCESS] Servidores em processo de inicializacao!
echo.
echo URLs:
echo - Frontend: http://127.0.0.1:3000
echo - Backend:  http://127.0.0.1:8000
echo ==============================================================

endlocal
