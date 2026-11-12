#!/bin/sh
set -e

CERT_DIR="/etc/letsencrypt/live"

if [ -d "$CERT_DIR" ]; then
    for dir in "$CERT_DIR"/*; do
        if [ -d "$dir" ] && [ -f "$dir/fullchain.pem" ] && [ -f "$dir/privkey.pem" ]; then
            CERT_DOMAIN=$(basename "$dir")
            echo "==> [Nginx] Certificado SSL detectado para o dominio: $CERT_DOMAIN"
            echo "==> [Nginx] Ativando servidor seguro HTTPS (porta 443)..."
            sed -e "s|\${SSL_DOMAIN}|$CERT_DOMAIN|g" /etc/nginx/templates/nginx-ssl.conf.template > /etc/nginx/conf.d/default.conf
            exit 0
        fi
    done
fi

echo "==> [Nginx] Operando em modo HTTP inicial com desafio ACME ativado (porta 80)."
exit 0
