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
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]