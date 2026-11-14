#!/bin/sh
set -e

echo "==> Aguardando inicialização e aplicando migrações..."
python manage.py migrate --noinput

if [ "$SEED_DEMO_DATA" = "1" ] || [ -z "$SEED_DEMO_DATA" ]; then
    echo "==> Carregando dados mockados de demonstração..."
    python manage.py seed_demo_data
fi

if [ "$COLLECT_STATIC" = "1" ]; then
    echo "==> Coletando arquivos estáticos para o Nginx..."
    python manage.py collectstatic --noinput
fi

if [ "$DJANGO_SERVER_MODE" = "gunicorn" ]; then
    echo "==> Iniciando servidor de produção Gunicorn..."
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers ${GUNICORN_WORKERS:-3} \
        --timeout 60 \
        --access-logfile - \
        --error-logfile -
else
    echo "==> Iniciando servidor Django de desenvolvimento..."
    exec python manage.py runserver 0.0.0.0:8000
fi
