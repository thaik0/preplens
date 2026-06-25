"""Command-line entry point for the PrepLens local ingestion prototype."""

import argparse
import sys

from src.db import get_all_chunks, get_connection, initialize_database
from src.evaluation.retrieval_eval import METHODS, evaluate_retrieval
from src.generation.answer import DEFAULT_ANSWER_MODEL, generate_grounded_answer
from src.ingest.ingest import ingest_folder
from src.logging.interactive_feedback import collect_source_feedback
from src.logging.query_log import (
    FEEDBACK_TYPES,
    add_feedback,
    get_feedback_summary,
    get_query_details,
    get_recent_queries,
    log_ask_run,
)
from src.retrieval.embeddings import (
    EMBEDDING_MODEL,
    embed_stored_chunks,
    embed_stored_queries,
    semantic_search,
    similar_queries,
)
from src.retrieval.feedback_aware import feedback_search as feedback_aware_search
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


def embed_queries(model: str) -> int:
    """Generate and store missing semantic embeddings for logged queries."""
    result = embed_stored_queries(model)
    print(
        f"Created {result['created_count']} query embeddings and skipped "
        f"{result['skipped_count']} existing query embeddings."
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


def run_similar_queries(query: str, model: str) -> int:
    """Print logged queries closest in meaning to a new query."""
    results = similar_queries(query, model=model)
    if not results:
        print("No query embeddings found. Run: python3 main.py embed-queries")
        return 0

    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. Query {result['query_id']} | cosine similarity "
            f"{float(result['score']):.4f} | {result['created_at']}"
        )
        print(f"   {build_preview(str(result['query_text']))}")
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


def run_feedback_search(
    query: str,
    top_k: int,
    candidate_k: int,
    alpha: float,
    similarity_threshold: float,
    gamma: float,
) -> int:
    """Print hybrid results reranked by feedback from similar past queries."""
    report = feedback_aware_search(
        query,
        top_k=top_k,
        candidate_k=candidate_k,
        alpha=alpha,
        similarity_threshold=similarity_threshold,
        gamma=gamma,
    )
    results = report["results"]
    diagnostics = report["diagnostics"]
    if not isinstance(results, list) or not isinstance(diagnostics, dict):
        raise RuntimeError("Feedback search returned an invalid report.")

    if not diagnostics["used_feedback"]:
        print("No similar feedback found; results fall back to hybrid ranking.")
        print()

    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. Chunk {result['chunk_id']} | {result['filename']} | "
            f"chunk {result['chunk_index']}"
        )
        print(f"   hybrid score: {float(result['hybrid_score']):.4f}")
        print(f"   feedback score: {float(result['feedback_score']):.4f}")
        print(f"   final score: {float(result['final_score']):.4f}")
        print(f"   {build_preview(str(result['text']))}")
        print()

    print("Diagnostics:")
    print(f"  Past query embeddings checked: {diagnostics['checked_query_embeddings']}")
    print(f"  Similar queries above threshold: {diagnostics['similar_query_count']}")
    print(f"  Feedback labels used: {diagnostics['feedback_labels_used']}")
    print("  Top similar queries:")
    top_similar_queries = diagnostics["top_similar_queries"]
    if not top_similar_queries:
        print("    none")
    else:
        for similar_query in top_similar_queries:
            print(
                f"    Query {similar_query['query_id']} | similarity "
                f"{float(similar_query['similarity']):.4f}"
            )
            print(f"      {build_preview(str(similar_query['query_text']), 120)}")

    return 0


def ask(
    question: str, top_k: int, alpha: float, model: str, collect_feedback: bool = False
) -> int:
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

    if collect_feedback:
        # The ask run is saved first, then feedback reuses the same validation
        # rules as the standalone feedback command for the retrieved chunks.
        _, logged_results = get_query_details(query_id)
        collect_source_feedback(query_id, logged_results, build_preview)

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
        feedback = str(result["feedback"]) or "none"
        print(
            f"{result['rank']}. Chunk {result['chunk_id']} | "
            f"{result['filename']} | chunk {result['chunk_index']} | "
            f"hybrid score {float(result['hybrid_score']):.4f} | cited: {cited} | "
            f"feedback: {feedback}"
        )
        print(f"   {build_preview(str(result['text']))}")

    return 0


def feedback(
    query_id: int, chunk_id: int, feedback_type: str, comment: str | None
) -> int:
    """Save one feedback label for a chunk from a past ask retrieval."""
    feedback_id = add_feedback(query_id, chunk_id, feedback_type, comment)
    print(
        f"Saved feedback ID: {feedback_id} | query {query_id} | "
        f"chunk {chunk_id} | {feedback_type}"
    )
    return 0


def feedback_summary() -> int:
    """Print aggregate feedback counts."""
    summary = get_feedback_summary()
    print(f"Total feedback entries: {summary['total_feedback']}")
    print(f"Helpful: {summary['helpful_count']}")
    print(f"Not helpful: {summary['not_helpful_count']}")
    print(f"Wrong source: {summary['wrong_source_count']}")
    return 0


