"""Ingestion flow that reads notes, chunks them, and stores them in SQLite."""

from src.db import get_connection, initialize_database, insert_chunks, insert_document
from src.ingest.chunk import chunk_text
from src.ingest.read_files import read_note_files


def ingest_folder(folder: str) -> dict[str, int]:
    """Ingest all supported note files from a folder into the local database."""
    note_files = read_note_files(folder)

    document_count = 0
    chunk_count = 0

    with get_connection() as conn:
        initialize_database(conn)

        for note_file in note_files:
            chunks = chunk_text(note_file["text"])
            document_id = insert_document(
                conn,
                filename=note_file["filename"],
                filepath=note_file["filepath"],
                file_type=note_file["file_type"],
            )
            insert_chunks(conn, document_id, chunks)

            document_count += 1
            chunk_count += len(chunks)

        conn.commit()

    return {"document_count": document_count, "chunk_count": chunk_count}
