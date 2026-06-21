"""Command-line entry point for the PrepLens local ingestion prototype."""

import argparse
import sys

from src.db import get_all_chunks, get_connection, initialize_database
from src.ingest.ingest import ingest_folder
from src.retrieval.keyword import score_chunks


def list_docs() -> int:
    """Print all documents currently stored in SQLite."""
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

    if not rows:
        print("No documents found. Run: python3 main.py ingest notes/")
        return 0

    for row in rows:
        print(
            f"{row['id']}: {row['filename']} "
            f"({row['file_type']}, {row['chunk_count']} chunks) - {row['filepath']}"
        )

    return 0


def show_chunks(document_id: int) -> int:
    """Print chunks for one document so their boundaries can be inspected."""
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
            print(f"No document found with id {document_id}.", file=sys.stderr)
            return 1

        chunks = conn.execute(
            """
            SELECT chunk_index, text, start_char, end_char
            FROM chunks
            WHERE document_id = ?
            ORDER BY chunk_index
            """,
            (document_id,),
        ).fetchall()

    print(f"Document {document['id']}: {document['filename']}")
    print(f"Path: {document['filepath']}")
    print()

    if not chunks:
        print("No chunks found for this document.")
        return 0

    for chunk in chunks:
        print(
            f"--- Chunk {chunk['chunk_index']} "
            f"[{chunk['start_char']}:{chunk['end_char']}] ---"
        )
        print(chunk["text"])
        print()

    return 0


def build_preview(text: str, max_length: int = 240) -> str:
    """Turn chunk text into a compact one-line preview for search output."""
    preview = " ".join(text.split())
    if len(preview) <= max_length:
        return preview
    return f"{preview[:max_length].rstrip()}..."


def search(query: str) -> int:
    """Rank stored chunks for a keyword query and print the top results."""
    with get_connection() as conn:
        initialize_database(conn)
        chunks = get_all_chunks(conn)

    if not chunks:
        print("No chunks found. Run: python3 main.py ingest notes/")
        return 0

    results = score_chunks(query, chunks)
    if not results:
        print(f'No matching chunks found for: "{query}"')
        return 0

    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. Chunk {result['chunk_id']} | {result['filename']} | "
            f"chunk {result['chunk_index']} | score {result['score']}"
        )
        print(f"   {build_preview(str(result['text']))}")
        print()

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser and its supported commands."""
    parser = argparse.ArgumentParser(
        description="PrepLens local CLI for reading notes into SQLite."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest", help="Read .md and .txt files from a folder into SQLite."
    )
    ingest_parser.add_argument("folder", help="Folder containing note files, e.g. notes/")

    subparsers.add_parser("list-docs", help="List ingested documents.")

    chunks_parser = subparsers.add_parser(
        "show-chunks", help="Print chunks for a stored document."
    )
    chunks_parser.add_argument("document_id", type=int, help="Document id to inspect.")

    search_parser = subparsers.add_parser(
        "search", help="Find the top matching chunks with keyword search."
    )
    search_parser.add_argument("query", help='Search terms, e.g. "fast slow pointer"')

    return parser


def main() -> int:
    """Dispatch CLI commands."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "ingest":
            result = ingest_folder(args.folder)
            print(
                f"Ingested {result['document_count']} documents "
                f"and {result['chunk_count']} chunks."
            )
            return 0

        if args.command == "list-docs":
            return list_docs()

        if args.command == "show-chunks":
            return show_chunks(args.document_id)

        if args.command == "search":
            return search(args.query)

    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
