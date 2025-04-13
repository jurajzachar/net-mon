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