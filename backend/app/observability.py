import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge


logger = logging.getLogger("webplay")


HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "path", "status"],
)

HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=["method", "path", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

# Métricas de capacidade por usuário/contexto
USER_CAPACITY_REMAINING = Gauge(
    "user_capacity_remaining",
    "Remaining device capacity by user and context",
    labelnames=["username", "context"],
)

CAPACITY_LIMIT_REACHED_TOTAL = Counter(
    "capacity_limit_reached_total",
    "Times a user hit capacity limit",
    labelnames=["context"],
)

# Rate limit blocks
RATE_LIMIT_BLOCKED_TOTAL = Counter(
    "rate_limit_blocked_total",
    "Times a request was blocked by rate limiting",
    labelnames=["path"],
)


async def metrics_middleware(request: Request, call_next: Callable[[Request], Response]):
    start = time.perf_counter()
    # Request ID
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Descobrir o path template (fallback para path real)
    route = request.scope.get("route")
    path_template = getattr(route, "path", None) or request.url.path

    response: Response
    try:
        response = await call_next(request)
    except Exception as exc:
        duration = time.perf_counter() - start
        status_code = 500
        HTTP_REQUESTS.labels(request.method, path_template, str(status_code)).inc()
        HTTP_LATENCY.labels(request.method, path_template, str(status_code)).observe(duration)
        logger.exception(
            "msg=unhandled_exception request_id=%s method=%s path=%s duration_ms=%.2f",
            req_id,
            request.method,
            path_template,
            duration * 1000.0,
        )
        raise

    # Métricas e logs em caso de sucesso/erro controlado
    duration = time.perf_counter() - start
    status_code = response.status_code
    HTTP_REQUESTS.labels(request.method, path_template, str(status_code)).inc()
    HTTP_LATENCY.labels(request.method, path_template, str(status_code)).observe(duration)

    # Propagar X-Request-ID
    response.headers["X-Request-ID"] = req_id

    # Log estruturado simples
    logger.info(
        "msg=request_handled request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        req_id,
        request.method,
        path_template,
        status_code,
        duration * 1000.0,
    )

    return response

