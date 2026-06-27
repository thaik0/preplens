"""Reusable retrieval evaluation workflow."""

from typing import Any

from src.evaluation.retrieval_eval import evaluate_retrieval


def run_retrieval_evaluation(
    evaluation_path: str,
    alpha: float = 0.5,
    top_k: int = 5,
    include_feedback: bool = False,
    candidate_k: int = 20,
    similarity_threshold: float = 0.65,
    gamma: float = 0.20,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run labeled retrieval evaluation and return structured metrics."""
    return evaluate_retrieval(
        evaluation_path,
        alpha=alpha,
        top_k=top_k,
        include_feedback=include_feedback,
        candidate_k=candidate_k,
        similarity_threshold=similarity_threshold,
        gamma=gamma,
        verbose=verbose,
    )
