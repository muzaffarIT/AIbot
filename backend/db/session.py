from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings


def _build_engine_kwargs() -> dict:
    kwargs = {
        "echo": False,
        "future": True,
        "pool_pre_ping": True,
    }

    if settings.postgres_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    return kwargs


engine = create_engine(settings.postgres_url, **_build_engine_kwargs())

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)
