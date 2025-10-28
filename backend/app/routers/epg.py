import os
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone

from app.services.epg import get_channel_epg, get_epg


router = APIRouter(prefix="/catalog", tags=["catalog"])


def _epg_source() -> str:
    return os.getenv("EPG_SOURCE", "sample.xml")


@router.get("/epg")
async def epg_catalog():
    source = _epg_source()
    try:
        data = await get_epg(source)
        return data
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

        return {**data, "programs": filtered}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Arquivo EPG não encontrado: {e}")
