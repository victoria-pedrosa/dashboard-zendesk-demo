@echo off
chcp 65001 > nul
echo.
echo ========================================
echo  Dashboard de Mencoes Slack - Exemplo
echo ========================================
echo.

if "%1"=="" (
    echo Buscando mencoes do mes atual...
    python mencoes.py
) else (
    echo Buscando mencoes de %1 ate %2...
    python mencoes.py %1 %2
)

echo.
pause
