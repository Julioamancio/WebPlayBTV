from __future__ import annotations
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from urllib.parse import urljoin, urlparse, quote
import httpx
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


# Proxy simples para HLS/DASH com cabeçalhos customizados
@router.get("/proxy")
async def stream_proxy(
    request: Request,
    url: str = Query(..., description="URL do recurso a ser proxyado (playlist .m3u8, .mpd ou segmento)"),
    ua: str | None = Query(default=None, description="User-Agent a ser enviado"),
    referer: str | None = Query(default=None, description="Referer a ser enviado"),
    token: str | None = Query(default=None, description="Token a anexar como query na URL (opcional)"),
):
    try:
        # Anexar token como query se fornecido
        target = url
        if token:
            sep = '&' if ('?' in target) else '?'
            target = f"{target}{sep}token={quote(token)}"

        # Headers base
        hdrs = {
            'User-Agent': ua or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
            'Accept': 'application/vnd.apple.mpegurl,application/x-mpegURL,video/*;q=0.9,*/*;q=0.8',
        }
        # Propagar Range e outros headers relevantes
        rng = request.headers.get('range')
        if rng: hdrs['Range'] = rng
        if referer:
            hdrs['Referer'] = referer
            # Alguns providers checam Origin também
            try:
                parsed = urlparse(referer)
                origin = f"{parsed.scheme}://{parsed.netloc}"
                hdrs['Origin'] = origin
            } except Exception:
                pass

        async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(20.0)) as client:
            resp = await client.get(target, headers=hdrs)
            if resp.status_code >= 400:
                raise HTTPException(status_code=resp.status_code, detail=f"Proxy falhou: {resp.text[:300]}")
            ctype = resp.headers.get('content-type', '')
            # Reescrever playlists HLS para que segmentos passem pelo proxy
            if 'application/vnd.apple.mpegurl' in ctype or 'application/x-mpegURL' in ctype or target.lower().endswith('.m3u8'):
                text = resp.text
                base_url = str(resp.url)
                base_dir = base_url.rsplit('/', 1)[0] + '/'
                proxied = []
                for line in text.splitlines():
                    if line.startswith('#EXT-X-KEY') and 'URI=' in line:
                        # Reescrever URI do KEY
                        try:
                            import re
                            def repl(m):
                                uri = m.group(1)
                                absu = uri if uri.startswith('http') else urljoin(base_dir, uri)
                                return f'URI="/catalog/proxy?url={quote(absu, safe="")}"'
                            line = re.sub(r'URI="([^"]+)"', repl, line)
                        except Exception:
                            pass
                        proxied.append(line)
                    elif line.startswith('#') or not line.strip():
                        proxied.append(line)
                    else:
                        # Linha de recurso (segmento ou playlist aninhada)
                        absu = line if line.startswith('http') else urljoin(base_dir, line)
                        proxied.append(f"/catalog/proxy?url={quote(absu, safe='')}" )
                body = "\n".join(proxied)
                return Response(content=body, media_type='application/vnd.apple.mpegurl')
            # Caso geral: stream pass-through
            headers = { 'Content-Type': ctype }
            # Propagar content-length e accept-ranges quando disponíveis
            cl = resp.headers.get('content-length')
            if cl: headers['Content-Length'] = cl
            ar = resp.headers.get('accept-ranges')
            if ar: headers['Accept-Ranges'] = ar
            return StreamingResponse(resp.aiter_bytes(), status_code=resp.status_code, headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no proxy: {e}")


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
