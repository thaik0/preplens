"""Reusable ingestion and document-inspection workflows."""

from typing import Any

from src.database.access import get_document_with_chunks, list_documents_with_chunk_counts
from src.ingest.ingest import ingest_folder


def ingest_notes(folder: str) -> dict[str, int | list[str]]:
    """Ingest supported note files through the existing ingestion module."""
    return ingest_folder(folder)


def list_documents() -> dict[str, Any]:
    """Return ingested documents with chunk counts."""
    documents = [
        {
            "id": int(row["id"]),
            "filename": str(row["filename"]),
            "file_type": str(row["file_type"]),
            "filepath": str(row["filepath"]),
            "chunk_count": int(row["chunk_count"]),
        }
        for row in list_documents_with_chunk_counts()
    ]
    return {"documents": documents}


def get_document_chunks(document_id: int) -> dict[str, Any] | None:
    """Return one document and its chunks for inspection."""
    report = get_document_with_chunks(document_id)
    if report is None:
        return None

    document = report["document"]
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
            for row in report["chunks"]
        ],
    }
