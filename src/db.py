"""Legacy sqlite3 helpers for source documents and retrieval internals.

SQLAlchemy Core now owns schema creation and the newer access boundary. These
helpers remain for lower-level ingestion, embedding, and retrieval code until a
later cleanup can migrate those paths without changing behavior.
"""

from collections.abc import Iterator
from contextlib import contextmanager
import os
import sqlite3
from pathlib import Path

from src.config import (
    DEFAULT_SQLITE_DB_PATH,
    PREPLENS_DB_PATH_ENV,
    get_database_url,
    get_sqlite_db_path,
)
from src.database.engine import create_sqlite_engine
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
    conn: sqlite3.Connection, filename: str, filepath: str, file_type: str
) -> int:
    """Insert one document row and return its generated id."""
    cursor = conn.execute(
        """
        INSERT INTO documents (filename, filepath, file_type)
        VALUES (?, ?, ?)
        """,
        (filename, filepath, file_type),
    )
    return int(cursor.lastrowid)


def insert_chunks(
    conn: sqlite3.Connection, document_id: int, chunks: list[dict[str, int | str]]
) -> None:
    """Insert all chunks for a document."""
    conn.executemany(
        """
        INSERT INTO chunks (document_id, chunk_index, text, start_char, end_char)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                document_id,
                chunk["chunk_index"],
                chunk["text"],
                chunk["start_char"],
                chunk["end_char"],
            )
            for chunk in chunks
        ],
    )


def get_all_chunks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return every stored chunk with the filename needed for search results."""
    return conn.execute(
        """
        SELECT c.id, c.chunk_index, c.text, d.filename
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        ORDER BY c.id
        """
    ).fetchall()


def get_chunks_without_embeddings(
    conn: sqlite3.Connection, model: str
) -> list[sqlite3.Row]:
    """Return chunks that do not yet have an embedding for the given model."""
    return conn.execute(
        """
        SELECT c.id, c.text
        FROM chunks c
        LEFT JOIN chunk_embeddings e
            ON e.chunk_id = c.id AND e.model = ?
        WHERE e.id IS NULL
        ORDER BY c.id
        """,
        (model,),
    ).fetchall()


def count_chunks(conn: sqlite3.Connection) -> int:
    """Return the number of stored chunks."""
    row = conn.execute("SELECT COUNT(*) AS chunk_count FROM chunks").fetchone()
    return int(row["chunk_count"])


def insert_chunk_embedding(
    conn: sqlite3.Connection, chunk_id: int, model: str, embedding_json: str
) -> None:
    """Store one serialized embedding for a chunk and model."""
    conn.execute(
        """
        INSERT INTO chunk_embeddings (chunk_id, model, embedding_json)
        VALUES (?, ?, ?)
        """,
        (chunk_id, model, embedding_json),
    )


def get_chunk_embeddings(
    conn: sqlite3.Connection, model: str
) -> list[sqlite3.Row]:
    """Return stored embeddings together with the chunk metadata for display."""
    return conn.execute(
        """
        SELECT c.id AS chunk_id, c.chunk_index, c.text, d.filename,
               e.embedding_json
        FROM chunk_embeddings e
        JOIN chunks c ON c.id = e.chunk_id
        JOIN documents d ON d.id = c.document_id
        WHERE e.model = ?
        ORDER BY c.id
        """,
        (model,),
    ).fetchall()


def get_queries_without_embeddings(
    conn: sqlite3.Connection, model: str
) -> list[sqlite3.Row]:
    """Return logged queries that do not yet have an embedding for this model."""
    return conn.execute(
        """
        SELECT q.id, q.query_text
        FROM queries q
        LEFT JOIN query_embeddings e
            ON e.query_id = q.id AND e.model = ?
        WHERE e.id IS NULL
        ORDER BY q.id
        """,
        (model,),
    ).fetchall()


def count_queries(conn: sqlite3.Connection) -> int:
    """Return the number of logged ask queries."""
    row = conn.execute("SELECT COUNT(*) AS query_count FROM queries").fetchone()
    return int(row["query_count"])


def insert_query_embedding(
    conn: sqlite3.Connection, query_id: int, model: str, embedding_json: str
) -> None:
    """Store one serialized embedding for a logged query and model."""
    conn.execute(
        """
        INSERT INTO query_embeddings (query_id, model, embedding_json)
        VALUES (?, ?, ?)
        """,
        (query_id, model, embedding_json),
    )


def get_query_embeddings(
    conn: sqlite3.Connection, model: str
) -> list[sqlite3.Row]:
    """Return stored query embeddings with query metadata for similarity search."""
    return conn.execute(
        """
        SELECT q.id AS query_id, q.query_text, q.created_at, e.embedding_json
        FROM query_embeddings e
        JOIN queries q ON q.id = e.query_id
        WHERE e.model = ?
        ORDER BY q.id
        """,
        (model,),
    ).fetchall()


def get_feedback_for_queries(
    conn: sqlite3.Connection, query_ids: list[int]
) -> list[sqlite3.Row]:
    """Return feedback labels attached to the provided logged query IDs."""
    if not query_ids:
        return []

    placeholders = ", ".join("?" for _ in query_ids)
    return conn.execute(
        f"""
        SELECT query_id, chunk_id, feedback_type
        FROM feedback
        WHERE query_id IN ({placeholders})
        ORDER BY query_id, id
        """,
        query_ids,
    ).fetchall()
