import os
import re
import time
import asyncio
from typing import Any, Dict, List, Optional, Tuple

import httpx
from app.config import M3U_TTL_SECONDS, M3U_FETCH_RETRIES, FETCH_BACKOFF_SECONDS


_cache_text: Optional[str] = None
_cache_source: Optional[str] = None
_cache_ts: float = 0.0
_M3U_TTL_SECONDS = float(M3U_TTL_SECONDS)


def _parse_extinf(line: str) -> Tuple[Dict[str, str], str]:
    attrs: Dict[str, str] = {}
    # Extrai chave="valor" incluindo chaves com hífen
    for key, val in re.findall(r'([\w-]+)="(.*?)"', line):
        attrs[key] = val
    # Nome do canal fica após a última vírgula
    name_match = re.search(r",\s*(.*)$", line)
    name = name_match.group(1).strip() if name_match else ""
    return attrs, name


def parse_m3u(text: str) -> List[Dict[str, Any]]:
    channels: List[Dict[str, Any]] = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            attrs, name = _parse_extinf(line)
            # Próxima linha deve ser a URL
            url = ""
            if i + 1 < len(lines):
                url = lines[i + 1]
                i += 1
            channels.append(
                {
                    "name": name,
                    "url": url,
                    "tvg_id": attrs.get("tvg-id"),
                    "group": attrs.get("group-title"),
                    "logo": attrs.get("tvg-logo"),
                    "raw_extinf": line,
                }
            )
        i += 1
    return channels


async def load_m3u_text(source: str, force: bool = False) -> str:
    global _cache_text, _cache_source, _cache_ts
    now = time.time()
    if (
        not force
        and _cache_text is not None
        and source == _cache_source
        and (now - _cache_ts) < _M3U_TTL_SECONDS
    ):
        return _cache_text

    if source.startswith("http://") or source.startswith("https://"):
        attempts = max(1, int(M3U_FETCH_RETRIES))
        backoff = float(FETCH_BACKOFF_SECONDS)
        last_err: Optional[Exception] = None
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for i in range(attempts):
                try:
                    resp = await client.get(source)
                    resp.raise_for_status()
                    text = resp.text
                    break
                except Exception as e:
                    last_err = e
                    if i < attempts - 1:
                        await asyncio.sleep(backoff * (2 ** i))
                    else:
                        raise last_err
    else:
        # Caminho relativo à pasta backend
        rel_path = source
        # __file__ = backend/app/services/m3u.py -> subir três níveis até backend
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        file_path = os.path.join(base_dir, rel_path)
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

    _cache_text = text
    _cache_source = source
    _cache_ts = now
    return text
