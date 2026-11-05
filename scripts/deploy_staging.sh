#!/usr/bin/env bash
set -e

echo "=========================================="
echo "   FCN TI - Deploy do Ambiente Staging    "
echo "=========================================="

if [ ! -f .env.staging ]; then
    echo "[ERRO] Arquivo .env.staging nao encontrado!"
    echo "Copie o arquivo .env.staging.example para .env.staging e configure suas variaveis."
    exit 1
fi

echo "==> Construindo imagens (Gunicorn + Nginx)..."
docker compose --env-file .env.staging -f docker-compose.staging.yml build

echo "==> Subindo containers em background..."
docker compose --env-file .env.staging -f docker-compose.staging.yml up -d --remove-orphans

echo "==> Aguardando serviços subirem e verificando status..."
docker compose --env-file .env.staging -f docker-compose.staging.yml ps

echo "=========================================="
echo " Deploy concluido! Ambiente Staging ativo."
echo "=========================================="
