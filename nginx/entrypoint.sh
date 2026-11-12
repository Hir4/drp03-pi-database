#!/bin/sh
set -e

CERT_DIR="/etc/letsencrypt/live"
CERT_EXISTS=0
CERT_DOMAIN=""

if [ -d "$CERT_DIR" ]; then
    for dir in "$CERT_DIR"/*; do
        if [ -d "$dir" ] && [ -f "$dir/fullchain.pem" ] && [ -f "$dir/privkey.pem" ]; then
            CERT_DOMAIN=$(basename "$dir")
            CERT_EXISTS=1
            break
        fi
    done
fi

if [ "$CERT_EXISTS" -eq 1 ]; then
    echo "==> [Nginx] Certificado SSL detectado para o dominio: $CERT_DOMAIN"
    echo "==> [Nginx] Ativando servidor seguro HTTPS (porta 443) com redirecionamento de HTTP (porta 80)..."
    sed -e "s|\${SSL_DOMAIN}|$CERT_DOMAIN|g" /etc/nginx/templates/nginx-ssl.conf.template > /etc/nginx/conf.d/default.conf
else
    echo "==> [Nginx] Nenhum certificado SSL detectado. Operando em modo HTTP com desafio ACME ativado."
    cp /etc/nginx/templates/nginx-http.conf /etc/nginx/conf.d/default.conf
fi
