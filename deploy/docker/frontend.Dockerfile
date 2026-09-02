# Builds the console bundle from source, then serves it from nginx.
FROM node:20-alpine AS build
WORKDIR /src
COPY dca-ui/package*.json ./
RUN npm ci --no-audit --no-fund
COPY dca-ui/ ./
RUN npm run build:prod

FROM nginx:1.27-alpine
COPY deploy/docker/frontend-nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist/ /usr/share/nginx/html/
EXPOSE 5174
