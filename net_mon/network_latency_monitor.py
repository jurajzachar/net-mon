import queue
import threading
import time
import socket

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv
import os
import logging

from urllib3.exceptions import NewConnectionError

# Load environment variables (optional, use .env for credentials)
load_dotenv()


class NetworkLatencyMonitor:
    def __init__(self,
                 influxdb_url: str,
                 influxdb_token: str,
                 influxdb_org: str,
                 influxdb_bucket: str,
                 target_host: str,
                 target_port: int,
                 interval: int):
        # InfluxDB Configuration
        self.INFLUXDB_URL = influxdb_url
        self.INFLUXDB_TOKEN = influxdb_token
        self.INFLUXDB_ORG = influxdb_org
        self.INFLUXDB_BUCKET = influxdb_bucket

        # Target Host Configuration
        self.TARGET_HOST = target_host
        self.TARGET_PORT = target_port
        self.INTERVAL = interval

        # sanity check
        self._check_mandatory_env_vars()

        # Initialize InfluxDB client
        self.client = influxdb_client.InfluxDBClient(
            url=self.INFLUXDB_URL,
            token=self.INFLUXDB_TOKEN,
            org=self.INFLUXDB_ORG)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

        # Global stop flag to control the monitoring loop
        self.stop_flag = threading.Event()
        # Queue to hold exceptions
        self.exception_queue = queue.Queue()

        # Internet connection status
        self.lock = threading.Lock()
        self.currently_connected = True
        self.last_success_time = time.time()
        self.last_check_time = time.time()

    @classmethod
    def from_env(cls):
        """Secondary constructor that initializes the class using environment variables."""
        influxdb_url = os.getenv("INFLUXDB_URL")
        influxdb_token = os.getenv("INFLUXDB_TOKEN")
        influxdb_org = os.getenv("INFLUXDB_ORG")
        influxdb_bucket = os.getenv("INFLUXDB_BUCKET")
        target_host = os.getenv("TARGET_HOST")
        target_port = int(os.getenv("TARGET_PORT"))
        interval = int(os.getenv("CHECK_INTERVAL"))

        return cls(influxdb_url, influxdb_token, influxdb_org, influxdb_bucket, target_host, target_port, interval)

    def _check_mandatory_env_vars(self):
        if not self.INFLUXDB_URL:
            logging.error("InfluxDB URL is not set")
            raise ValueError("INFLUXDB_URL")
        if not self.INFLUXDB_TOKEN:
            logging.error("InfluxDB token is not set")
            raise ValueError("INFLUXDB_TOKEN")
        if not self.INFLUXDB_ORG:
            logging.error("InfluxDB organization is not set")
            raise ValueError("INFLUXDB_ORG")
        if not self.INFLUXDB_BUCKET:
            logging.error("InfluxDB bucket is not set")
            raise ValueError("INFLUXDB_BUCKET")

    def _measure_latency(self):
        """Measures connection latency to the target host."""
        try:
            start = time.time()
            with socket.create_connection((self.TARGET_HOST, self.TARGET_PORT), timeout=5):
                latency = (time.time() - start) * 1000
            with self.lock:
                self.currently_connected = True
                self.last_success_time = time.time()
                self.last_check_time = time.time()
            logging.info(f"{self.TARGET_HOST}:{self.TARGET_PORT} - latency: {latency:.2f} ms")
            return latency, True
        except (socket.timeout, socket.error, NewConnectionError) as e:
            with self.lock:
                self.currently_connected = False
                self.last_check_time = time.time()
            self.exception_queue.put(e)
            return None, False

    def _write_metrics(self, latency, success):
        """Writes latency and connection drop metrics to InfluxDB."""
        points = []

        if success:
            points.append(
                influxdb_client.Point("network_latency")
                .tag("host", self.TARGET_HOST)
                .tag("port", str(self.TARGET_PORT))
                .field("latency_ms", latency)
            )
        else:
            points.append(
                influxdb_client.Point("connection_drops")
                .tag("host", self.TARGET_HOST)
                .tag("port", str(self.TARGET_PORT))
                .field("drops", 1)  # 1 means a failed connection
            )
        try:
            self.write_api.write(bucket=self.INFLUXDB_BUCKET, org=self.INFLUXDB_ORG, record=points)
        except Exception as e:
            logging.error(f"failed to write metrics to Influxdb "
                          f"{self.INFLUXDB_ORG}/{self.INFLUXDB_BUCKET}; "
                          f"url: {self.INFLUXDB_URL}; "
                          f"reason: {e.args}")

            # let the process crash
            self.exception_queue.put(e)

    def get_status(self):
        with self.lock:
            now = time.time()
            downtime = 0 if self.currently_connected else now - self.last_success_time
            return {
                "connected": self.currently_connected,
                "last_success": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.last_success_time)),
                "downtime_seconds": round(downtime, 1)
            }

    def stop(self):
        self.stop_flag.set()

    def run(self):
        logging.info(
            f"Starting network latency monitor for {self.TARGET_HOST}:{self.TARGET_PORT} (interval: {self.INTERVAL}s)")

        while not self.stop_flag.is_set():
            latency, success = self._measure_latency()
            self._write_metrics(latency, success)
            time.sleep(self.INTERVAL)
