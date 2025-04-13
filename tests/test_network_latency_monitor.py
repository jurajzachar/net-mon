import logging
import os
import threading
import time

import pytest
from influxdb_client import InfluxDBClient
from testcontainers.influxdb import InfluxDbContainer

from net_mon import main

handler = logging.StreamHandler()
handler.setFormatter(main.JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])

token, org, bucket = "fake-token", "fake-org", "fake-bucket"


@pytest.fixture(scope="session")
def influxdb_container():
    """Starts an InfluxDB container and yields its connection details.
    see https://docs.influxdata.com/influxdb/v2/install/?t=Docker
    """
    with (InfluxDbContainer("influxdb:2")
                  .with_env("DOCKER_INFLUXDB_INIT_MODE", "setup")
                  .with_env("DOCKER_INFLUXDB_INIT_USERNAME", "admin")
                  .with_env("DOCKER_INFLUXDB_INIT_PASSWORD", "fake-secret")
                  .with_env("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN", token)
                  .with_env("DOCKER_INFLUXDB_INIT_ORG", org)
                  .with_env("DOCKER_INFLUXDB_INIT_BUCKET", bucket)
                  .with_env("DOCKER_INFLUXDB_INIT_RETENTION", "1d")
          as influxdb):
        url = influxdb.get_url()
        logging.info(f"connecting to InfluxDB at {url}")

        with InfluxDBClient(url=url, token=token, org=org) as client:
            # check connectivity
            assert client.ping()

            # create a bucket
            # read query succeeds with empty result set
            resp = client.query_api().query(f"from(bucket: \"{bucket}\") |> range(start: -1m)")
            assert resp is not None
            assert len(resp) == 0

            # db active, set environment variables
            os.environ["INFLUXDB_URL"] = url
            os.environ["INFLUXDB_TOKEN"] = token
            os.environ["INFLUXDB_ORG"] = org
            os.environ["INFLUXDB_BUCKET"] = bucket

            # measure latency to influxdb on localhost every second
            os.environ["TARGET_HOST"] = "8.8.8.8"
            os.environ["TARGET_PORT"] = str(53)
            os.environ["CHECK_INTERVAL"] = "3"

        yield influxdb


def test_take_latency_measurement_successfully(influxdb_container):
    logging.info("Testing network latency monitor [latency]...")
    from net_mon import network_latency_monitor
    try:
        # Initialize the network latency monitor
        mon = network_latency_monitor.NetworkLatencyMonitor.from_env()
        thread = threading.Thread(target=mon.run)
        thread.start()
        # let network monitor run for a while
        time.sleep(5)
        mon.stop()
        thread.join()

        # Check for exceptions
        if not mon.exception_queue.empty():
            for e in mon.exception_queue.queue:
                logging.error(f"network monitor failed to execute due to: {e.args}")
                pytest.fail(f"network monitor failed to execute due to: {e.args}")

        # check if data was written to influxdb
        with InfluxDBClient(url=mon.INFLUXDB_URL, token=mon.INFLUXDB_TOKEN, org=mon.INFLUXDB_ORG) as client:
            query_api = client.query_api()
            result = query_api.query(f'from(bucket: "{mon.INFLUXDB_BUCKET}") |> range(start: -1m)')
            assert result is not None
            logging.info(f"latency metrics: {result}")
            assert len(result) > 0

    except ValueError as e:
        pytest.fail(f"network monitor failed to initialize due to: {e.args}")
