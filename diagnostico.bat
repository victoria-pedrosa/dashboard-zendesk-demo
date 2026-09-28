@echo off
chcp 65001 >nul
set PYTHON=C:\Users\Exemplo1\AppData\Local\Python\pythoncore-3.14-64\python.exe
set LOG=%~dp0data\diagnostico.log
cd /d "%~dp0"

mkdir data 2>nul

echo Testando instalacao de pacotes...
%PYTHON% -c "import slack_sdk; print('slack_sdk OK')" >> "%LOG%" 2>&1
%PYTHON% -c "import apscheduler; print('apscheduler OK')" >> "%LOG%" 2>&1
%PYTHON% -c "import pandas; print('pandas OK')" >> "%LOG%" 2>&1
%PYTHON% -c "import dotenv; print('dotenv OK')" >> "%LOG%" 2>&1
%PYTHON% -c "import fpdf; print('fpdf OK')" >> "%LOG%" 2>&1
%PYTHON% -c "from slack_sdk.socket_mode.builtin import SocketModeClient; print('socket_mode OK')" >> "%LOG%" 2>&1
echo --- >> "%LOG%"
echo Testando config... >> "%LOG%"
%PYTHON% -c "from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN; print('BOT:', SLACK_BOT_TOKEN[:20] if SLACK_BOT_TOKEN else 'AUSENTE'); print('APP:', SLACK_APP_TOKEN[:20] if SLACK_APP_TOKEN else 'AUSENTE')" >> "%LOG%" 2>&1
echo --- >> "%LOG%"
echo Rodando scheduler por 10 segundos... >> "%LOG%"
%PYTHON% -c "
import sys, os, logging
logging.basicConfig(level=logging.INFO)
os.makedirs('data', exist_ok=True)
try:
    from scheduler import *
    print('scheduler importou OK')
except Exception as e:
    print('ERRO no scheduler:', e)
" >> "%LOG%" 2>&1

notepad "%LOG%"
