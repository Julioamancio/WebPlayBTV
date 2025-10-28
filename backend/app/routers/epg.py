import os
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
import json
import hashlib
from datetime import datetime, timezone
import time
from prometheus_client import Counter, Histogram

from app.services.epg import get_channel_epg, get_epg
from app.config import EPG_TTL_SECONDS


router = APIRouter(prefix="/catalog", tags=["catalog"])


def _epg_source() -> str:
    return os.getenv("EPG_SOURCE", "sample.xml")


# Cache por parâmetros (query-aware) para o endpoint global /catalog/epg
_QUERY_CACHE: Dict[str, Tuple[float, Dict[str, Any], str]] = {}
_CACHE_TTL = float(EPG_TTL_SECONDS)

# Métricas Prometheus para observabilidade de /catalog/epg
EPG_QUERY_CACHE_TOTAL = Counter(
    "epg_query_cache_total",
    "Cache usage for /catalog/epg endpoint",
    ["result"],
)
EPG_FILTER_USAGE_TOTAL = Counter(
    "epg_filter_usage_total",
    "Usage of start/end filters in /catalog/epg",
    ["has_start", "has_end"],
)
EPG_PAGINATION_USAGE_TOTAL = Counter(
    "epg_pagination_usage_total",
    "Usage of pagination params in /catalog/epg",
    ["has_limit", "has_offset"],
)
EPG_LIMIT_PER_CHANNEL = Histogram(
    "epg_limit_per_channel",
    "Distribution of limit_per_channel values",
    buckets=(1, 2, 3, 5, 10, 20, 50, 100, 200, 500),
)
EPG_OFFSET_PER_CHANNEL = Histogram(
    "epg_offset_per_channel",
    "Distribution of offset_per_channel values",
    buckets=(0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000),
)


def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _make_cache_key(
    base_hash: str,
    start: Optional[datetime],
    end: Optional[datetime],
    limit_per_channel: Optional[int],
    offset_per_channel: int,
) -> str:
    return json.dumps(
        {
            "base": base_hash,
            "start": _dt_to_iso(start),
            "end": _dt_to_iso(end),
            "limit": limit_per_channel,
            "offset": offset_per_channel,
        },
        sort_keys=True,
    )


