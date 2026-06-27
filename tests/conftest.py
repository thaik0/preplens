from pathlib import Path

import pytest

import src.db as db


@pytest.fixture
def isolated_db(tmp_path: Path, monkeypatch) -> Path:
    """Point services at a fresh SQLite file instead of local data/preplens.db."""
    test_db_path = tmp_path / "preplens-test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    return test_db_path
