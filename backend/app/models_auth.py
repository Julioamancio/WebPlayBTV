from typing import Optional

from sqlmodel import Field, SQLModel


class UserAccount(SQLModel, table=True):
    username: str = Field(primary_key=True)
    full_name: Optional[str] = None
    password_hash: str

