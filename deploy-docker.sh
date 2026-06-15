#!/bin/bash

echo ""
echo "==============================================================================="
echo " [RAT CONTROL PANEL] - DOCKER DEPLOY"
echo "==============================================================================="
echo ""

echo "[STEP 1] Verificando Docker..."
if ! command -v docker &> /dev/null; then
    echo "[ERRO] Docker não está instalado"
    exit 1
fi
echo "[OK] Docker disponível"

echo ""
echo "[STEP 2] Parando container anterior (se existir)..."
docker-compose down 2>/dev/null || true
echo "[OK] Container anterior removido"

echo ""
echo "[STEP 3] Construindo imagem Docker..."
docker-compose build
if [ $? -ne 0 ]; then
    echo "[ERRO] Falha ao construir imagem Docker"
    exit 1
fi
echo "[OK] Imagem construída"

echo ""
echo "[STEP 4] Iniciando container..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo "[ERRO] Falha ao iniciar container"
    exit 1
fi
echo "[OK] Container iniciado"

echo ""
echo "[STEP 5] Aguardando container ficar healthy..."
sleep 5

docker-compose ps

echo ""
echo "==============================================================================="
echo " [SUCESSO] Painel rodando em http://localhost:5000"
echo "==============================================================================="
echo ""
echo "Para acessar os logs:"
echo "   docker logs -f rat-panel"
echo ""
echo "Para parar:"
echo "   docker-compose down"
echo ""
