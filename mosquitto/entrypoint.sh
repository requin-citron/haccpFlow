#!/bin/sh
set -eu

: "${MQTT_USERNAME:?MQTT_USERNAME is required}"
: "${MQTT_PASSWORD:?MQTT_PASSWORD is required}"

PASSWD_FILE=/mosquitto/data/passwd

mkdir -p /mosquitto/data /mosquitto/log

# `mosquitto_passwd -c` refuses to overwrite an existing file ("File exists"),
# and /mosquitto/data survives restarts through its named volume. Drop the old
# file first, then rebuild it from the environment so the broker credentials
# always match `.env`. Any user added by hand to the file is discarded.
rm -f "$PASSWD_FILE"
mosquitto_passwd -c -b "$PASSWD_FILE" "$MQTT_USERNAME" "$MQTT_PASSWORD"

chown -R mosquitto:mosquitto /mosquitto/data /mosquitto/log 2>/dev/null || true
chmod 600 "$PASSWD_FILE"

exec "$@"
