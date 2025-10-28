from typing import Iterator

from sqlmodel import SQLModel, Session, create_engine


sqlite_url = "sqlite:///webplay.db"
engine = create_engine(sqlite_url, echo=False)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

