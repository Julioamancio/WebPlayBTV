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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

