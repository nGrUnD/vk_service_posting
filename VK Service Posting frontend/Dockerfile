# Строим фронтенд
FROM node:20 AS build

WORKDIR /app
COPY package-lock.json ./
COPY vk_service_posting/ ./
RUN npm ci
RUN npm run build

# Используем Nginx для сервинга
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/nginx.http.conf.template
COPY nginx.https.conf /etc/nginx/templates/nginx.https.conf.template
COPY docker-entrypoint-generate-nginx.sh /docker-entrypoint.d/40-generate-nginx-config.sh
RUN chmod +x /docker-entrypoint.d/40-generate-nginx-config.sh
EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]