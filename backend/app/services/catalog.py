from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.m3u import load_m3u_text, parse_m3u
from app.services.epg import get_epg


def _to_dt(iso_str: Optional[str]) -> Optional[datetime]:
    if not iso_str:
        return None
    s = iso_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


async def get_enriched_channels(m3u_source: str, epg_source: str, force: bool = False) -> List[Dict[str, Any]]:
    text = await load_m3u_text(m3u_source, force=force)
    channels = parse_m3u(text)

    epg = await get_epg(epg_source)
    epg_channels_raw: Dict[str, Dict[str, Any]] = epg.get("channels", {})
    # Helpers de normalização
    def _norm(s: Optional[str]) -> Optional[str]:
        return s.strip().lower() if isinstance(s, str) else None

    # Mapear por id case-insensitive e por nome normalizado (fallback)
    epg_by_id = {k.lower(): v for k, v in epg_channels_raw.items()}
    epg_by_name: Dict[str, Dict[str, Any]] = {}
    for cid, info in epg_channels_raw.items():
        nm = _norm(info.get("name"))
        if nm:
            epg_by_name[nm] = info

    enriched: List[Dict[str, Any]] = []
    for ch in channels:
        tvg_id = ch.get("tvg_id")
        key = tvg_id.lower() if isinstance(tvg_id, str) else None
        epg_info = epg_by_id.get(key) if key else None
        if not epg_info:
            # Fallback por nome quando tvg-id estiver ausente ou não casar
            name_norm = _norm(ch.get("name"))
            if name_norm:
                epg_info = epg_by_name.get(name_norm)
        item = {
            **ch,
            "epg": epg_info,  # pode ser None
        }
        enriched.append(item)
    return enriched


async def get_now(m3u_source: str, epg_source: str, ref_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
    epg = await get_epg(epg_source)
    channels_raw = epg.get("channels", {})
    programs_raw = epg.get("programs", {})
    channels = {k.lower(): v for k, v in channels_raw.items()}
    programs = {k.lower(): v for k, v in programs_raw.items()}

    now = ref_time.astimezone(timezone.utc) if ref_time else datetime.now(timezone.utc)

    # Carregar m3u para ordenar conforme a lista do usuário e mapear tvg_id
    m3u_text = await load_m3u_text(m3u_source, force=False)
    m3u_channels = parse_m3u(m3u_text)

    results: List[Dict[str, Any]] = []
    for ch in m3u_channels:
        tvg_id = ch.get("tvg_id")
        key = tvg_id.lower() if isinstance(tvg_id, str) else None
        if not key or key not in channels:
            continue
        plist = programs.get(key, [])
        current = None
        upcoming = None
        for p in plist:
            s = _to_dt(p.get("start"))
            e = _to_dt(p.get("stop"))
            if not s or not e:
                continue
            if s <= now < e:
                current = p
            if s > now and upcoming is None:
                upcoming = p
            if current and upcoming:
                break

        results.append(
            {
                "tvg_id": tvg_id,
                "name": ch.get("name"),
                "logo": ch.get("logo") or channels.get(key, {}).get("icon"),
                "current": current,
                "next": upcoming,
            }
        )

    return results
