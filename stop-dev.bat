@echo off
setlocal

cd /d "%~dp0"

echo ==========================================
echo Agent-BI - Dev Hybrid Shutdown
echo ==========================================

echo.
echo [1/3] Encerrando janela do backend local...
taskkill /FI "WINDOWTITLE eq Agent-BI Backend*" /T /F >nul 2>nul

echo [2/3] Encerrando janela do frontend local...
taskkill /FI "WINDOWTITLE eq Agent-BI Frontend*" /T /F >nul 2>nul

echo [3/3] Modo local rapido: nenhum container sera parado.

echo.
echo Ambiente de dev parado.
echo.

endlocal
