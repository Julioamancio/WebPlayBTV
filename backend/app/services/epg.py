import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import xmltodict
from app.config import EPG_TTL_SECONDS, EPG_FETCH_RETRIES, FETCH_BACKOFF_SECONDS


@dataclass
class EPGCache:
    content: Optional[Dict[str, Any]] = None
    ts: float = 0.0


_CACHE = EPGCache()
_TTL_SECONDS = float(EPG_TTL_SECONDS)


def _backend_base_dir() -> Path:
    # backend/app/services/ -> backend
    return Path(__file__).resolve().parents[2]


def _parse_xmltv_time(value: str) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    # Common XMLTV formats: YYYYmmddHHMMSS Z, or without timezone
    fmts = ["%Y%m%d%H%M%S %z", "%Y%m%d%H%M%S"]
    for fmt in fmts:
        try:
            dt = datetime.strptime(value, fmt)
            # Quando sem timezone, considerar UTC
            if dt.tzinfo is None:
                return dt.isoformat() + "Z"
            return dt.isoformat()
        except Exception:
            continue
    return None


async def _fetch_remote(url: str) -> str:
    attempts = max(1, int(EPG_FETCH_RETRIES))
    backoff = float(FETCH_BACKOFF_SECONDS)
    last_err: Optional[Exception] = None
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for i in range(attempts):
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                last_err = e
                if i < attempts - 1:
                    await asyncio.sleep(backoff * (2 ** i))
                else:
                    raise last_err


def _read_local(path_like: str) -> str:
    base = _backend_base_dir()
    candidate = (base / path_like).resolve()
    if not candidate.exists():
        raise FileNotFoundError(str(candidate))
    return candidate.read_text(encoding="utf-8")


async def load_xmltv(source: str) -> Dict[str, Any]:
    now = time.time()
    if _CACHE.content and (now - _CACHE.ts) < _TTL_SECONDS:
        return _CACHE.content

    if source.startswith("http://") or source.startswith("https://"):
        raw = await _fetch_remote(source)
    else:
        raw = _read_local(source)

    data = xmltodict.parse(raw)
    _CACHE.content = data
    _CACHE.ts = now
    return data


def _normalize_epg(data: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    tv = data.get("tv", {}) if isinstance(data, dict) else {}
    channels_src = tv.get("channel", [])
    progs_src = tv.get("programme", [])

    # Garantir listas
    if isinstance(channels_src, dict):
        channels_src = [channels_src]
    if isinstance(progs_src, dict):
        progs_src = [progs_src]

    channels: Dict[str, Dict[str, Any]] = {}
    programs: Dict[str, List[Dict[str, Any]]] = {}

    for ch in channels_src:
        cid = ch.get("@id")
        if not cid:
            continue
        display = ch.get("display-name")
        if isinstance(display, list):
            display_name = display[0].get("#text") if isinstance(display[0], dict) else str(display[0])
        elif isinstance(display, dict):
            display_name = display.get("#text")
        else:
            display_name = display

        icon = None
        icon_field = ch.get("icon")
        if isinstance(icon_field, dict):
            icon = icon_field.get("@src")
        elif isinstance(icon_field, list) and icon_field:
            icon = icon_field[0].get("@src") if isinstance(icon_field[0], dict) else None

        channels[cid] = {"id": cid, "name": display_name, "icon": icon}
        programs[cid] = []

    for p in progs_src:
        cid = p.get("@channel")
        if not cid:
            continue
        title_field = p.get("title")
        if isinstance(title_field, dict):
            title = title_field.get("#text")
        elif isinstance(title_field, list) and title_field:
            title = title_field[0].get("#text") if isinstance(title_field[0], dict) else str(title_field[0])
        else:
            title = title_field

        desc_field = p.get("desc")
        if isinstance(desc_field, dict):
            description = desc_field.get("#text")
        elif isinstance(desc_field, list) and desc_field:
            description = desc_field[0].get("#text") if isinstance(desc_field[0], dict) else str(desc_field[0])
        else:
            description = desc_field

        start = _parse_xmltv_time(p.get("@start"))
        stop = _parse_xmltv_time(p.get("@stop"))

        item = {
            "title": title,
            "description": description,
            "start": start,
            "stop": stop,
        }
        programs.setdefault(cid, []).append(item)

    # Ordenar programas por início quando possível
    for cid, lst in programs.items():
        lst.sort(key=lambda x: (x.get("start") or ""))

    return channels, programs


async def get_epg(source: str) -> Dict[str, Any]:
    data = await load_xmltv(source)
    channels, programs = _normalize_epg(data)
    return {"channels": channels, "programs": programs}


async def get_channel_epg(source: str, channel_id: str) -> Dict[str, Any]:
    epg = await get_epg(source)
    channel = epg["channels"].get(channel_id)
    if not channel:
        return {"channel": None, "programs": []}
    return {"channel": channel, "programs": epg["programs"].get(channel_id, [])}
