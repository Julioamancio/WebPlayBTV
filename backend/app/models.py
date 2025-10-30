from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    username: str = Field(primary_key=True)
    full_name: Optional[str] = None


class Device(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fingerprint: str = Field(index=True)
    name: Optional[str] = None
    platform: Optional[str] = None
    owner_username: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class License(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_username: str = Field(index=True)
    status: str = Field(default="active")
    # Plano opcional da licença (ex.: bronze/silver/gold); quando presente,
    # pode definir limites específicos por plano.
    plan: Optional[str] = Field(default=None, index=True)
    # ID externo da licença/assinatura (ex.: subscription.id do Stripe)
    external_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    actor_username: str = Field(index=True)
    action: str
    resource: str
    resource_id: Optional[int] = None
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Playlist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_username: str = Field(index=True)
    name: str
    # tipo da lista: m3u ou hls (texto livre para flexibilidade)
    type: str = Field(index=True)
    url: str
    epg_url: Optional[str] = None
    active: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

