import uuid
from typing import Callable

from fastapi import Request, Response


HEADER_NAME = "X-Request-ID"


def _is_valid_incoming(value: str) -> bool:
    if not value:
        return False
    # Limitar tamanho para evitar header gigante
    if len(value) > 128:
        return False
    return True


async def request_id_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
    incoming = request.headers.get(HEADER_NAME)
    if incoming and _is_valid_incoming(incoming):
        req_id = incoming
    else:
        req_id = str(uuid.uuid4())

    # Disponibiliza para downstream
    request.state.request_id = req_id

    response = await call_next(request)
    # Garante o header na resposta
    response.headers[HEADER_NAME] = req_id
    return response

