"""SQLAlchemy engine creation for PrepLens.

SQLAlchemy Core is the database access foundation. SQLite remains the only
implemented backend for now; DATABASE_URL/Postgres support is planned for a
later sprint.
"""

from pathlib import Path

from sqlalchemy import Engine, create_engine

from src.config import get_database_url, get_sqlite_db_path


def create_sqlite_engine(db_path: Path | None = None) -> Engine:
    """Create a SQLAlchemy Core engine for the configured SQLite database."""
    sqlite_path = db_path if db_path is not None else get_sqlite_db_path()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{sqlite_path}", future=True)


def get_engine() -> Engine:
    """Return the configured engine, intentionally limited to SQLite today."""
    if get_database_url():
        raise NotImplementedError(
            "DATABASE_URL/Postgres support is planned, but SQLite is the only "
            "implemented PrepLens database backend right now."
        )
    return create_sqlite_engine()