def eval_retrieval(evaluation_path: str, alpha: float, top_k: int) -> int:
    """Print aggregate metrics for all retrieval methods on labeled questions."""
    report = evaluate_retrieval(evaluation_path, alpha=alpha, top_k=top_k)
    print(f"Evaluation questions: {report['question_count']}")
    print(f"Alpha: {alpha}")
    print(f"Retrieval depth: {top_k}")

    for method in METHODS:
        metrics = report[method]
        if not isinstance(metrics, dict):
            continue
        print()
        print(method)
        print(f"  top_1_accuracy: {float(metrics['top_1_accuracy']):.3f}")
        print(f"  top_3_recall: {float(metrics['top_3_recall']):.3f}")
        print(f"  top_5_recall: {float(metrics['top_5_recall']):.3f}")
        print(
            f"  mean_reciprocal_rank: "
            f"{float(metrics['mean_reciprocal_rank']):.3f}"
        )

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

    embed_queries_parser = subparsers.add_parser(
        "embed-queries",
        help="Generate embeddings for logged queries missing the selected model.",
    )
    embed_queries_parser.add_argument(
        "--model",
        default=EMBEDDING_MODEL,
        help=f"Embedding model to use (default: {EMBEDDING_MODEL}).",
    )

    semantic_search_parser = subparsers.add_parser(
        "semantic-search", help="Find the top matching chunks by meaning."
    )
    semantic_search_parser.add_argument(
        "query", help='Question to search for, e.g. "how do I find a loop?"'
    )

    similar_queries_parser = subparsers.add_parser(
        "similar-queries", help="Find logged queries with similar meaning."
    )
    similar_queries_parser.add_argument(
        "query", help='Question to compare, e.g. "how do I find a loop?"'
    )
    similar_queries_parser.add_argument(
        "--model",
        default=EMBEDDING_MODEL,
        help=f"Embedding model to use (default: {EMBEDDING_MODEL}).",
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

    feedback_search_parser = subparsers.add_parser(
        "feedback-search",
        help="Rerank hybrid retrieval with feedback from similar past queries.",
    )
    feedback_search_parser.add_argument(
        "query", help='Question to search for, e.g. "how do I find a loop?"'
    )
    feedback_search_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of final chunks to return (default: 5).",
    )
    feedback_search_parser.add_argument(
        "--candidate-k",
        type=int,
        default=20,
        help="Hybrid candidates to rerank before final output (default: 20).",
    )
    feedback_search_parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Keyword weight for hybrid candidate generation (default: 0.5).",
    )
    feedback_search_parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.65,
        help="Minimum past-query similarity needed to use feedback (default: 0.65).",
    )
    feedback_search_parser.add_argument(
        "--gamma",
        type=float,
        default=0.20,
        help="Weight applied to the feedback score (default: 0.20).",
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
    ask_parser.add_argument(
        "--feedback",
        action="store_true",
        help="Prompt for feedback on each retrieved source after the answer is saved.",
    )

    subparsers.add_parser("history", help="List recent saved ask queries.")

    show_query_parser = subparsers.add_parser(
        "show-query", help="Inspect one saved ask query and its sources."
    )
    show_query_parser.add_argument("query_id", type=int, help="Saved query id to inspect.")

    feedback_parser = subparsers.add_parser(
        "feedback", help="Save feedback for a chunk retrieved by a past ask run."
    )
    feedback_parser.add_argument("query_id", type=int, help="Saved query id.")
    feedback_parser.add_argument("chunk_id", type=int, help="Retrieved chunk id.")
    feedback_parser.add_argument(
        "feedback_type", choices=sorted(FEEDBACK_TYPES), help="Feedback label."
    )
    feedback_parser.add_argument("--comment", help="Optional explanation for the label.")

    subparsers.add_parser(
        "feedback-summary", help="Show aggregate feedback counts."
    )

    eval_parser = subparsers.add_parser(
        "eval-retrieval", help="Compare retrieval methods on labeled questions."
    )
    eval_parser.add_argument("evaluation_path", help="Path to an evaluation JSON file.")
    eval_parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Keyword weight for hybrid retrieval (default: 0.5).",
    )
    eval_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Results to retrieve per method; must be at least 5 (default: 5).",
    )

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

        if args.command == "embed-queries":
            return embed_queries(args.model)

        if args.command == "semantic-search":
            return run_semantic_search(args.query)

        if args.command == "similar-queries":
            return run_similar_queries(args.query, args.model)

        if args.command == "hybrid-search":
            return run_hybrid_search(args.query, args.alpha)

        if args.command == "feedback-search":
            return run_feedback_search(
                args.query,
                args.top_k,
                args.candidate_k,
                args.alpha,
                args.similarity_threshold,
                args.gamma,
            )

        if args.command == "ask":
            return ask(
                args.question,
                args.top_k,
                args.alpha,
                args.model,
                args.feedback,
            )

        if args.command == "history":
            return history()

        if args.command == "show-query":
            return show_query(args.query_id)

        if args.command == "feedback":
            return feedback(
                args.query_id, args.chunk_id, args.feedback_type, args.comment
            )

        if args.command == "feedback-summary":
            return feedback_summary()

        if args.command == "eval-retrieval":
            return eval_retrieval(args.evaluation_path, args.alpha, args.top_k)

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
