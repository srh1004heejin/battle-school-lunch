FROM node:24-alpine AS build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend ./
RUN npm run build

FROM nginx:1.27-alpine

ENV BACKEND_HOST=backend:8000 \
    NGINX_ENVSUBST_FILTER=BACKEND_HOST

COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 CMD wget -q -O - http://127.0.0.1/ >/dev/null || exit 1
