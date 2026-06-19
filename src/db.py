"""SQLite helpers for storing source documents and their text chunks."""

from collections.abc import Iterator
from contextlib import contextmanager
import sqlite3
from pathlib import Path


DB_PATH = Path("data") / "preplens.db"


@contextmanager
def get_connection(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection for a block of work, then close it."""
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
