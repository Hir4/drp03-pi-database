FROM nginx:1.27-alpine

RUN rm -f /etc/nginx/conf.d/default.conf
RUN mkdir -p /etc/nginx/templates /var/www/certbot /var/www/staticfiles

COPY templates/ /etc/nginx/templates/
COPY entrypoint.sh /docker-entrypoint.d/40-ssl-detect.sh
RUN chmod +x /docker-entrypoint.d/40-ssl-detect.sh

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
