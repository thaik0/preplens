"""SQLite persistence and inspection helpers for successful ask runs."""

from src.database.access import (
    FEEDBACK_TYPES,
    add_feedback as add_feedback_record,
    get_feedback_summary as get_feedback_summary_record,
    get_query_details as get_query_details_record,
    list_recent_queries,
)
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


def get_recent_queries(limit: int = 10) -> list[dict]:
    """Return recent query records for the history command."""
    return list_recent_queries(limit=limit)


def get_query_details(query_id: int) -> tuple[dict | None, list[dict]]:
    """Return one logged query and its persisted retrieval result rows."""
    return get_query_details_record(query_id)


def add_feedback(
    query_id: int, chunk_id: int, feedback_type: str, comment: str | None = None
) -> int:
    """Save feedback for a chunk that was retrieved for the given query."""
    return add_feedback_record(query_id, chunk_id, feedback_type, comment)


def get_feedback_summary() -> dict:
    """Return aggregate counts for each supported feedback type."""
    return get_feedback_summary_record()
