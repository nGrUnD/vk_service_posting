#!/bin/sh
set -eu

DOMAIN_NAME="${DOMAIN_NAME:-raccster.vk.dmtr.ru}"
HTTP_TEMPLATE="/etc/nginx/templates/nginx.http.conf.template"
HTTPS_TEMPLATE="/etc/nginx/templates/nginx.https.conf.template"
TARGET_CONFIG="/etc/nginx/nginx.conf"
CERT_DIR="/etc/letsencrypt/live/${DOMAIN_NAME}"

export DOMAIN_NAME

if [ -f "${CERT_DIR}/fullchain.pem" ] && [ -f "${CERT_DIR}/privkey.pem" ]; then
    envsubst '${DOMAIN_NAME}' < "${HTTPS_TEMPLATE}" > "${TARGET_CONFIG}"
    echo "Using HTTPS nginx config for ${DOMAIN_NAME}"
else
    envsubst '${DOMAIN_NAME}' < "${HTTP_TEMPLATE}" > "${TARGET_CONFIG}"
    echo "TLS certificate for ${DOMAIN_NAME} not found, using HTTP nginx config"
fi
