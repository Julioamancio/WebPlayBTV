import logging
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.api.deps.auth import require_active_license
from app.models import User
from app.services.stream import decompress_response, get_cookie_jar_for_origin

router = APIRouter(prefix="/stream", tags=["stream"])
logger = logging.getLogger("webplayer.stream")


@router.get("/m3u8")
def proxy_m3u8(
    url: str,
    current_user: User = Depends(require_active_license),
    *,
    request: Request,
) -> Response:
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
                "Accept": "application/vnd.apple.mpegurl,application/x-mpegURL,text/plain,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Connection": "keep-alive",
                "Referer": referer,
                "Origin": referer,
            },
        )
        key = origin.netloc
        jar = get_cookie_jar_for_origin(key)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        with opener.open(req, timeout=30) as response:
            raw = response.read()
            data_bytes = decompress_response(raw, response.headers.get("Content-Encoding"))
            charset = "utf-8"
            content_type = response.headers.get("Content-Type") or ""
            if "charset=" in content_type.lower():
                charset = content_type.split("charset=")[-1].split(";")[0]
            content = data_bytes.decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        try:
            body_bytes = exc.read()
            body = body_bytes.decode("utf-8", errors="ignore") if body_bytes else ""
        except Exception:
            body = ""
        snippet = body[:300]
        logger.error(
            "Upstream m3u8 HTTPError %s for %s: %s; body=%s",
            exc.code,
            url,
            exc.reason,
            snippet,
        )
        raise HTTPException(
            status_code=exc.code or 400,
            detail=f"Failed to load m3u8: {exc.reason}; body={snippet}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Upstream m3u8 error for %s: %s", url, exc)
        raise HTTPException(status_code=400, detail=f"Failed to load m3u8: {exc}") from exc

    proxied_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            proxied_lines.append(line)
            continue

        if stripped.lower().startswith("http"):
            absolute_uri = stripped
        else:
            absolute_uri = urllib.parse.urljoin(url, stripped)

        token = None
        device_id = None
        if request:
            auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                token = auth_header.split(" ", 1)[1].strip()
            if not token:
                token = request.query_params.get("token")
            device_id = request.headers.get("X-Device-ID") or request.query_params.get("device_id")

        query_params = {k: v for k, v in [("url", absolute_uri), ("token", token), ("device_id", device_id)] if v}
        proxied = f"/stream/segment?{urllib.parse.urlencode(query_params)}"
        proxied_lines.append(proxied)

    result = "\n".join(proxied_lines)
    return Response(result, media_type="application/vnd.apple.mpegurl")


@router.get("/segment")
def proxy_segment(
    url: str,
    current_user: User = Depends(require_active_license),
) -> Response:
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
                "Accept": "*/*",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Connection": "keep-alive",
                "Referer": referer,
                "Origin": referer,
            },
        )
        key = origin.netloc
        jar = get_cookie_jar_for_origin(key)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        with opener.open(req, timeout=30) as response:
            raw = response.read()
            data_bytes = decompress_response(raw, response.headers.get("Content-Encoding"))
            mime = response.headers.get("Content-Type") or "application/octet-stream"
            return Response(data_bytes, media_type=mime)
    except urllib.error.HTTPError as exc:
        try:
            body_bytes = exc.read()
            body = body_bytes.decode("utf-8", errors="ignore") if body_bytes else ""
        except Exception:
            body = ""
        snippet = body[:300]
        logger.error(
            "Upstream segment HTTPError %s for %s: %s; body=%s",
            exc.code,
            url,
            exc.reason,
            snippet,
        )
        raise HTTPException(
            status_code=exc.code or 400,
            detail=f"Failed to load segment: {exc.reason}; body={snippet}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Upstream segment error for %s: %s", url, exc)
        raise HTTPException(status_code=400, detail=f"Failed to load segment: {exc}") from exc
