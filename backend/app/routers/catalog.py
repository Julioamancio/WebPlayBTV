from __future__ import annotations
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import hashlib

from app.config import os as _os  # reuse loaded dotenv context
from app.services.m3u import load_m3u_text, parse_m3u
from app.services.catalog import get_enriched_channels, get_now
from sqlmodel import Session, select
from app.db import get_session
from app.models import Playlist
from app.routers.auth import get_current_user, UserProfile


router = APIRouter(prefix="/catalog", tags=["catalog"])


class ChannelResponse(BaseModel):
    name: str
    url: str
    tvg_id: str | None = None
    group: str | None = None
    logo: str | None = None


class ProgramItem(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start: Optional[str] = None
    stop: Optional[str] = None


class EpgInfo(BaseModel):
    id: str
    name: Optional[str] = None
    icon: Optional[str] = None


class EnrichedChannelResponse(ChannelResponse):
    epg: Optional[EpgInfo] = None
    current: Optional[ProgramItem] = None
    next: Optional[ProgramItem] = None


class NowItem(BaseModel):
    tvg_id: str
    name: Optional[str] = None
    logo: Optional[str] = None
    current: Optional[ProgramItem] = None
    next: Optional[ProgramItem] = None


class NextItem(BaseModel):
    tvg_id: str
    name: Optional[str] = None
    logo: Optional[str] = None
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

def _get_active_playlist(
    session: Session,
    current_user: UserProfile,
) -> Playlist | None:
    try:
        return session.exec(
            select(Playlist).where(
                Playlist.owner_username == current_user.username,
                Playlist.active == True,
            )
        ).first()
    except Exception:
        return None


@router.get("/m3u", response_class=PlainTextResponse)
async def get_m3u(request: Request, force: bool = Query(default=False)):
    source = _get_source()
    try:
        text = await load_m3u_text(source, force=force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    etag = hashlib.sha256(text.encode("utf-8")).hexdigest()
    inm = request.headers.get("if-none-match")
    if inm == etag:
        return Response(status_code=304)
    return PlainTextResponse(text, headers={"ETag": etag})


@router.get("/next", response_model=List[NextItem])
async def get_next_program(time: Optional[datetime] = Query(default=None, description="ISO8601; assume UTC se sem timezone")):
    m3u_source = _get_source()
    epg_source = _get_epg_source()
    try:
        ref_time = None
        if time is not None:
            ref_time = time if time.tzinfo else time.replace(tzinfo=timezone.utc)
        items = await get_now(m3u_source, epg_source, ref_time=ref_time)
        result: List[NextItem] = []
        for it in items:
            result.append(
                NextItem(
                    tvg_id=it.get("tvg_id"),
                    name=it.get("name"),
                    logo=it.get("logo"),
                    next=ProgramItem(**it["next"]) if it.get("next") else None,
                )
            )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Fonte EPG não encontrada: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels", response_model=List[ChannelResponse])
async def get_channels(force: bool = Query(default=False)):
    source = _get_source()
    try:
        text = await load_m3u_text(source, force=force)
        channels = parse_m3u(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return [ChannelResponse(**c) for c in channels]


@router.get("/channels/me", response_model=List[ChannelResponse])
async def get_channels_me(
    force: bool = Query(default=False),
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    item = _get_active_playlist(session, current_user)
    if not item:
        raise HTTPException(status_code=404, detail="Nenhuma playlist ativa para este usuário")
    try:
        text = await load_m3u_text(item.url, force=force)
        channels = parse_m3u(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return [ChannelResponse(**c) for c in channels]


@router.get("/channels/enriched", response_model=List[EnrichedChannelResponse])
async def get_channels_enriched(
    force: bool = Query(default=False),
    include_now: bool = Query(default=False, description="Inclui current/next por canal"),
    time: Optional[datetime] = Query(default=None, description="ISO8601; assume UTC se sem timezone"),
):
    m3u_source = _get_source()
    epg_source = _get_epg_source()
    try:
        items = await get_enriched_channels(m3u_source, epg_source, force=force)
        now_map = {}
        if include_now:
            ref_time = None
            if time is not None:
                ref_time = time if time.tzinfo else time.replace(tzinfo=timezone.utc)
            now_items = await get_now(m3u_source, epg_source, ref_time=ref_time)
            # mapear por tvg_id (case-insensitive)
            for it in now_items:
                tid = it.get("tvg_id")
                key = tid.lower() if isinstance(tid, str) else None
                if key:
                    now_map[key] = {
                        "current": it.get("current"),
                        "next": it.get("next"),
                    }
        # Modelagem: epg pode ser None ou dict compatível com EpgInfo
        result: List[EnrichedChannelResponse] = []
        for it in items:
            epg = it.get("epg")
            payload = {k: it.get(k) for k in ["name", "url", "tvg_id", "group", "logo"]}
            if epg:
                payload["epg"] = EpgInfo(**epg)  # type: ignore[arg-type]
            if include_now:
                tvg_id = it.get("tvg_id")
                key = tvg_id.lower() if isinstance(tvg_id, str) else None
                if key and key in now_map:
                    nm = now_map[key]
                    if nm.get("current"):
                        payload["current"] = ProgramItem(**nm["current"])  # type: ignore[arg-type]
                    if nm.get("next"):
                        payload["next"] = ProgramItem(**nm["next"])  # type: ignore[arg-type]
            result.append(EnrichedChannelResponse(**payload))
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Fonte EPG não encontrada: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels/enriched/me", response_model=List[EnrichedChannelResponse])
async def get_channels_enriched_me(
    force: bool = Query(default=False),
    include_now: bool = Query(default=False, description="Inclui current/next por canal"),
    time: Optional[datetime] = Query(default=None, description="ISO8601; assume UTC se sem timezone"),
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    item = _get_active_playlist(session, current_user)
    if not item:
        raise HTTPException(status_code=404, detail="Nenhuma playlist ativa para este usuário")
    m3u_source = item.url
    epg_source = item.epg_url or _get_epg_source()
    try:
        items = await get_enriched_channels(m3u_source, epg_source, force=force)
        now_map = {}
        if include_now:
            ref_time = None
            if time is not None:
                ref_time = time if time.tzinfo else time.replace(tzinfo=timezone.utc)
            now_items = await get_now(m3u_source, epg_source, ref_time=ref_time)
            for it in now_items:
                tid = it.get("tvg_id")
                key = tid.lower() if isinstance(tid, str) else None
                if key:
                    now_map[key] = {
                        "current": it.get("current"),
                        "next": it.get("next"),
                    }
        result: List[EnrichedChannelResponse] = []
        for it in items:
            epg = it.get("epg")
            payload = {k: it.get(k) for k in ["name", "url", "tvg_id", "group", "logo"]}
            if epg:
                payload["epg"] = EpgInfo(**epg)  # type: ignore[arg-type]
            if include_now:
                tvg_id = it.get("tvg_id")
                key = tvg_id.lower() if isinstance(tvg_id, str) else None
                if key and key in now_map:
                    nm = now_map[key]
                    if nm.get("current"):
                        payload["current"] = ProgramItem(**nm["current"])  # type: ignore[arg-type]
                    if nm.get("next"):
                        payload["next"] = ProgramItem(**nm["next"])  # type: ignore[arg-type]
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
