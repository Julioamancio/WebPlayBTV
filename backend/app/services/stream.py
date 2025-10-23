import gzip
import http.cookiejar
import logging
import time
import zlib
from typing import Tuple

from app.core.config import get_settings

logger = logging.getLogger("webplayer.stream")
settings = get_settings()

_COOKIE_JARS: dict[str, Tuple[http.cookiejar.CookieJar, float]] = {}


def get_cookie_jar_for_origin(key: str) -> http.cookiejar.CookieJar:
    now = time.time()
    stale_keys = [
        k for k, (_, ts) in _COOKIE_JARS.items() if now - ts > settings.cookie_jar_ttl_seconds
    ]
    for stale_key in stale_keys:
        _COOKIE_JARS.pop(stale_key, None)

    if key in _COOKIE_JARS:
        jar, _ = _COOKIE_JARS[key]
        _COOKIE_JARS[key] = (jar, now)
        return jar

    if len(_COOKIE_JARS) >= settings.cookie_jar_max:
        oldest_key = min(_COOKIE_JARS.items(), key=lambda item: item[1][1])[0]
        _COOKIE_JARS.pop(oldest_key, None)

    jar = http.cookiejar.CookieJar()
    _COOKIE_JARS[key] = (jar, now)
    return jar


def decompress_response(data: bytes, encoding: str | None) -> bytes:
    encoding = (encoding or "").lower()
    if "gzip" in encoding:
        return gzip.decompress(data)
    if "deflate" in encoding:
        return zlib.decompress(data)
    return data

