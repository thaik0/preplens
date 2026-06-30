"""Reusable feedback workflows around persisted source-level labels."""

from typing import Any

from src.database.access import FEEDBACK_TYPES, add_feedback, get_feedback_summary


def add_source_feedback(
    query_id: int, chunk_id: int, feedback_type: str, comment: str | None = None
) -> dict[str, Any]:
    """Save feedback for one retrieved query/chunk pair."""
    feedback_id = add_feedback(query_id, chunk_id, feedback_type, comment)
    return {
        "feedback_id": feedback_id,
        "query_id": query_id,
        "chunk_id": chunk_id,
        "feedback_type": feedback_type,
        "comment": comment,
    }


def get_feedback_summary_report() -> dict[str, int]:
    """Return aggregate counts for source feedback labels."""
    summary = get_feedback_summary()
    return {
        "total_feedback": int(summary["total_feedback"]),
        "helpful_count": int(summary["helpful_count"]),
        "not_helpful_count": int(summary["not_helpful_count"]),
        "wrong_source_count": int(summary["wrong_source_count"]),
    }
