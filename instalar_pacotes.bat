@echo off
chcp 65001 >nul
echo ========================================
echo  Instalando pacotes necessarios...
echo ========================================
echo.

set PYTHON=C:\Users\Exemplo1\AppData\Local\Python\pythoncore-3.14-64\python.exe
cd /d "%~dp0"

%PYTHON% -m pip install slack-sdk apscheduler fpdf2 python-dotenv --quiet

echo.
echo [OK] Pacotes instalados!
echo.
echo Instalando inicializacao automatica...

set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
copy "%~dp0iniciar_silencioso.vbs" "%STARTUP%\DashboardZendesk.vbs" /Y >nul

echo [OK] Dashboard vai iniciar automaticamente com o Windows.
echo.
echo Iniciando agora em segundo plano...
wscript.exe "%STARTUP%\DashboardZendesk.vbs"

echo [OK] Pronto! Pode fechar esta janela.
echo.
pause
