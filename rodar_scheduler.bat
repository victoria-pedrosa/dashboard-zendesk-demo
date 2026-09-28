@echo off
chcp 65001 >nul
echo ========================================
echo   Scheduler Zendesk - Exemplo
echo ========================================
echo.
echo Este processo roda em segundo plano e:
echo  - Coleta tickets a cada 5 minutos
echo  - Envia alertas de atraso (mais de 2h)
echo  - Envia relatorio diario as 17h
echo.
echo Para parar: feche esta janela ou pressione Ctrl+C
echo.

set PYTHON=C:\Users\Exemplo1\AppData\Local\Python\pythoncore-3.14-64\python.exe
cd /d "%~dp0"

%PYTHON% scheduler.py

pause
