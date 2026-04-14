@echo off
title Lanzador GlassApp (Servidor + Red Activa)
color 0B

echo ===================================================
echo   Iniciando Servidor Flask y Tailscale Funnel...
echo ===================================================
echo.

:: 1. Liberar el puerto 5000 de forma segura
:: Esto evita el error de "address already in use" buscando y matando solo el proceso del puerto 5000
echo [*] Limpiando procesos bloqueados en el puerto 5000...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do taskkill /f /pid %%a > nul 2>&1
timeout /t 1 /nobreak > nul

:: 2. Iniciar Servidor Flask (app.py iniciara el Funnel internamente)
echo [1/2] Arrancando el entorno virtual y el Servidor de Python...
:: IMPORTANTE: Abre una nueva ventana activando el entorno virtual (env) y ejecutando la app
start "GlassApp Server" cmd /k "call env\Scripts\activate && python app.py"

:: Damos 5 segundos para que Flask y Tailscale arranquen bien
timeout /t 5 /nobreak > nul

:: 3. Abrir Navegador
echo [2/2] Abriendo el panel de administracion en tu navegador local...
start http://127.0.0.1:5000

echo.
echo ===================================================
echo  !TODO LISTO!
echo  La aplicacion y el tunel estan en linea.
echo.
echo  [ ! ] MODO RED ACTIVA HABILITADO [ ! ]
echo  Tu pantalla podra apagarse para ahorrar energia,
echo  pero enviaremos latidos (pings) cada 60 segundos
echo  para que la tarjeta de red y Tailscale Funnel
echo  NO se desconecten.
echo  MINIMIZALA PERO NO LA CIERRES.
echo ===================================================

:: Loop de Red Activa (Keep-Alive)
:latido

:: 1. Manda un pulso al servidor central de Tailscale para mantener el tunel
ping 100.100.100.100 -n 1 -w 2000 > nul 2>&1

:: 2. Manda un pulso a Google para mantener activa la placa de red
ping 8.8.8.8 -n 1 -w 2000 > nul 2>&1

:: Espera 60 segundos y vuelve a latir
timeout /t 60 /nobreak > nul
goto latido