@router.get("/epg")
async def epg_catalog(
    request: Request,
    start: Optional[datetime] = Query(default=None, description="ISO8601; assume UTC se sem timezone"),
    end: Optional[datetime] = Query(default=None, description="ISO8601; assume UTC se sem timezone"),
    limit_per_channel: Optional[int] = Query(default=None, ge=1, description="Limite de programas por canal"),
    offset_per_channel: int = Query(default=0, ge=0, description="Deslocamento por canal"),
):
    source = _epg_source()
    try:
        data = await get_epg(source)
        # Base hash do EPG normalizado para invalidar cache quando conteúdo mudar
        base_payload = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
        base_hash = hashlib.sha256(base_payload).hexdigest()

        # Consultar cache por parâmetros
        cache_key = _make_cache_key(base_hash, start, end, limit_per_channel, offset_per_channel)
        now_ts = time.time()
        # Registrar uso de filtros/paginação
        has_start = "yes" if start is not None else "no"
        has_end = "yes" if end is not None else "no"
        has_limit = "yes" if limit_per_channel is not None else "no"
        has_offset = "yes" if (offset_per_channel or 0) > 0 else "no"
        EPG_FILTER_USAGE_TOTAL.labels(has_start=has_start, has_end=has_end).inc()
        EPG_PAGINATION_USAGE_TOTAL.labels(has_limit=has_limit, has_offset=has_offset).inc()
        if limit_per_channel is not None:
            try:
                EPG_LIMIT_PER_CHANNEL.observe(float(limit_per_channel))
            except Exception:
                pass
        try:
            EPG_OFFSET_PER_CHANNEL.observe(float(offset_per_channel))
        except Exception:
            pass

        cached = _QUERY_CACHE.get(cache_key)
        if cached and (now_ts - cached[0]) < _CACHE_TTL:
            cached_data, cached_etag = cached[1], cached[2]
            inm = request.headers.get("if-none-match")
            if inm == cached_etag:
                EPG_QUERY_CACHE_TOTAL.labels(result="hit").inc()
                return Response(status_code=304)
            EPG_QUERY_CACHE_TOTAL.labels(result="hit").inc()
            return JSONResponse(content=cached_data, headers={"ETag": cached_etag})
        else:
            EPG_QUERY_CACHE_TOTAL.labels(result="miss").inc()
        # Aplicar filtros globais por intervalo e paginação por canal
        if start is not None or end is not None or limit_per_channel is not None or offset_per_channel:
            # Normalizar timezone (assume UTC se ausente)
            ref_start = start if (start is None or start.tzinfo) else start.replace(tzinfo=timezone.utc)
            ref_end = end if (end is None or end.tzinfo) else end.replace(tzinfo=timezone.utc)
            programs = data.get("programs", {})
            new_programs: Dict[str, List[Dict[str, Any]]] = {}
            for cid, plist in programs.items():
                filtered: List[Dict[str, Any]] = []
                for p in plist:
                    s = _to_dt(p.get("start"))
                    e = _to_dt(p.get("stop"))
                    if not s or not e:
                        continue
                    if ref_start and e <= ref_start:
                        continue
                    if ref_end and s >= ref_end:
                        continue
                    filtered.append(p)
                # Paginação por canal
                start_idx = offset_per_channel if offset_per_channel >= 0 else 0
                end_idx = start_idx + limit_per_channel if (limit_per_channel is not None) else None
                new_programs[cid] = filtered[start_idx:end_idx]
            data = {**data, "programs": new_programs}

        payload = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
        etag = hashlib.sha256(payload).hexdigest()
        inm = request.headers.get("if-none-match")
        if inm == etag:
            return Response(status_code=304)
        # Armazenar no cache por parâmetros
        _QUERY_CACHE[cache_key] = (now_ts, data, etag)
        return JSONResponse(content=data, headers={"ETag": etag})
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Arquivo EPG não encontrado: {e}")


def _to_dt(iso_str: Optional[str]) -> Optional[datetime]:
    if not iso_str:
        return None
    s = iso_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


@router.get("/epg/{channel_id}")
async def epg_channel(
    channel_id: str,
    start: Optional[datetime] = Query(default=None, description="ISO8601; assume UTC se sem timezone"),
    end: Optional[datetime] = Query(default=None, description="ISO8601; assume UTC se sem timezone"),
    limit: Optional[int] = Query(default=None, ge=1, description="Limite de programas retornados"),
    offset: int = Query(default=0, ge=0, description="Deslocamento inicial para paginação"),
):
    source = _epg_source()
    try:
        data = await get_channel_epg(source, channel_id)
        if not data.get("channel"):
            raise HTTPException(status_code=404, detail="Canal não encontrado no EPG")
        # Se sem filtros, retorna completo
        if start is None and end is None:
            return data

        # Normalizar timezone (assume UTC se ausente)
        ref_start = start if (start is None or start.tzinfo) else start.replace(tzinfo=timezone.utc)
        ref_end = end if (end is None or end.tzinfo) else end.replace(tzinfo=timezone.utc)

        progs: List[Dict[str, Any]] = data.get("programs", [])
        filtered: List[Dict[str, Any]] = []
        for p in progs:
            s = _to_dt(p.get("start"))
            e = _to_dt(p.get("stop"))
            if not s or not e:
                continue
            # Critério de sobreposição do intervalo [start, end):
            # - Se start fornecido: programa precisa terminar depois de start
            # - Se end fornecido: programa precisa iniciar antes de end
            if ref_start and e <= ref_start:
                continue
            if ref_end and s >= ref_end:
                continue
            filtered.append(p)

        # Aplicar paginação
        start_idx = offset if offset >= 0 else 0
        end_idx = start_idx + limit if (limit is not None) else None
        paginated = filtered[start_idx:end_idx]

        return {**data, "programs": paginated}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Arquivo EPG não encontrado: {e}")
