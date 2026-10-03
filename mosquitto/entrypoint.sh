#!/bin/sh
set -eu

: "${MQTT_USERNAME:?MQTT_USERNAME is required}"
: "${MQTT_PASSWORD:?MQTT_PASSWORD is required}"

PASSWD_FILE=/mosquitto/data/passwd

mkdir -p /mosquitto/data /mosquitto/log

# The password file is rebuilt from the environment on every start so the
# broker credentials always match `.env`.
mosquitto_passwd -c -b "$PASSWD_FILE" "$MQTT_USERNAME" "$MQTT_PASSWORD"

chown -R mosquitto:mosquitto /mosquitto/data /mosquitto/log 2>/dev/null || true
chmod 600 "$PASSWD_FILE"

exec "$@"
