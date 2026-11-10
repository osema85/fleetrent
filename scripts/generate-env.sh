#!/usr/bin/env sh
# Creates a private .env file with strong random secrets.
# Usage: ./scripts/generate-env.sh [admin-email]
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
EXAMPLE_FILE="$ROOT_DIR/.env.example"
ADMIN_EMAIL="${1:-admin@example.com}"

if [ -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE already exists. Delete it first if you really want new secrets." >&2
  echo "       (Changing POSTGRES_PASSWORD after the first start requires resetting the database volume.)" >&2
  exit 1
fi

command -v openssl >/dev/null 2>&1 || { echo "ERROR: openssl is required." >&2; exit 1; }

rand() { openssl rand -base64 "$1" | tr -d '\n/+=' | cut -c1-"$2"; }

DB_PASSWORD="$(rand 48 40)"
SECRET_KEY="$(rand 96 64)"
# Admin password: random part + guaranteed character classes for the password policy
ADMIN_PASSWORD="$(rand 24 16)Aa1!"

umask 077
sed \
  -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$DB_PASSWORD|" \
  -e "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" \
  -e "s|^FIRST_ADMIN_EMAIL=.*|FIRST_ADMIN_EMAIL=$ADMIN_EMAIL|" \
  -e "s|^FIRST_ADMIN_PASSWORD=.*|FIRST_ADMIN_PASSWORD=$ADMIN_PASSWORD|" \
  "$EXAMPLE_FILE" > "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "Created $ENV_FILE (permissions 600)."
echo ""
echo "  First admin login:"
echo "    email:    $ADMIN_EMAIL"
echo "    password: $ADMIN_PASSWORD"
echo ""
echo "Store this password in a password manager and change it after the first login."
