@echo off
chcp 65001 > nul
echo.
echo  ========================================================
echo  EXTRATOR DE DIAGNÓSTICO J.A.R.V.I.S
echo  ========================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERRO] Pasta 'venv' nao encontrada! 
    echo Certifique-se de que este arquivo esta na pasta raiz do Jarvis.
    pause
    exit /b
)

echo Rodando diagnostico via VENV...
echo.
venv\Scripts\python.exe diagnostico_geral.py

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] O diagnostico falhou criticamente (Erro: %errorlevel%).
    pause
)
exit
