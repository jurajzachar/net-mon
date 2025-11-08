#!/bin/bash
CONFIG_FILE="/etc/network-health-watcher.conf"

# shellcheck disable=SC1090
[ -f "$CONFIG_FILE" ] && source "$CONFIG_FILE"

# Fallback defaults
: "${API_URL:=http://localhost:8080/api/network-status}"
: "${THRESHOLD:=300}"
: "${CURL_TIMEOUT:=5}"
: "${LOG_TAG:=network-health-watcher}"

response=$(curl -s --max-time "$CURL_TIMEOUT" "$API_URL")
if [ $? -ne 0 ]; then
  logger -t "$LOG_TAG" "Failed to reach API ($API_URL)"
  exit 0
fi

downtime=$(echo "$response" | jq -r '.downtime_seconds // 0')

if [[ -z "$downtime" ]]; then
  logger -t "$LOG_TAG" "Invalid API response: $response"
  exit 0
fi

if (( $(echo "$downtime > $THRESHOLD" | bc -l) )); then
  logger -t "$LOG_TAG" "Internet down for ${downtime}s > ${THRESHOLD}s — rebooting host..."
  systemctl reboot
fi