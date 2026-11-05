#!/usr/bin/env bash
# Script de configuracao inicial e seguranca da VPS Hostinger (Ubuntu 24.04)
# Execute na VPS como root: bash scripts/vps_setup.sh
set -e

echo "=========================================="
echo "    FCN TI - Setup de Seguranca da VPS    "
echo "=========================================="

echo "==> 1. Atualizando pacotes do sistema..."
apt update && apt upgrade -y

echo "==> 2. Instalando ferramentas essenciais e Fail2ban..."
apt install -y ufw fail2ban curl git htop

echo "==> 3. Configurando Firewall UFW (Seguranca de Portas)..."
# Permitir SSH (porta 22), HTTP (80) e HTTPS (443)
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP Nginx'
ufw allow 443/tcp comment 'HTTPS'

# Ativar UFW sem prompt interativo
echo "y" | ufw enable
ufw status verbose

echo "==> 4. Ativando Fail2ban contra ataques de forca bruta..."
systemctl enable fail2ban
systemctl restart fail2ban
systemctl status fail2ban --no-pager

echo "==> 5. Verificando Docker e Docker Compose..."
docker --version
docker compose version

echo "=========================================="
echo " Setup concluido com sucesso!"
echo " Servidor blindado e pronto para deploy."
echo "=========================================="
