from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlmodel import Session, select

from app.db import get_session
from app.models import Playlist, AuditLog
from app.routers.auth import get_current_user, UserProfile
from app.services.m3u import load_m3u_text, parse_m3u


router = APIRouter(prefix="/playlists", tags=["playlists"])


class PlaylistCreate(BaseModel):
    name: str
    type: str
    url: str
    epg_url: Optional[str] = None


class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    epg_url: Optional[str] = None
    active: Optional[bool] = None


class PlaylistResponse(BaseModel):
    id: int
    name: str
    type: str
    url: str
    epg_url: Optional[str]
    active: bool


class PlaylistReloadSummary(BaseModel):
    total_channels: int
    by_group: dict[str, int]
    categories: dict[str, int]


@router.get("/me", response_model=List[PlaylistResponse])
def list_my_playlists(
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    items = session.exec(select(Playlist).where(Playlist.owner_username == current_user.username)).all()
    return [
        PlaylistResponse(
            id=i.id,
            name=i.name,
            type=i.type,
            url=i.url,
            epg_url=i.epg_url,
            active=i.active,
        )
        for i in items
    ]


@router.post("/create", response_model=PlaylistResponse)
def create_playlist(
    data: PlaylistCreate,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    item = Playlist(
        owner_username=current_user.username,
        name=data.name.strip(),
        type=data.type.strip().lower(),
        url=data.url.strip(),
        epg_url=(data.epg_url.strip() if data.epg_url else None),
        active=False,
    )
    session.add(item)
    session.add(
        AuditLog(
            actor_username=current_user.username,
            action="playlist.create",
            resource="playlist",
            resource_id=None,
            details=f"name={item.name} type={item.type}",
        )
    )
    session.commit()
    session.refresh(item)
    return PlaylistResponse(id=item.id, name=item.name, type=item.type, url=item.url, epg_url=item.epg_url, active=item.active)


@router.put("/{playlist_id}", response_model=PlaylistResponse)
def update_playlist(
    playlist_id: int,
    data: PlaylistUpdate,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    item = session.get(Playlist, playlist_id)
    if not item or item.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist não encontrada")
    if data.name is not None:
        item.name = data.name.strip()
    if data.type is not None:
        item.type = data.type.strip().lower()
    if data.url is not None:
        item.url = data.url.strip()
    if data.epg_url is not None:
        item.epg_url = data.epg_url.strip() if data.epg_url else None
    if data.active is not None:
        item.active = bool(data.active)
        if item.active:
            # desativar outras playlists do usuário
            others = session.exec(select(Playlist).where(Playlist.owner_username == current_user.username, Playlist.id != item.id)).all()
            for o in others:
                o.active = False
    session.add(
        AuditLog(
            actor_username=current_user.username,
            action="playlist.update",
            resource="playlist",
            resource_id=item.id,
            details=f"active={item.active}",
        )
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return PlaylistResponse(id=item.id, name=item.name, type=item.type, url=item.url, epg_url=item.epg_url, active=item.active)


@router.delete("/{playlist_id}")
def delete_playlist(
    playlist_id: int,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    item = session.get(Playlist, playlist_id)
    if not item or item.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist não encontrada")
    session.delete(item)
    session.add(
        AuditLog(
            actor_username=current_user.username,
            action="playlist.delete",
            resource="playlist",
            resource_id=playlist_id,
            details=f"name={item.name}",
        )
    )
    session.commit()
    return {"ok": True}


@router.post("/{playlist_id}/activate", response_model=PlaylistResponse)
def activate_playlist(
    playlist_id: int,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    item = session.get(Playlist, playlist_id)
    if not item or item.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist não encontrada")
    # ativar e desativar demais
    item.active = True
    others = session.exec(select(Playlist).where(Playlist.owner_username == current_user.username, Playlist.id != item.id)).all()
    for o in others:
        o.active = False
    session.add(
        AuditLog(
            actor_username=current_user.username,
            action="playlist.activate",
            resource="playlist",
            resource_id=item.id,
            details=f"name={item.name}",
        )
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return PlaylistResponse(id=item.id, name=item.name, type=item.type, url=item.url, epg_url=item.epg_url, active=item.active)


@router.post("/{playlist_id}/reload", response_model=PlaylistReloadSummary)
async def reload_playlist(
    playlist_id: int,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user),
):
    item = session.get(Playlist, playlist_id)
    if not item or item.owner_username != current_user.username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist não encontrada")
    try:
        text = await load_m3u_text(item.url, force=True)
        channels = parse_m3u(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao carregar lista: {e}")

    # Contagem por grupo
    by_group: dict[str, int] = {}
    for ch in channels:
        grp = (ch.get("group") or "").strip() or "Sem grupo"
        by_group[grp] = by_group.get(grp, 0) + 1

    # Heurísticas simples para categorias TV/Filmes/Séries
    def is_movies(ch: dict) -> bool:
        g = (ch.get("group") or "").lower()
        n = (ch.get("name") or "").lower()
        return any(k in g for k in ["movie", "filme", "movies"]) or any(k in n for k in ["filme", "movie"])

    def is_series(ch: dict) -> bool:
        g = (ch.get("group") or "").lower()
        n = (ch.get("name") or "").lower()
        return any(k in g for k in ["series", "serie", "seriados"]) or any(k in n for k in ["serie", "series"])

    movies_count = sum(1 for c in channels if is_movies(c))
    series_count = sum(1 for c in channels if is_series(c))
    tv_count = max(0, len(channels) - movies_count - series_count)

    # Registrar auditoria
    session.add(
        AuditLog(
            actor_username=current_user.username,
            action="playlist.reload",
            resource="playlist",
            resource_id=item.id,
            details=f"total={len(channels)}"
        )
    )
    session.commit()

    return PlaylistReloadSummary(
        total_channels=len(channels),
        by_group=by_group,
        categories={"tv": tv_count, "filmes": movies_count, "series": series_count},
    )
