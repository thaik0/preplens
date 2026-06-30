from pathlib import Path

import pytest

from sqlalchemy import inspect

import src.db as db
from src.config import DEFAULT_SQLITE_DB_PATH
from src.database.access import initialize_schema
from src.database.engine import get_engine
from src.database.schema import metadata


def test_engine_uses_default_sqlite_path_when_env_unset(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PREPLENS_DB_PATH", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    engine = get_engine()

    assert Path(str(engine.url.database)) == DEFAULT_SQLITE_DB_PATH
    assert DEFAULT_SQLITE_DB_PATH.parent.exists()


def test_engine_uses_preplens_db_path_when_set(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "custom" / "preplens-test.db"
    monkeypatch.setenv("PREPLENS_DB_PATH", str(db_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    engine = get_engine()

    assert Path(str(engine.url.database)) == db_path
    assert db_path.parent.exists()


def test_schema_initialization_creates_all_tables(
    tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "schema-test.db"
    monkeypatch.setenv("PREPLENS_DB_PATH", str(db_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    initialize_schema()
    table_names = set(inspect(get_engine()).get_table_names())

    assert table_names == set(metadata.tables)


def test_legacy_initialize_database_honors_db_path_override(
    tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "legacy-override.db"
    monkeypatch.delenv("PREPLENS_DB_PATH", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(db, "DB_PATH", db_path)

    with db.get_connection() as conn:
        db.initialize_database(conn)
        table_names = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert set(metadata.tables).issubset(table_names)
    assert db_path.exists()


def test_database_url_is_explicitly_not_implemented(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/preplens")

    with pytest.raises(NotImplementedError, match="Postgres support is planned"):
        get_engine()
