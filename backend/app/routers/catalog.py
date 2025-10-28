from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.config import os as _os  # reuse loaded dotenv context
from app.services.m3u import load_m3u_text, parse_m3u
from app.services.catalog import get_enriched_channels, get_now


router = APIRouter(prefix="/catalog", tags=["catalog"])


class ChannelResponse(BaseModel):
    name: str
    url: str
    tvg_id: str | None = None
    group: str | None = None
    logo: str | None = None


class EpgInfo(BaseModel):
    id: str
    name: Optional[str] = None
    icon: Optional[str] = None


class EnrichedChannelResponse(ChannelResponse):
    epg: Optional[EpgInfo] = None


class ProgramItem(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start: Optional[str] = None
    stop: Optional[str] = None


class NowItem(BaseModel):
    tvg_id: str
    name: Optional[str] = None
    logo: Optional[str] = None
    current: Optional[ProgramItem] = None
    next: Optional[ProgramItem] = None


def _get_source() -> str:
    source = _os.getenv("M3U_SOURCE")
    if not source:
        # Fallback padrão para demonstração
        source = "sample.m3u"
    return source


def _get_epg_source() -> str:
    source = _os.getenv("EPG_SOURCE")
    if not source:
        source = "sample.xml"
    return source


@router.get("/m3u", response_class=PlainTextResponse)
async def get_m3u(force: bool = Query(default=False)):
    source = _get_source()
    try:
        text = await load_m3u_text(source, force=force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return PlainTextResponse(text)


@router.get("/channels", response_model=List[ChannelResponse])
async def get_channels(force: bool = Query(default=False)):
    source = _get_source()
    try:
        text = await load_m3u_text(source, force=force)
        channels = parse_m3u(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return [ChannelResponse(**c) for c in channels]


@router.get("/channels/enriched", response_model=List[EnrichedChannelResponse])
async def get_channels_enriched(force: bool = Query(default=False)):
    m3u_source = _get_source()
    epg_source = _get_epg_source()
    try:
        items = await get_enriched_channels(m3u_source, epg_source, force=force)
        # Modelagem: epg pode ser None ou dict compatível com EpgInfo
        result: List[EnrichedChannelResponse] = []
        for it in items:
            epg = it.get("epg")
            payload = {k: it.get(k) for k in ["name", "url", "tvg_id", "group", "logo"]}
            if epg:
                payload["epg"] = EpgInfo(**epg)  # type: ignore[arg-type]
            result.append(EnrichedChannelResponse(**payload))
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Fonte EPG não encontrada: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/now", response_model=List[NowItem])
async def get_now_playing(time: Optional[datetime] = Query(default=None, description="ISO8601; assume UTC se sem timezone")):
    m3u_source = _get_source()
    epg_source = _get_epg_source()
    try:
        ref_time = None
        if time is not None:
            ref_time = time if time.tzinfo else time.replace(tzinfo=timezone.utc)
        items = await get_now(m3u_source, epg_source, ref_time=ref_time)
        # Convert to pydantic models
        result: List[NowItem] = []
        for it in items:
            result.append(
                NowItem(
                    tvg_id=it.get("tvg_id"),
                    name=it.get("name"),
                    logo=it.get("logo"),
                    current=ProgramItem(**it["current"]) if it.get("current") else None,
                    next=ProgramItem(**it["next"]) if it.get("next") else None,
                )
            )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Fonte EPG não encontrada: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
