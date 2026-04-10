@echo off
setlocal
echo ==========================================
echo   Agent-BI: Inicializando Banco de Dados
echo ==========================================
echo.
echo [1/5] Aplicando Migrações...
python manage.py migrate
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha ao aplicar migracoes.
    goto :error
)
echo [2/5] Populando Agent Prompts...
python manage.py seed_agent_prompts
if %ERRORLEVEL% NEQ 0 echo [AVISO] Falha em seed_agent_prompts.
echo [3/5] Populando Especialistas...
python manage.py seed_specialists
if %ERRORLEVEL% NEQ 0 echo [AVISO] Falha em seed_specialists.
echo [4/5] Populando Banking Prompts...
python manage.py seed_banking_prompts
if %ERRORLEVEL% NEQ 0 echo [AVISO] Falha em seed_banking_prompts.
echo [5/5] Populando Credit Risk...
python manage.py seed_credit_risk_enhanced
if %ERRORLEVEL% NEQ 0 echo [AVISO] Falha em seed_credit_risk_enhanced.
echo.
echo ==========================================
echo   Setup Finalizado com Sucesso!
echo ==========================================
echo.
pause
exit /b 0
:error
echo.
echo Ocorreu um erro critico durante o setup.
pause
exit /b 1