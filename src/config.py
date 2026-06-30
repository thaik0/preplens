"""Runtime configuration for PrepLens persistence.

DATABASE_URL enables external database mode, including Postgres. When it is not
set, PrepLens uses SQLite and PREPLENS_DB_PATH can override the local database
file path.
"""

import os
from pathlib import Path


DEFAULT_SQLITE_DB_PATH = Path("data") / "preplens.db"
PREPLENS_DB_PATH_ENV = "PREPLENS_DB_PATH"
DATABASE_URL_ENV = "DATABASE_URL"


def get_sqlite_db_path() -> Path:
    """Return the SQLite path used when DATABASE_URL is not configured."""
    configured_path = os.getenv(PREPLENS_DB_PATH_ENV)
    if configured_path:
        return Path(configured_path)
    return DEFAULT_SQLITE_DB_PATH


def get_database_url() -> str | None:
    """Return a configured external database URL, if one was supplied."""
    return os.getenv(DATABASE_URL_ENV)
