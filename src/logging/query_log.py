"""Persistence and inspection helpers for successful ask runs."""

from src.database.access import (
    FEEDBACK_TYPES,
    add_feedback as add_feedback_record,
    get_feedback_summary as get_feedback_summary_record,
    get_query_details as get_query_details_record,
    list_recent_queries,
    log_ask_run_record,
)


def log_ask_run(
    query_text: str,
    alpha: float,
    top_k: int,
    model: str,
    answer_text: str,
    results: list[dict[str, int | str | float]],
) -> int:
    """Save one completed ask run and return its query id."""
    return log_ask_run_record(query_text, alpha, top_k, model, answer_text, results)


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
