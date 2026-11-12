FROM nginx:1.27-alpine

RUN rm -f /etc/nginx/conf.d/*.conf
RUN mkdir -p /etc/nginx/custom-templates /var/www/certbot /var/www/staticfiles

COPY templates/ /etc/nginx/custom-templates/
COPY templates/nginx-http.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /docker-entrypoint.d/40-ssl-detect.sh

RUN sed -i 's/\r$//' /docker-entrypoint.d/40-ssl-detect.sh && \
    sed -i 's/\r$//' /etc/nginx/custom-templates/* && \
    sed -i 's/\r$//' /etc/nginx/conf.d/default.conf && \
    chmod +x /docker-entrypoint.d/40-ssl-detect.sh

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
