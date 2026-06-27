"""Reusable search workflows for CLI commands and future API handlers."""

from typing import Any

from src.db import get_all_chunks, get_connection, initialize_database
from src.retrieval.embeddings import EMBEDDING_MODEL, semantic_search
from src.retrieval.feedback_aware import feedback_search as feedback_aware_search
from src.retrieval.hybrid import hybrid_search
from src.retrieval.keyword import score_chunks


def build_preview(text: str, max_length: int = 240) -> str:
    """Turn chunk text into a compact one-line preview for structured results."""
    preview = " ".join(text.split())
    if len(preview) <= max_length:
        return preview
    return f"{preview[:max_length].rstrip()}..."


def _base_result(rank: int, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": rank,
        "chunk_id": int(result["chunk_id"]),
        "document_name": str(result["filename"]),
        "chunk_index": int(result["chunk_index"]),
        "preview": build_preview(str(result["text"])),
        "text": str(result["text"]),
    }


def keyword_search(query: str, limit: int = 5) -> dict[str, Any]:
    """Run keyword retrieval and return structured results."""
    with get_connection() as conn:
        initialize_database(conn)
        chunks = get_all_chunks(conn)

    if not chunks:
        return {"query": query, "method": "keyword", "results": []}

    results = []
    for rank, result in enumerate(score_chunks(query, chunks, limit=limit), start=1):
        item = _base_result(rank, result)
        item["keyword_score"] = int(result["score"])
        results.append(item)

    return {"query": query, "method": "keyword", "results": results}


def semantic_chunk_search(
    query: str, limit: int = 5, model: str = EMBEDDING_MODEL
) -> dict[str, Any]:
    """Run semantic retrieval and return structured results."""
    results = []
    for rank, result in enumerate(semantic_search(query, model=model, limit=limit), start=1):
        item = _base_result(rank, result)
        item["semantic_score"] = float(result["score"])
        results.append(item)

    return {"query": query, "method": "semantic", "model": model, "results": results}


def hybrid_chunk_search(
    query: str, alpha: float = 0.5, limit: int = 5, model: str = EMBEDDING_MODEL
) -> dict[str, Any]:
    """Run hybrid retrieval and return structured results."""
    results = []
    for rank, result in enumerate(
        hybrid_search(query, alpha=alpha, limit=limit, model=model), start=1
    ):
        item = _base_result(rank, result)
        item.update(
            {
                "keyword_score": float(result["keyword_score"]),
                "normalized_keyword_score": float(result["normalized_keyword_score"]),
                "semantic_score": float(result["semantic_score"]),
                "normalized_semantic_score": float(
                    result["normalized_semantic_score"]
                ),
                "hybrid_score": float(result["hybrid_score"]),
            }
        )
        results.append(item)

    return {
        "query": query,
        "method": "hybrid",
        "alpha": alpha,
        "model": model,
        "results": results,
    }


def feedback_chunk_search(
    query: str,
    top_k: int = 5,
    candidate_k: int = 20,
    alpha: float = 0.5,
    similarity_threshold: float = 0.65,
    gamma: float = 0.20,
    model: str = EMBEDDING_MODEL,
) -> dict[str, Any]:
    """Run feedback-aware retrieval and return structured results plus diagnostics."""
    report = feedback_aware_search(
        query,
        top_k=top_k,
        candidate_k=candidate_k,
        alpha=alpha,
        similarity_threshold=similarity_threshold,
        gamma=gamma,
        model=model,
    )
    raw_results = report["results"]
    diagnostics = report["diagnostics"]
    if not isinstance(raw_results, list) or not isinstance(diagnostics, dict):
        raise RuntimeError("Feedback search returned an invalid report.")

    results = []
    for rank, result in enumerate(raw_results, start=1):
        item = _base_result(rank, result)
        item.update(
            {
                "keyword_score": float(result["keyword_score"]),
                "normalized_keyword_score": float(result["normalized_keyword_score"]),
                "semantic_score": float(result["semantic_score"]),
                "normalized_semantic_score": float(
                    result["normalized_semantic_score"]
                ),
                "hybrid_score": float(result["hybrid_score"]),
                "feedback_score": float(result["feedback_score"]),
                "final_score": float(result["final_score"]),
            }
        )
        results.append(item)

    return {
        "query": query,
        "method": "feedback_aware",
        "alpha": alpha,
        "top_k": top_k,
        "candidate_k": candidate_k,
        "similarity_threshold": similarity_threshold,
        "gamma": gamma,
        "model": model,
        "results": results,
        "diagnostics": diagnostics,
    }
