from typing import Iterator

from sqlmodel import SQLModel, Session, create_engine
from app.config import os as _os  # reuse loaded dotenv context
from app.config import DATABASE_URL


db_url = DATABASE_URL or "sqlite:///webplay.db"
engine = create_engine(db_url, echo=False)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

