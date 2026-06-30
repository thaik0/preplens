"""Legacy sqlite3 compatibility helpers for PrepLens.

SQLAlchemy Core is now the preferred database access path. This module keeps
older imports working while remaining sqlite3 usage is reduced before Postgres.
"""

from collections.abc import Iterator
from contextlib import contextmanager
import os
import sqlite3
from pathlib import Path
from typing import Any

from src.config import (
    DEFAULT_SQLITE_DB_PATH,
    PREPLENS_DB_PATH_ENV,
    get_database_url,
    get_sqlite_db_path,
)
from src.database.engine import create_sqlite_engine
from src.database.access import (
    count_chunk_records,
    count_query_records,
    insert_chunk_records,
    insert_document_record,
    list_all_chunks,
    list_chunk_embeddings,
    list_chunks_missing_embeddings,
    list_feedback_for_queries,
    list_queries_missing_embeddings,
    list_query_embeddings,
    save_chunk_embedding,
    save_query_embedding,
)
from src.database.schema import metadata


DB_PATH = DEFAULT_SQLITE_DB_PATH


def _resolve_db_path(db_path: Path | None = None) -> Path:
    if db_path is not None:
        return db_path
    if os.getenv(PREPLENS_DB_PATH_ENV):
        return get_sqlite_db_path()
    return DB_PATH


@contextmanager
def get_connection(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection for a block of work, then close it."""
    db_path = _resolve_db_path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def initialize_database(conn: sqlite3.Connection) -> None:
    """Create the required tables via SQLAlchemy Core metadata."""
    if get_database_url():
        raise NotImplementedError(
            "DATABASE_URL/Postgres support is planned, but SQLite is the only "
            "implemented PrepLens database backend right now."
        )
    metadata.create_all(create_sqlite_engine(_resolve_db_path()))


def insert_document(
    conn: Any, filename: str, filepath: str, file_type: str
) -> int:
    """Insert one document row and return its generated id."""
    return insert_document_record(filename, filepath, file_type)


def insert_chunks(
    conn: Any, document_id: int, chunks: list[dict[str, int | str]]
) -> None:
    """Insert all chunks for a document."""
    insert_chunk_records(document_id, chunks)


def get_all_chunks(conn: Any) -> list[dict]:
    """Return every stored chunk with the filename needed for search results."""
    return list_all_chunks()


def get_chunks_without_embeddings(
    conn: Any, model: str
) -> list[dict]:
    """Return chunks that do not yet have an embedding for the given model."""
    return list_chunks_missing_embeddings(model)


def count_chunks(conn: Any) -> int:
    """Return the number of stored chunks."""
    return count_chunk_records()


def insert_chunk_embedding(
    conn: Any, chunk_id: int, model: str, embedding_json: str
) -> None:
    """Store one serialized embedding for a chunk and model."""
    save_chunk_embedding(chunk_id, model, embedding_json)


def get_chunk_embeddings(
    conn: Any, model: str
) -> list[dict]:
    """Return stored embeddings together with the chunk metadata for display."""
    return list_chunk_embeddings(model)


def get_queries_without_embeddings(
    conn: Any, model: str
) -> list[dict]:
    """Return logged queries that do not yet have an embedding for this model."""
    return list_queries_missing_embeddings(model)


def count_queries(conn: Any) -> int:
    """Return the number of logged ask queries."""
    return count_query_records()


def insert_query_embedding(
    conn: Any, query_id: int, model: str, embedding_json: str
) -> None:
    """Store one serialized embedding for a logged query and model."""
    save_query_embedding(query_id, model, embedding_json)


def get_query_embeddings(
    conn: Any, model: str
) -> list[dict]:
    """Return stored query embeddings with query metadata for similarity search."""
    return list_query_embeddings(model)


def get_feedback_for_queries(
    conn: Any, query_ids: list[int]
) -> list[dict]:
    """Return feedback labels attached to the provided logged query IDs."""
    return list_feedback_for_queries(query_ids)
