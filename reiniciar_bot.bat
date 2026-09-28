@echo off
chcp 65001 >nul

:: Solicita privilégios de administrador automaticamente
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ============================================
echo  Parando o bot...
echo ============================================
taskkill /F /IM python.exe >nul 2>&1
timeout /t 3 /nobreak >nul

echo ============================================
echo  Reiniciando o bot (modo silencioso)...
echo ============================================
cd /d "%~dp0"
cscript //nologo "%~dp0iniciar_silencioso.vbs"

echo.
echo Bot reiniciado com sucesso!
echo Aguarde 5 segundos e abra a aba Home do bot no Slack.
echo ============================================
timeout /t 5
