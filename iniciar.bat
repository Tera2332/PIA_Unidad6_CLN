@echo off
cd /d "%~dp0"
chcp 65001 >nul
title Sazon Urbano
echo ============================================
echo   Sazon Urbano - Sistema de pedidos
echo ============================================
echo.
if exist ".venv\Scripts\uvicorn.exe" goto :arrancar
if exist ".venv" rmdir /s /q ".venv"

echo [1/2] Creando entorno virtual por primera vez...
set "PY=py -3"
where python >nul 2>&1 && set "PY=python"
%PY% -m venv .venv
if errorlevel 1 goto :error
echo [2/2] Instalando dependencias (puede tardar unos minutos)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
echo.
echo Listo, entorno preparado.
echo.

:arrancar
set SEED_ON_START=true
set STOCK_CRITICO=5
echo  Interfaz:  http://localhost:8000
echo  API docs:  http://localhost:8000/docs
echo.
echo  En este equipo:            localhost:8000
echo  Desde otro dispositivo:    http://IP-DE-ESTA-PC:8000
echo.
echo  Presiona Ctrl+C para detener el servidor.
echo.
start "" http://localhost:8000
".venv\Scripts\uvicorn.exe" src.api.main:crear_app --factory --host 0.0.0.0 --port 8000
goto :eof
:error
echo.
echo *** Fallo el arranque.
echo *** Verifica que Python este instalado y marcado "Add to PATH".
echo.
pause
