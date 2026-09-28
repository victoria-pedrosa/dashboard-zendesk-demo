@echo off
chcp 65001 >nul
set PYTHON=C:\Users\Exemplo1\AppData\Local\Python\pythoncore-3.14-64\python.exe

echo Instalando dependencias...
"%PYTHON%" -m pip install reportlab --quiet
echo reportlab OK

"%PYTHON%" -m pip install slack-sdk apscheduler python-dotenv --quiet
echo demais pacotes OK

echo.
echo Tudo instalado! Pode fechar esta janela.
pause
