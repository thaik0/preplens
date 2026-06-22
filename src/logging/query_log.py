"""SQLite persistence and inspection helpers for successful ask runs."""

import sqlite3

from src.db import get_connection, initialize_database
from src.generation.answer import get_cited_chunk_ids


def log_ask_run(
    query_text: str,
    alpha: float,
    top_k: int,
    model: str,
    answer_text: str,
    results: list[dict[str, int | str | float]],
) -> int:
    """Save one completed ask run and return its query id."""
    # Logging establishes an inspectable baseline before feedback is added, so
    # future feedback can be connected to the exact question and answer.
    cited_chunk_ids = get_cited_chunk_ids(answer_text)

    with get_connection() as conn:
        initialize_database(conn)
        query_cursor = conn.execute(
            """
            INSERT INTO queries (query_text, retrieval_method, alpha, top_k, model)
            VALUES (?, ?, ?, ?, ?)
            """,
            (query_text, "hybrid", alpha, top_k, model),
        )
        query_id = int(query_cursor.lastrowid)

        conn.execute(
            """
            INSERT INTO answers (query_id, answer_text)
            VALUES (?, ?)
            """,
            (query_id, answer_text),
        )

        # Store this retrieval snapshot per query because future embeddings or
        # scoring changes could rank the same chunks differently.
        # was_cited is separate from retrieval: every row was retrieved, while
        # this flag records the subset the model used in its answer.
        conn.executemany(
            """
            INSERT INTO retrieval_results (
                query_id, chunk_id, "rank", keyword_score,
                normalized_keyword_score, semantic_score,
                normalized_semantic_score, hybrid_score, was_cited
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    query_id,
                    int(result["chunk_id"]),
                    rank,
                    float(result["keyword_score"]),
                    float(result["normalized_keyword_score"]),
                    float(result["semantic_score"]),
                    float(result["normalized_semantic_score"]),
                    float(result["hybrid_score"]),
                    1 if int(result["chunk_id"]) in cited_chunk_ids else 0,
                )
                for rank, result in enumerate(results, start=1)
            ],
        )
        conn.commit()

    return query_id


def get_recent_queries(limit: int = 10) -> list[sqlite3.Row]:
    """Return recent query records for the history command."""
    if limit <= 0:
        raise ValueError("limit must be greater than 0.")

    with get_connection() as conn:
        initialize_database(conn)
        return conn.execute(
            """
            SELECT id, query_text, retrieval_method, model, created_at
            FROM queries
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def get_query_details(query_id: int) -> tuple[sqlite3.Row | None, list[sqlite3.Row]]:
    """Return one logged query and its persisted retrieval result rows."""
    with get_connection() as conn:
        initialize_database(conn)
        query = conn.execute(
            """
            SELECT q.id, q.query_text, q.retrieval_method, q.alpha, q.top_k,
                   q.model, q.created_at, a.answer_text
            FROM queries q
            LEFT JOIN answers a ON a.query_id = q.id
            WHERE q.id = ?
            """,
            (query_id,),
        ).fetchone()

        if query is None:
            return None, []

        results = conn.execute(
            """
            SELECT r."rank", r.chunk_id, r.hybrid_score, r.was_cited,
                   c.chunk_index, c.text, d.filename
            FROM retrieval_results r
            JOIN chunks c ON c.id = r.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE r.query_id = ?
            ORDER BY r."rank"
            """,
            (query_id,),
        ).fetchall()

    return query, results
