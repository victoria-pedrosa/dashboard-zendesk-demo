Dim shell, pasta
Set shell = CreateObject("WScript.Shell")
' Usa o diretório onde o .vbs está — funciona em qualquer máquina
pasta = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
shell.CurrentDirectory = pasta
' Usa o python que estiver no PATH do sistema
shell.Run "python """ & pasta & "\scheduler.py""", 0, False
