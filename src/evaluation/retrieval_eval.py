"""Hand-labeled retrieval evaluation for keyword, semantic, and hybrid search."""

import json
from pathlib import Path
from typing import Any

from src.db import (
    get_all_chunks,
    get_chunks_without_embeddings,
    get_connection,
    initialize_database,
)
from src.retrieval.embeddings import EMBEDDING_MODEL, semantic_search
from src.retrieval.hybrid import hybrid_search
from src.retrieval.keyword import score_chunks


METHODS = ("keyword", "semantic", "hybrid")


def load_evaluation_questions(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate a hand-labeled JSON evaluation dataset."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Evaluation file does not exist: {file_path}")

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Evaluation file is not valid JSON: {file_path}") from exc

    if not isinstance(data, list) or not data:
        raise ValueError("Evaluation JSON must contain a non-empty list of questions.")

    questions: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Evaluation item {index} must be an object.")

        question = item.get("question")
        relevant_chunk_ids = item.get("relevant_chunk_ids")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"Evaluation item {index} needs a non-empty question.")
        if not isinstance(relevant_chunk_ids, list) or not relevant_chunk_ids:
            raise ValueError(
                f"Evaluation item {index} needs at least one relevant_chunk_id."
            )
        if not all(
            isinstance(chunk_id, int) and not isinstance(chunk_id, bool) and chunk_id > 0
            for chunk_id in relevant_chunk_ids
        ):
            raise ValueError(
                f"Evaluation item {index} has invalid relevant_chunk_ids."
            )

        questions.append(
            {
                "question": question,
                "relevant_chunk_ids": relevant_chunk_ids,
                "notes": item.get("notes", ""),
            }
        )

    return questions


def ensure_embeddings_available() -> None:
    """Require complete embedding coverage before semantic comparisons begin."""
    with get_connection() as conn:
        initialize_database(conn)
        missing_chunks = get_chunks_without_embeddings(conn, EMBEDDING_MODEL)

    if missing_chunks:
        raise RuntimeError(
            f"Embeddings are missing for {len(missing_chunks)} chunks. "
            "Run: python3 main.py embed-chunks"
        )


def score_ranking(ranked_chunk_ids: list[int], relevant_chunk_ids: set[int]) -> dict[str, float]:
    """Calculate top-1, top-3, top-5, and reciprocal-rank metrics.

    Top-k recall tests whether any labeled chunk appears in the first k results.
    MRR rewards putting the first relevant chunk nearer the top of the ranking.
    """
    first_relevant_rank = next(
        (
            rank
            for rank, chunk_id in enumerate(ranked_chunk_ids, start=1)
            if chunk_id in relevant_chunk_ids
        ),
        None,
    )
    return {
        "top_1_accuracy": 1.0 if first_relevant_rank == 1 else 0.0,
        "top_3_recall": 1.0 if first_relevant_rank is not None and first_relevant_rank <= 3 else 0.0,
        "top_5_recall": 1.0 if first_relevant_rank is not None and first_relevant_rank <= 5 else 0.0,
        "mean_reciprocal_rank": 1.0 / first_relevant_rank
        if first_relevant_rank is not None
        else 0.0,
    }


def evaluate_retrieval(
    evaluation_path: str | Path, alpha: float = 0.5, top_k: int = 5
) -> dict[str, dict[str, float] | int]:
    """Compare retrieval methods against the labeled evaluation questions."""
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be between 0.0 and 1.0.")
    if top_k < 5:
        raise ValueError("top_k must be at least 5 to calculate top_5_recall.")

    questions = load_evaluation_questions(evaluation_path)
    # Hand-labeled relevant chunks provide a fixed target, allowing retrieval
    # quality to be measured before changing the system with a reranker.
    with get_connection() as conn:
        initialize_database(conn)
        chunks = get_all_chunks(conn)

    if not chunks:
        raise ValueError("No chunks found. Run: python3 main.py ingest notes/")

    available_chunk_ids = {int(chunk["id"]) for chunk in chunks}
    for index, question in enumerate(questions, start=1):
        unknown_chunk_ids = set(question["relevant_chunk_ids"]) - available_chunk_ids
        if unknown_chunk_ids:
            unknown_ids = ", ".join(str(chunk_id) for chunk_id in sorted(unknown_chunk_ids))
            raise ValueError(
                f"Evaluation item {index} refers to unknown chunk IDs: {unknown_ids}."
            )

    ensure_embeddings_available()
    totals = {
        method: {
            "top_1_accuracy": 0.0,
            "top_3_recall": 0.0,
            "top_5_recall": 0.0,
            "mean_reciprocal_rank": 0.0,
        }
        for method in METHODS
    }

    for item in questions:
        question = str(item["question"])
        relevant_chunk_ids = set(item["relevant_chunk_ids"])
        rankings = {
            "keyword": [
                int(result["chunk_id"])
                for result in score_chunks(question, chunks, limit=top_k)
            ],
            "semantic": [
                int(result["chunk_id"])
                for result in semantic_search(question, limit=top_k)
            ],
            "hybrid": [
                int(result["chunk_id"])
                for result in hybrid_search(question, alpha=alpha, limit=top_k)
            ],
        }

        for method, ranked_chunk_ids in rankings.items():
            scores = score_ranking(ranked_chunk_ids, relevant_chunk_ids)
            for metric, score in scores.items():
                totals[method][metric] += score

    question_count = len(questions)
    return {
        "question_count": question_count,
        **{
            method: {
                metric: total / question_count for metric, total in totals[method].items()
            }
            for method in METHODS
        },
    }
