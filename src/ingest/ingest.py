"""Ingestion flow that reads notes, chunks them, and stores them in SQLite."""

from src.db import insert_chunks, insert_document
from src.database.access import document_exists_by_source_path
from src.ingest.chunk import chunk_text
from src.ingest.read_files import read_note_files


def ingest_folder(folder: str) -> dict[str, int | list[str]]:
    """Ingest all supported note files from a folder into the local database."""
    note_files = read_note_files(folder)

    document_count = 0
    chunk_count = 0
    skipped_files: list[str] = []

    for note_file in note_files:
        if document_exists_by_source_path(note_file["filepath"]):
            skipped_files.append(note_file["filepath"])
            continue

        chunks = chunk_text(note_file["text"])
        document_id = insert_document(
            None,
            filename=note_file["filename"],
            filepath=note_file["filepath"],
            file_type=note_file["file_type"],
        )
        insert_chunks(None, document_id, chunks)

        document_count += 1
        chunk_count += len(chunks)

    return {
        "document_count": document_count,
        "skipped_count": len(skipped_files),
        "chunk_count": chunk_count,
        "skipped_files": skipped_files,
    }
