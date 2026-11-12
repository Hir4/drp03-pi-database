#!/usr/bin/env bash
# ==============================================================================
# FCN TI - Script de Renovacao Automatica do Certificado SSL Let's Encrypt
# ==============================================================================
set -e

cd /app/fcn-ti 2>/dev/null || cd "$(dirname "$0")/.."

echo "==> Verificando e renovando certificados Let's Encrypt..."
docker compose --env-file .env.staging -f docker-compose.staging.yml run --rm certbot renew

echo "==> Recarregando Nginx para aplicar certificados renovados..."
docker compose --env-file .env.staging -f docker-compose.staging.yml exec nginx nginx -s reload

echo "==> Verificacao concluida com sucesso!"
