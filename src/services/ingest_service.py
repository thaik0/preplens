"""Reusable ingestion and document-inspection workflows."""

from typing import Any

from src.db import get_connection, initialize_database
from src.ingest.ingest import ingest_folder


def ingest_notes(folder: str) -> dict[str, int]:
    """Ingest supported note files through the existing ingestion module."""
    return ingest_folder(folder)


def list_documents() -> dict[str, Any]:
    """Return ingested documents with chunk counts."""
    with get_connection() as conn:
        initialize_database(conn)
        rows = conn.execute(
            """
            SELECT d.id, d.filename, d.file_type, d.filepath, COUNT(c.id) AS chunk_count
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            GROUP BY d.id
            ORDER BY d.id
            """
        ).fetchall()

    documents = [
        {
            "id": int(row["id"]),
            "filename": str(row["filename"]),
            "file_type": str(row["file_type"]),
            "filepath": str(row["filepath"]),
            "chunk_count": int(row["chunk_count"]),
        }
        for row in rows
    ]
    return {"documents": documents}


def get_document_chunks(document_id: int) -> dict[str, Any] | None:
    """Return one document and its chunks for inspection."""
    with get_connection() as conn:
        initialize_database(conn)
        document = conn.execute(
            """
            SELECT id, filename, filepath
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

        if document is None:
            return None

        rows = conn.execute(
            """
            SELECT chunk_index, text, start_char, end_char
            FROM chunks
            WHERE document_id = ?
            ORDER BY chunk_index
            """,
            (document_id,),
        ).fetchall()

    return {
        "document": {
            "id": int(document["id"]),
            "filename": str(document["filename"]),
            "filepath": str(document["filepath"]),
        },
        "chunks": [
            {
                "chunk_index": int(row["chunk_index"]),
                "text": str(row["text"]),
                "start_char": int(row["start_char"]),
                "end_char": int(row["end_char"]),
            }
            for row in rows
        ],
    }
