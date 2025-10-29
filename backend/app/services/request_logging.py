import logging
import json
import time
from typing import Callable

from fastapi import Request, Response


LOGGER_NAME = "webplay.request"


async def request_logging_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
    start = time.time()
    logger = logging.getLogger(LOGGER_NAME)

    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        # Em caso de erro, ainda registra e re-lança
        status = 500
        duration_ms = int((time.time() - start) * 1000)
        entry = {
            "level": "ERROR",
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        }
        logger.error(json.dumps(entry, ensure_ascii=False))
        raise

    duration_ms = int((time.time() - start) * 1000)
    entry = {
        "level": "INFO",
        "method": request.method,
        "path": request.url.path,
        "status": status,
        "duration_ms": duration_ms,
        "client_ip": request.client.host if request.client else None,
        "request_id": getattr(request.state, "request_id", None),
    }
    logger.info(json.dumps(entry, ensure_ascii=False))
    return response

