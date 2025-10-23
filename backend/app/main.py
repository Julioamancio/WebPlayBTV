from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from .database import SessionLocal, engine, get_db
from .models import Base, User, License, Device, AuditLog, Channel, M3UPlaylist
from .schemas import (
    UserCreate, UserResponse, LoginRequest, Token, TokenRefresh,
    LicenseCreate, LicenseResponse, DeviceCreate, DeviceResponse,
    DeviceUnbind, DeviceHeartbeat,
    ChannelResponse, M3UPlaylistResponse, M3UPlaylistUpdate
)
from .auth import (
    get_password_hash, authenticate_user, create_access_token, 
    create_refresh_token, verify_token, get_user_by_email, get_current_active_user, require_active_license
)
import secrets
import re
import urllib.request
import urllib.error
import urllib.parse
import gzip
import zlib
import http.cookiejar
import logging
import time
from datetime import datetime
from starlette.staticfiles import StaticFiles

# Criar tabelas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="WEBplayer JTV API")

# Simple cookie jars per origin to carry Set-Cookie between playlist and segments
COOKIE_JARS = {}
COOKIE_JAR_MAX = 32
COOKIE_JAR_TTL_SECONDS = 3600
logger = logging.getLogger("webplayer")


def get_cookie_jar_for_origin(key: str) -> http.cookiejar.CookieJar:
    """Return a cookie jar for the given origin, pruning stale entries."""
    now = time.time()
    stale_keys = [k for k, (_, ts) in COOKIE_JARS.items() if now - ts > COOKIE_JAR_TTL_SECONDS]
    for stale in stale_keys:
        COOKIE_JARS.pop(stale, None)
    if key in COOKIE_JARS:
        jar, _ = COOKIE_JARS[key]
        COOKIE_JARS[key] = (jar, now)
        return jar
    if len(COOKIE_JARS) >= COOKIE_JAR_MAX:
        oldest_key = min(COOKIE_JARS.items(), key=lambda kv: kv[1][1])[0]
        COOKIE_JARS.pop(oldest_key, None)
    jar = http.cookiejar.CookieJar()
    COOKIE_JARS[key] = (jar, now)
    return jar

