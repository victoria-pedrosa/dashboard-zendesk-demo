@echo off
chcp 65001 >nul
echo ========================================
echo   Dashboard Zendesk - Exemplo
echo ========================================
echo.

set PYTHON=C:\Users\Exemplo1\AppData\Local\Python\pythoncore-3.14-64\python.exe
cd /d "%~dp0"

echo [1/2] Coletando tickets do Slack...
echo.
%PYTHON% collector.py
if %errorlevel% neq 0 (
    echo.
    echo !! ERRO na coleta. Verifique se o token no .env esta correto.
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] Abrindo dashboard no navegador...
echo (Para fechar, pressione Ctrl+C nesta janela)
echo.
%PYTHON% -m streamlit run dashboard.py --server.headless false

pause
