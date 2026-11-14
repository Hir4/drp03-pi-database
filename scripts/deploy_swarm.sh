#!/usr/bin/env bash
set -e

echo "=========================================="
echo "  FCN TI - Deploy Docker Swarm (Staging)  "
echo "=========================================="

if [ ! -f .env.staging ]; then
    echo "[ERRO] Arquivo .env.staging nao encontrado!"
    echo "Copie o arquivo .env.staging.example para .env.staging e configure suas variaveis."
    exit 1
fi

if ! docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null | grep -q 'active'; then
    echo "==> Inicializando nó Docker Swarm..."
    docker swarm init
fi

# Exporta variáveis do .env.staging para o stack deploy
set -a
source .env.staging
set +a

echo "==> Construindo imagens locais..."
docker compose --env-file .env.staging -f docker-compose.staging.yml build

echo "==> Fazendo deploy da Stack fcn_staging..."
docker stack deploy -c docker-compose.staging.yml fcn_staging

echo "==> Verificando servicos da stack..."
docker stack services fcn_staging

echo "=========================================="
echo " Deploy no Docker Swarm concluido!"
echo " Dica para escalar: docker service scale fcn_staging_backend=2"
echo "=========================================="
