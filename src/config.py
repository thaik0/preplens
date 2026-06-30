"""Runtime configuration for PrepLens local persistence."""

import os
from pathlib import Path


DEFAULT_SQLITE_DB_PATH = Path("data") / "preplens.db"
PREPLENS_DB_PATH_ENV = "PREPLENS_DB_PATH"
DATABASE_URL_ENV = "DATABASE_URL"


def get_sqlite_db_path() -> Path:
    """Return the SQLite path used by the current process."""
    configured_path = os.getenv(PREPLENS_DB_PATH_ENV)
    if configured_path:
        return Path(configured_path)
    return DEFAULT_SQLITE_DB_PATH


def get_database_url() -> str | None:
    """Return a configured database URL, if one was supplied."""
    return os.getenv(DATABASE_URL_ENV)
