# python
import json
import logging
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.applications import Starlette

from network_latency_monitor import NetworkLatencyMonitor

APP_PORT = 8080

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

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])

@asynccontextmanager
async def lifespan(app: FastAPI):
    monitor = NetworkLatencyMonitor.from_env()
    thread = threading.Thread(target=monitor.run, daemon=True)
    thread.start()
    app.state.monitor = monitor
    app.state.monitor_thread = thread
    try:
        yield
    finally:
        monitor.stop()
        thread.join(timeout=5)

app: Starlette = FastAPI(title="Network Monitor", lifespan=lifespan)

@app.get("/healthcheck")
def healthcheck():
    """Basic process-level health."""
    monitor = app.state.monitor
    if monitor.exception_queue.empty():
        return JSONResponse(status_code=200, content={"status": "OK"})
    else:
        return JSONResponse(status_code=500, content={"status": "Monitor exceptions detected"})

@app.get("/api/network-status")
def network_status():
    """Return network connectivity information."""
    return JSONResponse(status_code=200, content=app.state.monitor.get_status())

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=APP_PORT)
