from __future__ import annotations

from backend.database.session import Base, engine
import backend.models  # noqa: F401 - ensure all ORM models are registered on Base.metadata


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
