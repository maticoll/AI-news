import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


def get_engine(url: str | None = None):
    database_url = url or os.getenv("DATABASE_URL", "sqlite:///./ainews.db")
    return create_engine(database_url, connect_args={"check_same_thread": False})


def init_db(engine=None):
    """Create all tables. Pass engine for testing; uses default engine otherwise."""
    from backend import models  # noqa: F401 — registers models
    target = engine or get_engine()
    Base.metadata.create_all(bind=target)


def get_session_factory(engine=None):
    target = engine or get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=target)


def get_db(session_factory=None):
    """FastAPI dependency — yields a DB session."""
    factory = session_factory or get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
