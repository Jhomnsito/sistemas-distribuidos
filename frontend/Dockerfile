FROM node:24-alpine AS build
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/index.html ./
COPY frontend/src/ ./src/
RUN npm run build
FROM nginx:1.28-alpine
COPY deploy/gateway.conf /etc/nginx/conf.d/default.conf
COPY deploy/routes.inc /etc/nginx/vayxer/routes.inc
COPY --from=build /web/dist /usr/share/nginx/html
