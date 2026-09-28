@echo off
set PYTHON=C:\Users\Exemplo1\AppData\Local\Python\pythoncore-3.14-64\python.exe
cd /d "%~dp0"
echo Testando scheduler...
%PYTHON% scheduler.py
pause
