@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ===============================================================================
echo  [RAT CONTROL PANEL] - DOCKER DEPLOY
echo ===============================================================================
echo.

echo [STEP 1] Verificando Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Docker não instalado ou não está no PATH
    exit /b 1
)
echo [OK] Docker disponível

echo.
echo [STEP 2] Parando container anterior (se existir)...
docker-compose down 2>nul
echo [OK] Container anterior removido

echo.
echo [STEP 3] Construindo imagem Docker...
docker-compose build
if errorlevel 1 (
    echo [ERRO] Falha ao construir imagem Docker
    exit /b 1
)
echo [OK] Imagem construída

echo.
echo [STEP 4] Iniciando container...
docker-compose up -d
if errorlevel 1 (
    echo [ERRO] Falha ao iniciar container
    exit /b 1
)
echo [OK] Container iniciado

echo.
echo [STEP 5] Aguardando container ficar healthy...
timeout /t 5 /nobreak

docker-compose ps

echo.
echo ===============================================================================
echo  [SUCESSO] Painel rodando em http://localhost:5000
echo ===============================================================================
echo.
echo Para acessar os logs:
echo   docker logs -f rat-panel
echo.
echo Para parar:
echo   docker-compose down
echo.
pause
