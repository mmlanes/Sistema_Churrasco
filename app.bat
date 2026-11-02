@echo off
title Calculadora e Gestao de Churrasco
cd /d "%~dp0"

echo ============================================================
echo   Iniciando Calculadora e Gestao de Churrasco
echo ============================================================
echo.

if exist ".venv\Scripts\activate.bat" (
    echo Ativando ambiente virtual .venv
    call ".venv\Scripts\activate.bat"
) else (
    echo Ambiente virtual nao encontrado. Usando Python padrao.
)

echo Iniciando o aplicativo Streamlit...
streamlit run app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocorreu um erro ao executar a aplicacao.
    pause
)
