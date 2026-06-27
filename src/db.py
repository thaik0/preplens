"""SQLite helpers for storing source documents and their text chunks."""

from collections.abc import Iterator
from contextlib import contextmanager
import sqlite3
from pathlib import Path


DB_PATH = Path("data") / "preplens.db"


@contextmanager
def get_connection(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection for a block of work, then close it."""
    if db_path is None:
        db_path = DB_PATH

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def initialize_database(conn: sqlite3.Connection) -> None:
    """Create the required tables if they do not already exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            file_type TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            start_char INTEGER NOT NULL,
            end_char INTEGER NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents (id)
        )
        """
    )
    # Embeddings live separately so a chunk can later be embedded by more than
    # one model without duplicating the original source text.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunk_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id INTEGER NOT NULL,
            model TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chunk_id) REFERENCES chunks (id),
            UNIQUE (chunk_id, model)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            retrieval_method TEXT NOT NULL,
            alpha REAL NOT NULL,
            top_k INTEGER NOT NULL,
            model TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Query embeddings are stored separately from query text so future
    # feedback-aware retrieval can compare new questions with past questions
    # without changing the logged query records.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS query_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id INTEGER NOT NULL,
            model TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (query_id) REFERENCES queries (id),
            UNIQUE (query_id, model)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id INTEGER NOT NULL UNIQUE,
            answer_text TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (query_id) REFERENCES queries (id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS retrieval_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id INTEGER NOT NULL,
            chunk_id INTEGER NOT NULL,
            "rank" INTEGER NOT NULL,
            keyword_score REAL NOT NULL,
            normalized_keyword_score REAL NOT NULL,
            semantic_score REAL NOT NULL,
            normalized_semantic_score REAL NOT NULL,
            hybrid_score REAL NOT NULL,
            was_cited INTEGER NOT NULL CHECK (was_cited IN (0, 1)),
            FOREIGN KEY (query_id) REFERENCES queries (id),
            FOREIGN KEY (chunk_id) REFERENCES chunks (id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id INTEGER NOT NULL,
            chunk_id INTEGER NOT NULL,
            feedback_type TEXT NOT NULL CHECK (
                feedback_type IN ('helpful', 'not_helpful', 'wrong_source')
            ),
            comment TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (query_id) REFERENCES queries (id),
            FOREIGN KEY (chunk_id) REFERENCES chunks (id)
        )
        """
    )
    conn.commit()


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
