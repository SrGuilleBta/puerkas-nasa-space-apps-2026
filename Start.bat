@echo off
setlocal
cd /d "%~dp0"

echo ==== Puerkas - NASA Space Apps 2026 ====
echo.

REM 1) Docker Desktop debe estar corriendo
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker no esta corriendo.
    echo Abre Docker Desktop, espera a que inicie y vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

REM 2) Crear .env la primera vez
if not exist ".env" (
    echo Creando .env desde .env.example...
    copy /y ".env.example" ".env" >nul
)

REM 3) Construir y levantar el contenedor
echo Construyendo y levantando el contenedor. La primera vez tarda unos minutos...
docker compose up --build -d
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo levantar el contenedor. Revisa el mensaje de arriba.
    echo.
    pause
    exit /b 1
)

REM 4) Esperar a que la app responda
echo.
echo Esperando a que la app responda...
set TRIES=0

:wait
curl -s -f http://localhost:8000/api/health >nul 2>&1
if not errorlevel 1 goto ready
set /a TRIES+=1
if %TRIES% GEQ 30 goto timeout
ping -n 3 127.0.0.1 >nul
goto wait

:ready
echo.
echo ================================================
echo  Listo. La app esta corriendo en:
echo    http://localhost:8000        (app)
echo    http://localhost:8000/docs   (documentacion API)
echo.
echo  Ver logs:  docker logs -f puerkas
echo  Apagar:    docker compose down
echo ================================================
start "" http://localhost:8000
echo.
pause
exit /b 0

:timeout
echo.
echo [ERROR] La app no respondio a tiempo.
echo Revisa los logs con: docker logs puerkas
echo.
pause
exit /b 1
