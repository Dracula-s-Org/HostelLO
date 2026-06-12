from sqlmodel import SQLModel, Session, create_engine

from app.config import config


def _normalize(url: str) -> str:
    # Render/Heroku-style URLs use the deprecated postgres:// scheme
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = _normalize(config.DATABASE_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def init_db() -> None:
    # Import models so every table is registered on the shared metadata
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
