@echo off
setlocal

cd /d "%~dp0"

echo ==============================================================
echo [INFO] Agent-BI - Local Fast Startup
echo [INFO] Ambiente: Sem Docker / SQLite / Django local / Next.js
echo ==============================================================

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Nao encontrei .venv\Scripts\python.exe
  echo [WARNING] Crie/ative a virtualenv antes de usar este script.
  pause
  exit /b 1
)

if not exist "frontend\package.json" (
  echo [ERROR] Nao encontrei o frontend em frontend\package.json
  pause
  exit /b 1
)

echo.
echo [INFO] ^(1/4^) Aplicando migracoes no SQLite local...
".venv\Scripts\python.exe" manage.py migrate --settings=config.settings.local_fast
if errorlevel 1 (
  echo [ERROR] Falha ao aplicar migracoes locais no Django.
  pause
  exit /b 1
)
echo [SUCCESS] Banco de dados validado com sucesso!

echo.
echo [INFO] ^(2/4^) Checando ou seedando Tenant Mock Local...
".venv\Scripts\python.exe" manage.py shell -c "from apps.users.models import Tenant; Tenant.objects.get_or_create(slug='default', defaults={'name': 'Default Tenant'})" --settings=config.settings.local_fast
echo [SUCCESS] Tenant mock 'default' validado!

echo.
echo [INFO] ^(3/4^) Subindo backend Django (porta 8000)...
start "Agent-BI Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\activate.bat && python manage.py runserver 0.0.0.0:8000 --settings=config.settings.local_fast"

echo.
echo [INFO] ^(4/4^) Construindo e subindo frontend Next.js (porta 3000)...
start "Agent-BI Frontend" cmd /k "cd /d %~dp0frontend && npm run build && npm run start:local"

echo.
echo ==============================================================
echo [SUCCESS] Pipeline de subida concluido! Acompanhe as 2 janelas novas.
echo.
echo URLs mapeadas:
echo - Frontend: http://127.0.0.1:3000
echo - Backend:  http://127.0.0.1:8000
echo - API Docs: http://127.0.0.1:8000/api/docs/
echo ==============================================================
echo Se precisar do modo com Docker depois, use start-dev-hybrid.bat
echo.

endlocal

