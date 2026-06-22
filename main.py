"""Command-line entry point for the PrepLens local ingestion prototype."""

import argparse
import sys

from src.db import get_all_chunks, get_connection, initialize_database
from src.generation.answer import DEFAULT_ANSWER_MODEL, generate_grounded_answer
from src.ingest.ingest import ingest_folder
from src.logging.query_log import get_query_details, get_recent_queries, log_ask_run
from src.retrieval.embeddings import embed_stored_chunks, semantic_search
from src.retrieval.hybrid import hybrid_search
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


def embed_chunks() -> int:
    """Generate and store missing semantic embeddings for every chunk."""
    result = embed_stored_chunks()
    print(
        f"Created {result['created_count']} embeddings and skipped "
        f"{result['skipped_count']} existing embeddings."
    )
    return 0


def run_semantic_search(query: str) -> int:
    """Print the most semantically similar stored chunks for a query."""
    results = semantic_search(query)
    if not results:
        print("No chunk embeddings found. Run: python3 main.py embed-chunks")
        return 0

    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. Chunk {result['chunk_id']} | {result['filename']} | "
            f"chunk {result['chunk_index']} | cosine similarity "
            f"{float(result['score']):.4f}"
        )
        print(f"   {build_preview(str(result['text']))}")
        print()

    return 0


def run_hybrid_search(query: str, alpha: float) -> int:
    """Print the top chunks ranked by combined keyword and semantic scores."""
    results = hybrid_search(query, alpha=alpha)
    if not results:
        print("No chunks found. Run: python3 main.py ingest notes/")
        return 0

    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. Chunk {result['chunk_id']} | {result['filename']} | "
            f"chunk {result['chunk_index']}"
        )
        print(
            f"   keyword: raw {float(result['keyword_score']):.4f}, "
            f"normalized {float(result['normalized_keyword_score']):.4f}"
        )
        print(
            f"   semantic: raw {float(result['semantic_score']):.4f}, "
            f"normalized {float(result['normalized_semantic_score']):.4f}"
        )
        print(f"   hybrid: {float(result['hybrid_score']):.4f}")
        print(f"   {build_preview(str(result['text']))}")
        print()

    return 0


def ask(question: str, top_k: int, alpha: float, model: str) -> int:
    """Retrieve source chunks, then generate a citation-backed answer from them."""
    # Retrieval happens before generation so the model sees only relevant,
    # inspectable evidence rather than being asked to answer from memory.
    results = hybrid_search(question, alpha=alpha, limit=top_k)
    if not results:
        print("No chunks found. Run: python3 main.py ingest notes/")
        return 0

    answer = generate_grounded_answer(question, results, model=model)
    query_id = log_ask_run(question, alpha, top_k, model, answer, results)

    print(f"Question: {question}")
    print()
    print("Answer:")
    print(answer)
    print()
    print(f"Saved query ID: {query_id}")
    print()
    print("Sources used for retrieval:")

    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. Chunk {result['chunk_id']} | {result['filename']} | "
            f"chunk {result['chunk_index']} | hybrid score "
            f"{float(result['hybrid_score']):.4f}"
        )
        print(f"   {build_preview(str(result['text']))}")

    return 0


def history() -> int:
    """Print recently logged ask queries."""
    queries = get_recent_queries()
    if not queries:
        print("No saved queries found. Run: python3 main.py ask \"your question\"")
        return 0

    for query in queries:
        print(
            f"{query['id']}: {build_preview(str(query['query_text']), 100)} | "
            f"{query['model']} | {query['retrieval_method']} | "
            f"{query['created_at']}"
        )

    return 0


def show_query(query_id: int) -> int:
    """Print one saved question, its answer, and its retrieved chunk snapshot."""
    query, results = get_query_details(query_id)
    if query is None:
        print(f"No saved query found with id {query_id}.", file=sys.stderr)
        return 1

    print(f"Query ID: {query['id']}")
    print(f"Question: {query['query_text']}")
    print(
        f"Settings: {query['retrieval_method']} | alpha {query['alpha']} | "
        f"top_k {query['top_k']} | model {query['model']}"
    )
    print(f"Created: {query['created_at']}")
    print()
    print("Answer:")
    print(query["answer_text"])
    print()
    print("Retrieved chunks:")

    for result in results:
        cited = "yes" if result["was_cited"] else "no"
        print(
            f"{result['rank']}. Chunk {result['chunk_id']} | "
            f"{result['filename']} | chunk {result['chunk_index']} | "
            f"hybrid score {float(result['hybrid_score']):.4f} | cited: {cited}"
        )
        print(f"   {build_preview(str(result['text']))}")

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

    subparsers.add_parser(
        "embed-chunks", help="Generate embeddings for chunks missing the selected model."
    )

    semantic_search_parser = subparsers.add_parser(
        "semantic-search", help="Find the top matching chunks by meaning."
    )
    semantic_search_parser.add_argument(
        "query", help='Question to search for, e.g. "how do I find a loop?"'
    )

    hybrid_search_parser = subparsers.add_parser(
        "hybrid-search", help="Combine keyword matches with semantic similarity."
    )
    hybrid_search_parser.add_argument(
        "query", help='Question to search for, e.g. "how do I find a loop?"'
    )
    hybrid_search_parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Keyword weight from 0.0 to 1.0 (default: 0.5).",
    )

    ask_parser = subparsers.add_parser(
        "ask", help="Answer a question using retrieved source chunks."
    )
    ask_parser.add_argument("question", help="Question to answer from your notes.")
    ask_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of source chunks to retrieve (default: 5).",
    )
    ask_parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Keyword weight from 0.0 to 1.0 (default: 0.5).",
    )
    ask_parser.add_argument(
        "--model",
        default=DEFAULT_ANSWER_MODEL,
        help=f"OpenAI model for answer generation (default: {DEFAULT_ANSWER_MODEL}).",
    )

    subparsers.add_parser("history", help="List recent saved ask queries.")

    show_query_parser = subparsers.add_parser(
        "show-query", help="Inspect one saved ask query and its sources."
    )
    show_query_parser.add_argument("query_id", type=int, help="Saved query id to inspect.")

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

        if args.command == "embed-chunks":
            return embed_chunks()

        if args.command == "semantic-search":
            return run_semantic_search(args.query)

        if args.command == "hybrid-search":
            return run_hybrid_search(args.query, args.alpha)

        if args.command == "ask":
            return ask(args.question, args.top_k, args.alpha, args.model)

        if args.command == "history":
            return history()

        if args.command == "show-query":
            return show_query(args.query_id)

    except (FileNotFoundError, NotADirectoryError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
