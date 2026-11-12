FROM nginx:1.27-alpine

RUN rm -f /etc/nginx/conf.d/*.conf
RUN mkdir -p /etc/nginx/templates /var/www/certbot /var/www/staticfiles

COPY templates/ /etc/nginx/templates/
COPY entrypoint.sh /docker-entrypoint.d/40-ssl-detect.sh

# Garante remocao de quebras de linha Windows (CRLF -> LF) e permissao de execucao
RUN sed -i 's/\r$//' /docker-entrypoint.d/40-ssl-detect.sh && \
    sed -i 's/\r$//' /etc/nginx/templates/* && \
    chmod +x /docker-entrypoint.d/40-ssl-detect.sh

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
