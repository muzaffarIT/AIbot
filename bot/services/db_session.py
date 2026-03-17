from sqlalchemy.orm import Session

from backend.db.session import SessionLocal


def get_db_session() -> Session:
    return SessionLocal()