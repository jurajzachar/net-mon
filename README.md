# Network Monitor
This is a very simple Python-based network monitor that measures the latency of a given host 
by opening a socket to spefied IP or hostname and  port. In case of failure, it will log and submit metrics to InfluxDB.

## Building
run `make build` to build the docker image. The image will be named "net-mon" and tagged as "latest".

## Running
```
docker run -d \
  --name net-mon \
  --restart always \
  -e INFLUXDB_URL=http://myinfluxdb:8086 \
  -e INFLUXDB_TOKEN=your_token \
  -e INFLUXDB_ORG=your_org \
  -e INFLUXDB_BUCKET=your_bucket \
  -e MONITOR_HOST=example.com \
  -e MONITOR_PORT=53 \
  -p 8080:8080 \
  net-mon:latest
```

## Systemd Network Watchdog Service
When internet connectivity is lost `net-mon` will detect it and output the following response on `/api/network-status`:
```json
{
  "connected": "false",
  "last_success": "2025-11-08T21:28:50Z",
  "downtime_seconds": 123
}
```

You can use this information to trigger a systemd service that will restart your network interface or perform other recovery actions.
[Network Health Watcher](systemd/network-health-watcher.sh) is a systemd service that uses `curl` to check the network status 
and restarts the host if connectivity is lost for more than `15 minutes` (THRESHOLD=900 seconds):

```ini
# /etc/network-watchdog.conf

# URL to check (container’s FastAPI endpoint)
API_URL=http://localhost:8080/api/network-status

# Reboot threshold (in seconds)
THRESHOLD=900

# Timeout for curl requests (in seconds)
CURL_TIMEOUT=5

# Logging tag for syslog
LOG_TAG=network-watchdog
```

### Installation

Execute [install.sh](systemd/install.sh) script with superuser privileges to install and start the service.

Alternatively, you can manually install the service by following these steps:

1. Copy `network-health-watcher.service` to `/etc/systemd/system/`
2. Copy `network-health-watcher.timer` to `/etc/systemd/system`
3. Copy `network-health-watcher.sh` to `/opt/local/bin/` and make it executable
4. Copy `network-watchdog.conf` to `/etc/`
5. Enable and start the service:
```bash
sudo systemctl enable network-health-watcher.service
sudo systemctl start network-health-watcher.service
```