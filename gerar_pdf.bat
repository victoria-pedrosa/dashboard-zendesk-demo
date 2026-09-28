@echo off
chcp 65001 >nul
echo ========================================
echo   Relatorio PDF Zendesk - Exemplo
echo ========================================
echo.

set PYTHON=C:\Users\Exemplo1\AppData\Local\Python\pythoncore-3.14-64\python.exe
cd /d "%~dp0"

echo Gerando PDF...
%PYTHON% gerar_pdf.py
if %errorlevel% neq 0 (
    echo.
    echo !! Erro ao gerar PDF. Verifique se a coleta ja foi executada.
    pause
    exit /b 1
)

echo.
echo PDF salvo na pasta data\
pause
