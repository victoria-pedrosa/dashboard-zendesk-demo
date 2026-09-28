@echo off
chcp 65001 >nul
echo ========================================
echo   Dashboard de Mencoes - Exemplo
echo ========================================
echo.
echo Mantenha esta janela aberta.
echo Os botoes do dashboard (Atualizar, Hoje,
echo Esta semana, Filtrar setor, PDF) so
echo funcionam enquanto esta janela estiver aberta.
echo.
echo Abrindo a aba Home do bot no Slack vai
echo carregar o dashboard automaticamente.
echo.
echo Para parar: feche esta janela ou Ctrl+C
echo ========================================
echo.

set PYTHON=C:\Users\Exemplo1\AppData\Local\Python\pythoncore-3.14-64\python.exe
cd /d "%~dp0"

%PYTHON% socket_handler.py

pause