# Dev CORS (ajustar em produção)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "file://",  # Para HTML local
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return RedirectResponse(url="/app/index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

# Helper de auditoria
def audit(db: Session, user_id: int, action: str, resource: str = None, resource_id: str = None, request: Request = None):
    ip = None
    ua = None
    if request:
        try:
            ip = request.client.host
        except Exception:
            ip = None
        ua = request.headers.get('user-agent')
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(log)
    db.commit()

@app.post("/auth/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db), request: Request = None):
    # Verificar se usuário já existe
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Criar usuário
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    audit(db, db_user.id, action="register", resource="user", resource_id=db_user.id, request=request)
    return db_user

@app.post("/auth/login", response_model=Token)
def login(form_data: LoginRequest, db: Session = Depends(get_db), request: Request = None):
    user = authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    audit(db, user.id, action="login", resource="user", resource_id=user.id, request=request)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/auth/refresh", response_model=Token)
def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    payload = verify_token(token_data.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.get("/auth/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.post("/licenses/issue", response_model=LicenseResponse)
def issue_license(payload: LicenseCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), request: Request = None):
    key = secrets.token_urlsafe(16)
    lic = License(
        license_key=key,
        user_id=current_user.id,
        plan_name=payload.plan_name,
        max_devices=payload.max_devices,
        is_active=True,
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)
    audit(db, current_user.id, action="license_issue", resource="license", resource_id=lic.id, request=request)
    return lic

# Ativar/Desativar licença
@app.post("/licenses/{license_id}/deactivate", response_model=LicenseResponse)
def deactivate_license(license_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), request: Request = None):
    lic = db.query(License).filter(License.id == license_id, License.user_id == current_user.id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    if not lic.is_active:
        raise HTTPException(status_code=400, detail="License already inactive")
    lic.is_active = False
    db.query(Device).filter(Device.license_id == lic.id).update({Device.is_active: False})
    db.commit()
    db.refresh(lic)
    audit(db, current_user.id, action="license_deactivate", resource="license", resource_id=lic.id, request=request)
    return lic

@app.post("/licenses/{license_id}/activate", response_model=LicenseResponse)
def activate_license(license_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), request: Request = None):
    lic = db.query(License).filter(License.id == license_id, License.user_id == current_user.id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    if lic.is_active:
        raise HTTPException(status_code=400, detail="License already active")
    lic.is_active = True
    db.commit()
    db.refresh(lic)
    audit(db, current_user.id, action="license_activate", resource="license", resource_id=lic.id, request=request)
    return lic

@app.get("/licenses/me", response_model=List[LicenseResponse])
def list_licenses(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    licenses = db.query(License).filter(License.user_id == current_user.id).all()
    return licenses

@app.post("/devices/bind", response_model=DeviceResponse)
def bind_device(payload: DeviceCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), request: Request = None):
    lic = db.query(License).filter(License.id == payload.license_id, License.user_id == current_user.id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    if not lic.is_active:
        raise HTTPException(status_code=400, detail="License inactive")
    current_count = db.query(Device).filter(Device.license_id == lic.id, Device.is_active == True).count()
    if current_count >= lic.max_devices:
        raise HTTPException(status_code=400, detail="Max devices reached for this license")
    existing = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device already bound")
    dev = Device(
        device_id=payload.device_id,
        device_name=payload.device_name,
        user_id=current_user.id,
        license_id=lic.id,
        is_active=True,
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    audit(db, current_user.id, action="device_bind", resource="device", resource_id=dev.id, request=request)
    return dev

# Desvincular dispositivo (desativar)
from .schemas import DeviceUnbind, DeviceHeartbeat
from datetime import datetime

@app.post("/devices/unbind", response_model=DeviceResponse)
def unbind_device(payload: DeviceUnbind, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), request: Request = None):
    dev = db.query(Device).filter(Device.id == payload.id, Device.user_id == current_user.id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    if not dev.is_active:
        raise HTTPException(status_code=400, detail="Device already inactive")
    dev.is_active = False
    db.commit()
    db.refresh(dev)
    audit(db, current_user.id, action="device_unbind", resource="device", resource_id=dev.id, request=request)
    return dev

@app.post("/devices/heartbeat", response_model=DeviceResponse)
def device_heartbeat(payload: DeviceHeartbeat, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db), request: Request = None):
    dev = db.query(Device).filter(Device.device_id == payload.device_id, Device.user_id == current_user.id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    dev.last_seen = datetime.utcnow()
    db.commit()
    db.refresh(dev)
    audit(db, current_user.id, action="device_heartbeat", resource="device", resource_id=dev.id, request=request)
    return dev

@app.get("/devices/me", response_model=List[DeviceResponse])
def list_devices(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    devices = db.query(Device).filter(Device.user_id == current_user.id).all()
    return devices

# Parser simples de M3U (EXTM3U/EXTINF)
def parse_m3u(content: str):
    channels = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF'):
            # Extrair atributos
            attrs = {}
            m = re.findall(r'(\w[\w-]*)="([^"]*)"', line)
            for k, v in m:
                attrs[k] = v
            # Nome após vírgula
            name_part = line.split(',', 1)
            name = name_part[1].strip() if len(name_part) > 1 else 'Unknown'
            # Próxima linha deve ser URL
            if i + 1 < len(lines):
                url = lines[i+1].strip()
                channels.append({
                    'name': name,
                    'url': url,
                    'logo_url': attrs.get('tvg-logo'),
                    'category': attrs.get('group-title'),
                    'country': attrs.get('tvg-country'),
                    'language': attrs.get('tvg-language'),
                })
                i += 2
                continue
        i += 1
    return channels

# Ingestão de playlist M3U
@app.post('/catalog/m3u/ingest', response_model=List[ChannelResponse])
def ingest_m3u(name: str, url: str | None = None, content: str | None = None, current_user: User = Depends(require_active_license), db: Session = Depends(get_db), request: Request = None):
    if not url and not content:
        raise HTTPException(status_code=400, detail='Provide url or content')
    data = None
    if url:
        if not url.startswith('http://') and not url.startswith('https://'):
            raise HTTPException(status_code=400, detail='Only http/https URLs are allowed')
        try:
            origin = urllib.parse.urlsplit(url)
            referer = f"{origin.scheme}://{origin.netloc}"
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36',
                    'Accept': 'text/plain,application/vnd.apple.mpegurl,application/x-mpegURL,*/*;q=0.8',
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Connection': 'keep-alive',
                    'Referer': referer,
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                enc = (resp.headers.get('Content-Encoding') or '').lower()
                if 'gzip' in enc:
                    data_bytes = gzip.decompress(raw)
                elif 'deflate' in enc:
                    data_bytes = zlib.decompress(raw)
                else:
                    data_bytes = raw
                charset = 'utf-8'
                ct = resp.headers.get('Content-Type') or ''
                m = re.search(r'charset=([\w-]+)', ct, re.I)
                if m:
                    charset = m.group(1)
                data = data_bytes.decode(charset, errors='replace')
        except urllib.error.HTTPError as e:
            raise HTTPException(status_code=e.code or 400, detail=f'Failed to download M3U: {e.reason}')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f'Failed to download M3U: {str(e)}')
    else:
        data = content
    if not data or '#EXTM3U' not in data:
        raise HTTPException(status_code=400, detail='Invalid M3U content')
    parsed = parse_m3u(data)
    # Criar/atualizar playlist (guardar conteúdo quando inserido manualmente)
    content_to_store = data if (not url and content) else None
    created: List[Channel] = []
    try:
        playlist = M3UPlaylist(
            name=name,
            url=url,
            content=content_to_store,
            channels_count=len(parsed),
            last_updated=datetime.utcnow(),
            is_active=True,
            user_id=current_user.id,
        )
        db.add(playlist)
        db.flush()
        # Inserir canais (simples: cria novos)
        urls = {ch.get('url') for ch in parsed if ch.get('url')}
        existing_by_url = {}
        if urls:
            existing_channels = (
                db.query(Channel)
                .filter(Channel.user_id == current_user.id, Channel.url.in_(urls))
                .all()
            )
            existing_by_url = {ch.url: ch for ch in existing_channels}
        for ch in parsed:
            ch_url = ch.get('url')
            if not ch_url:
                continue
            existing = existing_by_url.get(ch_url)
            if existing:
                existing.name = ch['name']
                existing.logo_url = ch.get('logo_url')
                existing.category = ch.get('category')
                existing.country = ch.get('country')
                existing.language = ch.get('language')
                existing.is_active = True
                existing.playlist_id = playlist.id
                existing.updated_at = datetime.utcnow()
                created.append(existing)
            else:
                channel = Channel(
                    name=ch['name'],
                    url=ch_url,
                    logo_url=ch.get('logo_url'),
                    category=ch.get('category'),
                    country=ch.get('country'),
                    language=ch.get('language'),
                    is_active=True,
                    user_id=current_user.id,
                    playlist_id=playlist.id,
                )
                db.add(channel)
                created.append(channel)

        playlist.channels_count = len(created)
        db.flush()
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(playlist)
    for channel in created:
        db.refresh(channel)
    audit(db, current_user.id, action='m3u_ingest', resource='playlist', resource_id=playlist.id, request=request)
    return created

# Listar canais
@app.get('/catalog/channels', response_model=List[ChannelResponse])
def list_channels(playlist_id: Optional[int] = None, current_user: User = Depends(require_active_license), db: Session = Depends(get_db)):
    query = db.query(Channel).filter(Channel.user_id == current_user.id, Channel.is_active == True)
    if playlist_id is not None:
        query = query.filter(Channel.playlist_id == playlist_id)
    items = query.order_by(Channel.created_at.asc()).all()
    return items

# Listar playlists M3U
@app.get('/catalog/playlists', response_model=List[M3UPlaylistResponse])
def list_playlists(current_user: User = Depends(require_active_license), db: Session = Depends(get_db)):
    items = (
        db.query(M3UPlaylist)
        .filter(M3UPlaylist.user_id == current_user.id)
        .order_by(M3UPlaylist.created_at.desc())
        .all()
    )
    return items

# Atualizar playlist (nome/url/ativo)
@app.patch('/catalog/playlists/{playlist_id}', response_model=M3UPlaylistResponse)
def update_playlist(playlist_id: int, payload: M3UPlaylistUpdate, current_user: User = Depends(require_active_license), db: Session = Depends(get_db), request: Request = None):
    pl = db.query(M3UPlaylist).filter(M3UPlaylist.id == playlist_id).first()
    if not pl:
        raise HTTPException(status_code=404, detail='Playlist not found')
    if payload.name is not None:
        pl.name = payload.name
    if payload.url is not None:
        pl.url = payload.url
    if payload.is_active is not None:
        pl.is_active = payload.is_active
    pl.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(pl)
    audit(db, current_user.id, action='playlist_update', resource='playlist', resource_id=pl.id, request=request)
    return pl

# Deletar playlist
@app.delete('/catalog/playlists/{playlist_id}')
def delete_playlist(playlist_id: int, current_user: User = Depends(require_active_license), db: Session = Depends(get_db), request: Request = None):
    pl = db.query(M3UPlaylist).filter(M3UPlaylist.id == playlist_id).first()
    if not pl:
        raise HTTPException(status_code=404, detail='Playlist not found')
    db.delete(pl)
    db.commit()
    audit(db, current_user.id, action='playlist_delete', resource='playlist', resource_id=playlist_id, request=request)
    return { 'status': 'deleted', 'id': playlist_id }

# Autenticação flexível: aceita Authorization Bearer ou ?token=...
async def current_user_from_request(db: Session = Depends(get_db), request: Request = None):
    token = None
    if request:
        auth = request.headers.get('authorization') or request.headers.get('Authorization')
        if auth and auth.lower().startswith('bearer '):
            token = auth.split(' ', 1)[1].strip()
        if not token:
            token = request.query_params.get('token')
    if not token:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

# Requer licença ativa; auto-vincula dispositivo se não estiver vinculado
async def require_active_license(current_user: User = Depends(current_user_from_request), db: Session = Depends(get_db), request: Request = None):
    # Verifica se há licença ativa
    lic = db.query(License).filter(License.user_id == current_user.id, License.is_active == True).order_by(License.id).first()
    if not lic:
        raise HTTPException(status_code=403, detail="No active license")

    # Obtém device_id via cabeçalho ou query param
    device_id = None
    device_name = None
    if request:
        device_id = request.headers.get('X-Device-ID') or request.query_params.get('device_id')
        device_name = request.headers.get('User-Agent')

    if not device_id:
        raise HTTPException(status_code=403, detail="Device not provided")

    # Busca dispositivo
    dev = db.query(Device).filter(Device.device_id == device_id, Device.user_id == current_user.id).first()

    # Se não existir ou estiver inativo, tenta auto-vincular ao primeiro license ativo, respeitando limite
    if not dev or not dev.is_active:
        current_count = db.query(Device).filter(Device.license_id == lic.id, Device.is_active == True).count()
        if current_count >= lic.max_devices:
            raise HTTPException(status_code=403, detail="Max devices reached for this license")
        if not dev:
            dev = Device(
                device_id=device_id,
                device_name=device_name,
                user_id=current_user.id,
                license_id=lic.id,
                is_active=True,
                last_seen=datetime.utcnow(),
            )
            db.add(dev)
        else:
            dev.license_id = lic.id
            dev.is_active = True
            dev.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(dev)
    else:
        # Atualiza last_seen para dispositivos já ativos
        dev.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(dev)

    return current_user

# Servir frontend via backend para mesma origem
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

# Proxy de stream para contornar CORS e normalizar URIs
@app.get('/stream/m3u8')
def stream_proxy_m3u8(url: str, current_user: User = Depends(require_active_license), request: Request = None):
    if not url.startswith('http://') and not url.startswith('https://'):
        raise HTTPException(status_code=400, detail='Only http/https URLs are allowed')
    try:
        origin = urllib.parse.urlsplit(url)
        referer = f"{origin.scheme}://{origin.netloc}"
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36',
                'Accept': 'application/vnd.apple.mpegurl,application/x-mpegURL,text/plain,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Connection': 'keep-alive',
                'Referer': referer,
                'Origin': referer,
            },
        )
        key = origin.netloc
        jar = get_cookie_jar_for_origin(key)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        with opener.open(req, timeout=30) as resp:
            raw = resp.read()
            enc = (resp.headers.get('Content-Encoding') or '').lower()
            if 'gzip' in enc:
                data_bytes = gzip.decompress(raw)
            elif 'deflate' in enc:
                data_bytes = zlib.decompress(raw)
            else:
                data_bytes = raw
            charset = 'utf-8'
            ct = resp.headers.get('Content-Type') or ''
            m = re.search(r'charset=([\w-]+)', ct, re.I)
            if m:
                charset = m.group(1)
            content = data_bytes.decode(charset, errors='replace')
    except urllib.error.HTTPError as e:
        body = None
        try:
            body_bytes = e.read()
            body = body_bytes.decode('utf-8', errors='ignore') if body_bytes else None
        except Exception:
            body = None
        snippet = (body[:300] if body else "")
        logger.error(f"Upstream m3u8 HTTPError {e.code} for {url}: {e.reason}; body={snippet}")
        raise HTTPException(status_code=e.code or 400, detail=f"Failed to load m3u8: {e.reason}; body={snippet}")
    except Exception as e:
        logger.exception(f"Upstream m3u8 error for {url}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to load m3u8: {str(e)}")
    out_lines = []
    for line in content.splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            out_lines.append(line)
            continue
        abs_uri = s
        if not s.lower().startswith('http'):
            try:
                base = urllib.parse.urlsplit(url)
                base_root = f"{base.scheme}://{base.netloc}"
                if s.startswith('/'):
                    abs_uri = f"{base_root}{s}"
                else:
                    base_dir = base.path.rsplit('/', 1)[0] if '/' in base.path else ''
                    abs_uri = f"{base_root}{('/' + base_dir) if base_dir else ''}/{s}"
            except Exception:
                abs_uri = s
        token = None
        device_id = None
        if request:
            auth = request.headers.get('authorization') or request.headers.get('Authorization')
            if auth and auth.lower().startswith('bearer '):
                token = auth.split(' ', 1)[1].strip()
            if not token:
                token = request.query_params.get('token')
            device_id = request.headers.get('X-Device-ID') or request.query_params.get('device_id')
        qp = urllib.parse.urlencode({k:v for k,v in [('url', abs_uri), ('token', token), ('device_id', device_id)] if v})
        proxied = f"/stream/segment?{qp}"
        out_lines.append(proxied)
    result = '\n'.join(out_lines)
    return Response(result, media_type='application/vnd.apple.mpegurl')

@app.get('/stream/segment')
def stream_proxy_segment(url: str, current_user: User = Depends(require_active_license)):
    if not url.startswith('http://') and not url.startswith('https://'):
        raise HTTPException(status_code=400, detail='Only http/https URLs are allowed')
    try:
        origin = urllib.parse.urlsplit(url)
        referer = f"{origin.scheme}://{origin.netloc}"
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Connection': 'keep-alive',
                'Referer': referer,
                'Origin': referer,
            },
        )
        key = origin.netloc
        jar = get_cookie_jar_for_origin(key)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        with opener.open(req, timeout=30) as resp:
            raw = resp.read()
            enc = (resp.headers.get('Content-Encoding') or '').lower()
            if 'gzip' in enc:
                data_bytes = gzip.decompress(raw)
            elif 'deflate' in enc:
                data_bytes = zlib.decompress(raw)
            else:
                data_bytes = raw
            mime = resp.headers.get('Content-Type') or 'application/octet-stream'
            return Response(data_bytes, media_type=mime)
    except urllib.error.HTTPError as e:
        body = None
        try:
            body_bytes = e.read()
            body = body_bytes.decode('utf-8', errors='ignore') if body_bytes else None
        except Exception:
            body = None
        snippet = (body[:300] if body else "")
        logger.error(f"Upstream segment HTTPError {e.code} for {url}: {e.reason}; body={snippet}")
        raise HTTPException(status_code=e.code or 400, detail=f"Failed to load segment: {e.reason}; body={snippet}")
    except Exception as e:
        logger.exception(f"Upstream segment error for {url}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to load segment: {str(e)}")
