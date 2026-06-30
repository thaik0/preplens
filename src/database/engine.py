"""SQLAlchemy engine creation for PrepLens."""

from pathlib import Path

from sqlalchemy import Engine, create_engine

from src.config import get_database_url, get_sqlite_db_path


def normalize_database_url(database_url: str) -> str:
    """Return a SQLAlchemy URL using PrepLens' supported sync drivers."""
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


def create_sqlite_engine(db_path: Path | None = None) -> Engine:
    """Create a SQLAlchemy Core engine for the configured SQLite database."""
    sqlite_path = db_path if db_path is not None else get_sqlite_db_path()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{sqlite_path}", future=True)


def create_database_url_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy Core engine from DATABASE_URL."""
    return create_engine(normalize_database_url(database_url), future=True)


def get_engine() -> Engine:
    """Return the configured SQLAlchemy Core engine.

    DATABASE_URL enables external database mode. When it is unset, PrepLens uses
    SQLite at PREPLENS_DB_PATH or the default data/preplens.db path.
    """
    database_url = get_database_url()
    if database_url:
        return create_database_url_engine(database_url)
    return create_sqlite_engine()
