@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ==============================================================
echo [INFO] Agent-BI - Local Setup
echo [INFO] Preparando ambiente Python, Node e dependencias
echo ==============================================================

REM ==============================================================
REM Validacoes basicas
REM ==============================================================
if not exist "manage.py" (
  echo [ERROR] Nao encontrei manage.py na raiz do projeto.
  pause
  exit /b 1
)

if not exist "frontend\package.json" (
  echo [ERROR] Nao encontrei frontend\package.json
  pause
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python nao encontrado no PATH.
  echo [WARNING] Instale Python 3 e marque a opcao "Add Python to PATH".
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm nao encontrado no PATH.
  echo [WARNING] Instale Node.js LTS para obter node e npm.
  pause
  exit /b 1
)

REM ==============================================================
REM Criar virtualenv
REM ==============================================================
if not exist ".venv\Scripts\python.exe" (
  echo.
  echo [INFO] Criando virtualenv em .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Falha ao criar a virtualenv.
    pause
    exit /b 1
  )
) else (
  echo.
  echo [INFO] Virtualenv .venv ja existe.
)

echo.
echo [INFO] Atualizando pip, setuptools e wheel...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
  echo [ERROR] Falha ao atualizar pip/setuptools/wheel.
  pause
  exit /b 1
)

REM ==============================================================
REM Instalar dependencias backend
REM ==============================================================
echo.
echo [INFO] Instalando dependencias Python...

if exist "requirements.txt" (
  pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Falha ao instalar requirements.txt
    pause
    exit /b 1
  )
) else if exist "requirements\local.txt" (
  pip install -r requirements\local.txt
  if errorlevel 1 (
    echo [ERROR] Falha ao instalar requirements\local.txt
    pause
    exit /b 1
  )
) else if exist "pyproject.toml" (
  echo [WARNING] Encontrei pyproject.toml, mas este script nao sabe qual gerenciador usar automaticamente.
  echo [WARNING] Se o projeto usa Poetry ou uv, instale as dependencias manualmente.
) else (
  echo [WARNING] Nao encontrei requirements.txt, requirements\local.txt ou pyproject.toml
)

REM ==============================================================
REM Criar .env se nao existir
REM ==============================================================
echo.
if not exist ".env" (
  echo [INFO] Arquivo .env nao encontrado. Criando .env basico...
  (
    echo SECRET_KEY=django-insecure-local-dev-key-123456789
    echo DEBUG=True
    echo ALLOWED_HOSTS=127.0.0.1,localhost,0.0.0.0
  ) > .env
  echo [SUCCESS] .env criado com configuracao basica.
) else (
  echo [INFO] Arquivo .env ja existe.
)

REM ==============================================================
REM Instalar dependencias frontend
REM ==============================================================
echo.
echo [INFO] Instalando dependencias do frontend...
cd /d "%~dp0frontend"
call npm install
if errorlevel 1 (
  echo [ERROR] Falha ao instalar dependencias do frontend.
  pause
  exit /b 1
)

cd /d "%~dp0"

echo.
echo ==============================================================
echo [SUCCESS] Setup local concluido com sucesso!
echo.
echo Proximos passos:
echo 1. Revise o arquivo .env
echo 2. Rode o script de start
echo ==============================================================

endlocal