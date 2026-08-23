@echo off
chcp 65001 >nul
title Painel de Acompanhamento - Servidor Local

echo.
echo ════════════════════════════════════════════════════════
echo   PAINEL DE ACOMPANHAMENTO - Iniciador do Servidor Local
echo ════════════════════════════════════════════════════════
echo.

REM Verifica se Python está instalado
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python não encontrado!
    echo.
    echo Instale o Python 3.10+ em:
    echo   https://www.python.org/downloads/
    echo.
    echo ⚠️ IMPORTANTE: Marque "Add Python to PATH" na instalação
    echo.
    pause
    exit /b 1
)

echo ✓ Python encontrado:
python --version
echo.
echo Iniciando servidor...
echo.

REM Navega para a pasta do script
cd /d "%~dp0"

REM Inicia o servidor
python servidor_painel.py 8000

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Erro ao iniciar o servidor.
    echo.
    pause
)
