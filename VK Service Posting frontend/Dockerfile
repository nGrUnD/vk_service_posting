# Строим V1
FROM node:20 AS build-v1

WORKDIR /app/v1
COPY vk_service_posting/package*.json ./
RUN npm ci
COPY vk_service_posting/ ./
RUN npm run build

# Строим V2
FROM node:20 AS build-v2

WORKDIR /app/v2
COPY vk_service_posting_v2/package*.json ./
RUN npm ci
COPY vk_service_posting_v2/ ./
RUN npm run build

# Используем Nginx для сервинга
FROM nginx:alpine
COPY --from=build-v1 /app/v1/dist /usr/share/nginx/html
COPY --from=build-v2 /app/v2/dist /usr/share/nginx/html/v2
COPY nginx.conf /etc/nginx/templates/nginx.http.conf.template
COPY nginx.https.conf /etc/nginx/templates/nginx.https.conf.template
COPY docker-entrypoint-generate-nginx.sh /docker-entrypoint.d/40-generate-nginx-config.sh
RUN chmod +x /docker-entrypoint.d/40-generate-nginx-config.sh
EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]