from typing import Optional
from datetime import datetime

from sqlmodel import Field, SQLModel


class UserAccount(SQLModel, table=True):
    username: str = Field(primary_key=True)
    full_name: Optional[str] = None
    password_hash: str
    stripe_customer_id: Optional[str] = Field(default=None, index=True)


class RevokedToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    jti: str = Field(index=True, unique=True)
    owner_username: Optional[str] = Field(default=None, index=True)
    expires_at: datetime

