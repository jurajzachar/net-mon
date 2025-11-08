#!/usr/bin/env bash
set -euo pipefail

# Paths (script assumes it's placed in `systemd/`)
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_SRC="$SRC_DIR/network-health-watcher.service"
TIMER_SRC="$SRC_DIR/network-health-watcher.timer"
SCRIPT_SRC="$SRC_DIR/network-health-watcher.sh"
CONF_SRC="$SRC_DIR/network-health-watcher.conf"

DEST_SERVICE="/etc/systemd/system/network-health-watcher.service"
DEST_TIMER="/etc/systemd/system/network-health-watcher.timer"
DEST_SCRIPT="/opt/local/bin/network-health-watcher.sh"
DEST_CONF="/etc/network-health-watcher.conf"

# Ensure running as root
if [ "$EUID" -ne 0 ]; then
  echo "Run as root or with sudo"
  exit 1
fi

# Check sources exist (include timer)
for f in "$SERVICE_SRC" "$TIMER_SRC" "$SCRIPT_SRC" "$CONF_SRC"; do
  if [ ! -f "$f" ]; then
    echo "Missing required file: $f"
    exit 2
  fi
done

echo "Installing service to $DEST_SERVICE"
cp "$SERVICE_SRC" "$DEST_SERVICE"
chmod 644 "$DEST_SERVICE"

echo "Installing timer to $DEST_TIMER"
cp "$TIMER_SRC" "$DEST_TIMER"
chmod 644 "$DEST_TIMER"

echo "Installing script to $DEST_SCRIPT"
mkdir -p "$(dirname "$DEST_SCRIPT")"
cp "$SCRIPT_SRC" "$DEST_SCRIPT"
chmod 755 "$DEST_SCRIPT"

echo "Installing config to $DEST_CONF"
cp "$CONF_SRC" "$DEST_CONF"
chmod 644 "$DEST_CONF"

echo "Reloading systemd daemon"
systemctl daemon-reload

# Do not call 'systemctl enable' because the units have no [Install] section.
# Start/restart units directly so they become active for this boot without enabling.
echo "Starting/restarting network-health-watcher.timer"
if ! systemctl restart network-health-watcher.timer; then
  systemctl start network-health-watcher.timer
fi

echo "Installation complete."