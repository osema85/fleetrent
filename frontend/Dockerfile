# ---- 1. Build the React app ---------------------------------------------
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi
COPY . .
RUN npm run build

# ---- 2. Serve it with an unprivileged nginx ---------------------------------
FROM nginxinc/nginx-unprivileged:1.27-alpine

USER root
RUN apk add --no-cache openssl curl \
 && rm -f /etc/nginx/conf.d/default.conf \
 && mkdir -p /etc/nginx/certs /etc/nginx/snippets \
 && chown -R 101:101 /etc/nginx/certs /etc/nginx/conf.d

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY nginx/security-headers.conf nginx/proxy.conf /etc/nginx/snippets/
COPY --chmod=755 nginx/10-generate-cert.sh /docker-entrypoint.d/10-generate-cert.sh
COPY --from=build /app/dist /usr/share/nginx/html

USER 101
EXPOSE 8080 8443

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD curl -fsk -o /dev/null https://127.0.0.1:8443/ || exit 1
