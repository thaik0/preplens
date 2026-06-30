"""Interactive helpers for collecting source feedback after ask runs."""

from collections.abc import Callable, Mapping
from typing import Any

from src.logging.query_log import add_feedback


FEEDBACK_ALIASES = {
    "h": "helpful",
    "helpful": "helpful",
    "n": "not_helpful",
    "not_helpful": "not_helpful",
    "w": "wrong_source",
    "wrong_source": "wrong_source",
}
SKIP_ALIASES = {"", "s", "skip"}


def parse_feedback_input(raw_value: str) -> tuple[str | None, str | None]:
    """Parse a feedback label and optional comment from one prompt response."""
    cleaned = raw_value.strip()
    if not cleaned:
        return None, None

    label, _, comment = cleaned.partition(" ")
    normalized_label = label.lower()
    if normalized_label in SKIP_ALIASES:
        return None, None
    if normalized_label not in FEEDBACK_ALIASES:
        allowed = "h/helpful, n/not_helpful, w/wrong_source, s/skip"
        raise ValueError(f"Enter one of: {allowed}.")

    return FEEDBACK_ALIASES[normalized_label], comment.strip() or None


def collect_source_feedback(
    query_id: int,
    retrieved_chunks: list[Mapping[str, Any]],
    preview_builder: Callable[[str], str],
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> None:
    """Prompt for source-level labels on the chunks retrieved for one ask run."""
    # Immediate feedback captures whether the visible sources helped while the
    # user's judgment is fresh, before a future UI or reranker exists.
    output_func("")
    output_func("Source feedback:")
    output_func(
        "Enter [h]elpful, [n]ot_helpful, [w]rong_source, or press [Enter] to skip."
    )

    for chunk in retrieved_chunks:
        cited = "yes" if chunk["was_cited"] else "no"
        output_func("")
        output_func(
            f"Chunk {chunk['chunk_id']} | {chunk['filename']} | "
            f"chunk {chunk['chunk_index']} | cited: {cited}"
        )
        output_func(f"   {preview_builder(str(chunk['text']))}")

        # Feedback is source-level because retrieval quality depends on whether
        # each chunk was useful evidence, not just whether the final answer read
        # well. These labels can later become examples for feedback-aware
        # retrieval or reranking.
        while True:
            raw_value = input_func("Feedback: ")
            try:
                feedback_type, comment = parse_feedback_input(raw_value)
            except ValueError as exc:
                output_func(f"Error: {exc}")
                continue

            if feedback_type is None:
                output_func("Skipped.")
                break

            feedback_id = add_feedback(
                query_id, int(chunk["chunk_id"]), feedback_type, comment
            )
            output_func(
                f"Saved feedback ID: {feedback_id} | chunk "
                f"{chunk['chunk_id']} | {feedback_type}"
            )
            break
