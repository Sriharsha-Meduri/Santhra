# Santhra frontend — Vite build served by nginx (proxies /api,/media to backend).
# Build context = repo root.
FROM node:20-alpine AS build
WORKDIR /app
# Use the committed lockfile for a reproducible install.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
