#!/usr/bin/env bash
# ==============================================================================
# FCN TI - Script de Ativacao Automatica de SSL/HTTPS Gratuito (Let's Encrypt)
# ==============================================================================
set -e

echo "=========================================="
echo "    FCN TI - Ativacao de SSL / HTTPS      "
echo "        (Let's Encrypt / Certbot)         "
echo "=========================================="

if [ ! -f .env.staging ]; then
    echo "[ERRO] Arquivo .env.staging nao encontrado! Execute na raiz do projeto."
    exit 1
fi

DEFAULT_DOMAIN="srv1397595.hstgr.cloud"

echo ""
echo "Opcoes gratuitas de dominio disponiveis:"
echo "1) Hostname oficial da Hostinger: $DEFAULT_DOMAIN"
echo "2) Wildcard DNS gratuito baseado no seu IP: 72-61-48-173.sslip.io"
echo "3) Seu proprio dominio customizado"
echo ""

read -p "Digite o dominio desejado [Pressionar Enter usa '$DEFAULT_DOMAIN']: " USER_DOMAIN
DOMAIN="${USER_DOMAIN:-$DEFAULT_DOMAIN}"

read -p "Digite seu e-mail para avisos de renovacao do Let's Encrypt: " EMAIL
if [ -z "$EMAIL" ]; then
    echo "[ERRO] O e-mail e obrigatorio para emissao do certificado Let's Encrypt."
    exit 1
fi

echo ""
echo "==> 1. Garantindo que o Nginx esta ativo na porta 80..."
docker compose --env-file .env.staging -f docker-compose.staging.yml up -d nginx

echo "==> 2. Solicitando certificado SSL gratuito para: $DOMAIN..."
docker compose --env-file .env.staging -f docker-compose.staging.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email

echo "==> 3. Atualizando .env.staging para ativar politicas HTTPS no Django..."
if grep -q "^USE_HTTPS=" .env.staging; then
    sed -i 's/^USE_HTTPS=.*/USE_HTTPS=1/' .env.staging
else
    echo "USE_HTTPS=1" >> .env.staging
fi

# Garante que o novo dominio esta presente em ALLOWED_HOSTS e CSRF_TRUSTED_ORIGINS
if ! grep -q "$DOMAIN" .env.staging; then
    sed -i "s/^ALLOWED_HOSTS=\(.*\)/ALLOWED_HOSTS=\1,$DOMAIN/" .env.staging
    sed -i "s|^CSRF_TRUSTED_ORIGINS=\(.*\)|\1,https://$DOMAIN|" .env.staging
fi

echo "==> 4. Reiniciando Nginx e Backend para aplicar o certificado e redirecionamento HTTPS..."
docker compose --env-file .env.staging -f docker-compose.staging.yml restart backend nginx

echo ""
echo "=========================================="
echo " SUCESSO! Certificado SSL ativado com o cadeado verde!"
echo " Acesse a aplicacao de forma segura em:"
echo " 👉 https://$DOMAIN/"
echo "=========================================="
