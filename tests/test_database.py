from pathlib import Path

import pytest

from sqlalchemy import inspect
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

import src.db as db
from src.config import DEFAULT_SQLITE_DB_PATH
from src.database.access import (
    document_exists_by_source_path,
    get_document_by_source_path,
    get_document_with_chunks,
    get_query_details,
    initialize_schema,
    insert_chunk_records,
    insert_document_record,
    list_chunk_embeddings,
    list_chunks_missing_embeddings,
    list_documents_with_chunk_counts,
    list_queries_missing_embeddings,
    list_query_embeddings,
    log_ask_run_record,
    save_chunk_embedding,
    save_query_embedding,
)
from src.database.engine import get_engine, normalize_database_url
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


def test_core_ingestion_inserts_document_and_chunks(isolated_db: Path) -> None:
    document_id = insert_document_record(
        "linked_lists.md",
        "notes/linked_lists.md",
        "md",
    )
    insert_chunk_records(
        document_id,
        [
            {
                "chunk_index": 0,
                "text": "Use slow and fast pointers.",
                "start_char": 0,
                "end_char": 27,
            }
        ],
    )

    documents = list_documents_with_chunk_counts()
    document = get_document_with_chunks(document_id)

    assert isolated_db.exists()
    assert documents == [
        {
            "id": document_id,
            "filename": "linked_lists.md",
            "file_type": "md",
            "filepath": "notes/linked_lists.md",
            "chunk_count": 1,
        }
    ]
    assert document is not None
    assert document["chunks"][0]["text"] == "Use slow and fast pointers."


def test_document_source_path_lookup_helpers(isolated_db: Path) -> None:
    document_id = insert_document_record("graphs.md", "notes/graphs.md", "md")

    document = get_document_by_source_path("notes/graphs.md")

    assert isolated_db.exists()
    assert document == {
        "id": document_id,
        "filename": "graphs.md",
        "file_type": "md",
        "filepath": "notes/graphs.md",
    }
    assert document_exists_by_source_path("notes/graphs.md") is True
    assert get_document_by_source_path("notes/missing.md") is None
    assert document_exists_by_source_path("notes/missing.md") is False


def test_core_ask_run_logging_round_trip(isolated_db: Path) -> None:
    document_id = insert_document_record("graphs.md", "notes/graphs.md", "md")
    insert_chunk_records(
        document_id,
        [
            {
                "chunk_index": 0,
                "text": "BFS explores level by level.",
                "start_char": 0,
                "end_char": 29,
            }
        ],
    )

    query_id = log_ask_run_record(
        "what does bfs do?",
        alpha=0.5,
        top_k=1,
        model="test-model",
        answer_text="BFS explores by levels. [chunk 1]",
        results=[
            {
                "chunk_id": 1,
                "keyword_score": 2.0,
                "normalized_keyword_score": 1.0,
                "semantic_score": 0.75,
                "normalized_semantic_score": 0.75,
                "hybrid_score": 0.875,
            }
        ],
    )

    query, results = get_query_details(query_id)

    assert isolated_db.exists()
    assert query is not None
    assert query["query_text"] == "what does bfs do?"
    assert query["answer_text"] == "BFS explores by levels. [chunk 1]"
    assert results[0]["chunk_id"] == 1
    assert results[0]["rank"] == 1
    assert results[0]["was_cited"] == 1


def test_core_embedding_save_load_round_trip(isolated_db: Path) -> None:
    document_id = insert_document_record("dp.md", "notes/dp.md", "md")
    insert_chunk_records(
        document_id,
        [
            {
                "chunk_index": 0,
                "text": "Memoization stores previous answers.",
                "start_char": 0,
                "end_char": 37,
            }
        ],
    )
    query_id = log_ask_run_record(
        "what is memoization?",
        alpha=0.5,
        top_k=1,
        model="test-model",
        answer_text="Memoization stores answers. [chunk 1]",
        results=[
            {
                "chunk_id": 1,
                "keyword_score": 1.0,
                "normalized_keyword_score": 1.0,
                "semantic_score": 1.0,
                "normalized_semantic_score": 1.0,
                "hybrid_score": 1.0,
            }
        ],
    )

    assert list_chunks_missing_embeddings("test-embedding-model") == [
        {"id": 1, "text": "Memoization stores previous answers."}
    ]
    assert list_queries_missing_embeddings("test-embedding-model") == [
        {"id": query_id, "query_text": "what is memoization?"}
    ]

    save_chunk_embedding(1, "test-embedding-model", "[0.1, 0.2]")
    save_query_embedding(query_id, "test-embedding-model", "[0.3, 0.4]")

    assert isolated_db.exists()
    assert list_chunks_missing_embeddings("test-embedding-model") == []
    assert list_queries_missing_embeddings("test-embedding-model") == []
    assert list_chunk_embeddings("test-embedding-model")[0]["embedding_json"] == (
        "[0.1, 0.2]"
    )
    assert list_query_embeddings("test-embedding-model")[0]["embedding_json"] == (
        "[0.3, 0.4]"
    )


def test_database_url_selects_postgres_engine(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://preplens:secret@localhost:5432/preplens_test",
    )

    engine = get_engine()

    assert engine.url.drivername == "postgresql+psycopg"
    assert engine.dialect.name == "postgresql"
    assert engine.url.database == "preplens_test"
    engine.dispose()


@pytest.mark.parametrize(
    ("configured_url", "expected_url"),
    [
        (
            "postgresql://preplens:secret@localhost/preplens",
            "postgresql+psycopg://preplens:***@localhost/preplens",
        ),
        (
            "postgres://preplens:secret@localhost/preplens",
            "postgresql+psycopg://preplens:***@localhost/preplens",
        ),
        (
            "postgresql+psycopg://preplens:secret@localhost/preplens",
            "postgresql+psycopg://preplens:***@localhost/preplens",
        ),
    ],
)
def test_database_url_postgres_formats_are_normalized(
    configured_url: str,
    expected_url: str,
) -> None:
    normalized_url = make_url(normalize_database_url(configured_url))

    assert normalized_url.render_as_string(hide_password=True) == expected_url


def test_database_url_schema_initialization_surfaces_clear_error(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://preplens:secret@localhost:5432/preplens_test",
    )

    def fail_create_all(engine) -> None:
        raise SQLAlchemyError("connection failed")

    monkeypatch.setattr(metadata, "create_all", fail_create_all)

    with pytest.raises(RuntimeError, match="Unable to initialize"):
        initialize_schema()
