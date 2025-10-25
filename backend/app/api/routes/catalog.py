from datetime import datetime
from typing import List, Optional
import re
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps.auth import require_active_license
from app.db.session import get_db
from app.models import Channel, M3UPlaylist, User
from app.schemas import (
    ChannelResponse,
    M3UPlaylistResponse,
    M3UPlaylistUpdate,
)
from app.services.audit import audit_event
from app.services.m3u import parse_m3u
from app.services.stream import decompress_response

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post("/m3u/ingest", response_model=List[ChannelResponse])
def ingest_m3u_playlist(
    name: str,
    url: Optional[str] = None,
    content: Optional[str] = None,
    current_user: User = Depends(require_active_license),
    db: Session = Depends(get_db),
    *,
    request: Request,
):
    if not url and not content:
        raise HTTPException(status_code=400, detail="Provide url or content")

    data = content
    if url:
        if not url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Only http/https URLs are allowed")
        try:
            origin = urllib.parse.urlsplit(url)
            referer = f"{origin.scheme}://{origin.netloc}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/117.0 Safari/537.36",
                    "Accept": "text/plain,application/vnd.apple.mpegurl,application/x-mpegURL,*/*;q=0.8",
                    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "Connection": "keep-alive",
                    "Referer": referer,
                },
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read()
                data_bytes = decompress_response(raw, response.headers.get("Content-Encoding"))
                content_type = response.headers.get("Content-Type") or ""
        except urllib.error.HTTPError as exc:
            raise HTTPException(
                status_code=exc.code or 400,
                detail=f"Failed to download M3U: {exc.reason}",
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=400, detail=f"Failed to download M3U: {exc}"
            ) from exc
        else:
            charset = "utf-8"
            match = re.search(r"charset=([\w-]+)", content_type, re.IGNORECASE)
            if match:
                charset = match.group(1)
            data = data_bytes.decode(charset, errors="replace")

    if not data or "#EXTM3U" not in data:
        raise HTTPException(status_code=400, detail="Invalid M3U content")

    parsed_channels = parse_m3u(data)
    stored_content = data if (not url and content) else None
    created: List[Channel] = []

    try:
        playlist = M3UPlaylist(
            name=name,
            url=url,
            content=stored_content,
            channels_count=len(parsed_channels),
            last_updated=datetime.utcnow(),
            is_active=True,
            user_id=current_user.id,
        )
        db.add(playlist)
        db.flush()

        urls = {ch.get("url") for ch in parsed_channels if ch.get("url")}
        existing_by_url: dict[str, Channel] = {}
        if urls:
            existing_channels = (
                db.query(Channel)
                .filter(Channel.user_id == current_user.id, Channel.url.in_(urls))
                .all()
            )
            existing_by_url = {channel.url: channel for channel in existing_channels}

        for channel_data in parsed_channels:
            channel_url = channel_data.get("url")
            if not channel_url:
                continue
            existing_channel = existing_by_url.get(channel_url)
            if existing_channel:
                existing_channel.name = channel_data["name"]
                existing_channel.logo_url = channel_data.get("logo_url")
                existing_channel.category = channel_data.get("category")
                existing_channel.country = channel_data.get("country")
                existing_channel.language = channel_data.get("language")
                existing_channel.is_active = True
                existing_channel.playlist_id = playlist.id
                existing_channel.updated_at = datetime.utcnow()
                created.append(existing_channel)
            else:
                new_channel = Channel(
                    name=channel_data["name"],
                    url=channel_url,
                    logo_url=channel_data.get("logo_url"),
                    category=channel_data.get("category"),
                    country=channel_data.get("country"),
                    language=channel_data.get("language"),
                    is_active=True,
                    user_id=current_user.id,
                    playlist_id=playlist.id,
                )
                db.add(new_channel)
                created.append(new_channel)

        playlist.channels_count = len(created)
        db.flush()
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        raise

    db.refresh(playlist)
    for channel in created:
        db.refresh(channel)

    audit_event(
        db,
        current_user.id,
        action="m3u_ingest",
        resource="playlist",
        resource_id=playlist.id,
        request=request,
    )
    return created


@router.get("/channels", response_model=List[ChannelResponse])
def list_channels(
    playlist_id: Optional[int] = None,
    current_user: User = Depends(require_active_license),
    db: Session = Depends(get_db),
) -> List[Channel]:
    query = db.query(Channel).filter(
        Channel.user_id == current_user.id, Channel.is_active.is_(True)
    )
    if playlist_id is not None:
        query = query.filter(Channel.playlist_id == playlist_id)
    return query.order_by(Channel.created_at.asc()).all()


@router.get("/playlists", response_model=List[M3UPlaylistResponse])
def list_playlists(
    current_user: User = Depends(require_active_license),
    db: Session = Depends(get_db),
) -> List[M3UPlaylist]:
    return (
        db.query(M3UPlaylist)
        .filter(M3UPlaylist.user_id == current_user.id)
        .order_by(M3UPlaylist.created_at.desc())
        .all()
    )


@router.patch("/playlists/{playlist_id}", response_model=M3UPlaylistResponse)
def update_playlist(
    playlist_id: int,
    payload: M3UPlaylistUpdate,
    current_user: User = Depends(require_active_license),
    db: Session = Depends(get_db),
    *,
    request: Request,
) -> M3UPlaylist:
    playlist = (
        db.query(M3UPlaylist)
        .filter(M3UPlaylist.id == playlist_id, M3UPlaylist.user_id == current_user.id)
        .first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    if payload.name is not None:
        playlist.name = payload.name
    if payload.url is not None:
        playlist.url = payload.url
    if payload.is_active is not None:
        playlist.is_active = payload.is_active

    playlist.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(playlist)

    audit_event(
        db,
        current_user.id,
        action="playlist_update",
        resource="playlist",
        resource_id=playlist.id,
        request=request,
    )
    return playlist


@router.delete("/playlists/{playlist_id}")
def delete_playlist(
    playlist_id: int,
    current_user: User = Depends(require_active_license),
    db: Session = Depends(get_db),
    *,
    request: Request,
) -> dict[str, object]:
    playlist = (
        db.query(M3UPlaylist)
        .filter(M3UPlaylist.id == playlist_id, M3UPlaylist.user_id == current_user.id)
        .first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    db.delete(playlist)
    db.commit()
    audit_event(
        db,
        current_user.id,
        action="playlist_delete",
        resource="playlist",
        resource_id=playlist_id,
        request=request,
    )
    return {"status": "deleted", "id": playlist_id}
