@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title FFmpeg Multi-Video Downloader
cd /d "%~dp0"

echo ========================================================
echo        FFmpeg Multi-Video Downloader
echo ========================================================
echo Iniciando interface visual...
echo.

python app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocorreu um erro ao executar a aplicacao.
    pause
)
