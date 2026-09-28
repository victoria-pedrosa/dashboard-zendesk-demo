@echo off
chcp 65001 >nul
echo Instalando inicializacao automatica...

set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS=%~dp0iniciar_silencioso.vbs

copy "%VBS%" "%STARTUP%\DashboardZendesk.vbs" /Y >nul

if exist "%STARTUP%\DashboardZendesk.vbs" (
    echo [OK] Instalado na pasta de Inicializacao do Windows.
    echo Iniciando agora...
    wscript.exe "%STARTUP%\DashboardZendesk.vbs"
    echo [OK] Rodando em segundo plano.
) else (
    echo [ERRO] Nao foi possivel copiar o arquivo.
)

pause
