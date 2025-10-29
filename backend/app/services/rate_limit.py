from collections import defaultdict, deque
import time
from typing import Callable

from fastapi import Request, Response

from app.config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_WINDOW_SECONDS,
    RATE_LIMIT_LOGIN_PER_WINDOW,
    RATE_LIMIT_REFRESH_PER_WINDOW,
    RATE_LIMIT_DEVICES_REGISTER_PER_WINDOW,
)
from app.observability import RATE_LIMIT_BLOCKED_TOTAL


# Estrutura in-memory simples: por (ip, path_template) guarda timestamps
_requests: dict[tuple[str, str], deque] = defaultdict(deque)


def _limit_for_path(path_template: str) -> int | None:
    # Limites por rota crítica; None significa sem rate limit para a rota
    if path_template == "/auth/login":
        return RATE_LIMIT_LOGIN_PER_WINDOW
    if path_template == "/auth/refresh":
        return RATE_LIMIT_REFRESH_PER_WINDOW
    if path_template == "/devices/register":
        return RATE_LIMIT_DEVICES_REGISTER_PER_WINDOW
    return None


async def rate_limit_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
    if not RATE_LIMIT_ENABLED:
        return await call_next(request)

    route = request.scope.get("route")
    path_template = getattr(route, "path", None) or request.url.path
    limit = _limit_for_path(path_template)
    if not limit or limit <= 0:
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    key = (ip, path_template)
    now = time.time()
    window_start = now - float(RATE_LIMIT_WINDOW_SECONDS)

    dq = _requests[key]
    # Purga eventos antigos fora da janela
    while dq and dq[0] < window_start:
        dq.popleft()

    if len(dq) >= int(limit):
        RATE_LIMIT_BLOCKED_TOTAL.labels(path_template).inc()
        # 429 Too Many Requests
        return Response(status_code=429, content=b"Too Many Requests")

    dq.append(now)
    return await call_next(request)

