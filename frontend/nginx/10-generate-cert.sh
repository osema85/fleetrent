#!/bin/sh
# Creates a self-signed TLS certificate on first start if none is present.
# For production, mount your real certificate as server.crt / server.key in /etc/nginx/certs.
set -eu

CERT_DIR=/etc/nginx/certs
CN="${TLS_COMMON_NAME:-localhost}"

if [ -s "$CERT_DIR/server.crt" ] && [ -s "$CERT_DIR/server.key" ]; then
  exit 0
fi

echo "10-generate-cert.sh: generating a self-signed certificate for $CN"
openssl req -x509 -nodes -newkey rsa:3072 -days 365 \
  -keyout "$CERT_DIR/server.key" -out "$CERT_DIR/server.crt" \
  -subj "/CN=$CN" \
  -addext "subjectAltName=DNS:$CN,DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
chmod 600 "$CERT_DIR/server.key"
