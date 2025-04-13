import http.server
import logging
import json
import socketserver
import threading

HEALTHCHECK_PORT = 8080


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'level': record.levelname,
            'message': record.getMessage(),
            'time': self.formatTime(record, self.datefmt),
            'threadName': record.threadName,
            'filename': record.filename,
            'funcName': record.funcName,
        }
        return json.dumps(log_record)


class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthcheck":
            # Check if the monitor's exception queue is empty
            if monitor.exception_queue.empty():
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Monitor has exceptions")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")


if __name__ == '__main__':
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])

    from network_latency_monitor import NetworkLatencyMonitor

    monitor = NetworkLatencyMonitor.from_env()
    thread = threading.Thread(target=monitor.run)
    thread.start()

    # Start the HTTP server
    with socketserver.TCPServer(("", HEALTHCHECK_PORT), HealthCheckHandler) as httpd:
        logging.info(f"Serving healthcheck on port {HEALTHCHECK_PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            monitor.stop()
            thread.join()
            httpd.server_close()
