"""Reusable ask workflow for the CLI and a future API backend."""

from typing import Any

from src.generation.answer import DEFAULT_ANSWER_MODEL, generate_grounded_answer
from src.logging.query_log import log_ask_run
from src.retrieval.hybrid import hybrid_search
from src.services.search_service import build_preview


def ask_question(
    question: str,
    top_k: int = 5,
    alpha: float = 0.5,
    model: str = DEFAULT_ANSWER_MODEL,
) -> dict[str, Any]:
    """Retrieve source chunks, generate a cited answer, and log the ask run.

    The service returns structured data; input prompts and terminal formatting
    stay in the CLI layer.
    """
    results = hybrid_search(question, alpha=alpha, limit=top_k)
    if not results:
        return {
            "query_id": None,
            "question": question,
            "answer": "",
            "sources": [],
        }

    answer = generate_grounded_answer(question, results, model=model)
    query_id = log_ask_run(question, alpha, top_k, model, answer, results)

    sources = []
    for rank, result in enumerate(results, start=1):
        sources.append(
            {
                "rank": rank,
                "chunk_id": int(result["chunk_id"]),
                "document_name": str(result["filename"]),
                "chunk_index": int(result["chunk_index"]),
                "keyword_score": float(result["keyword_score"]),
                "normalized_keyword_score": float(
                    result["normalized_keyword_score"]
                ),
                "semantic_score": float(result["semantic_score"]),
                "normalized_semantic_score": float(
                    result["normalized_semantic_score"]
                ),
                "hybrid_score": float(result["hybrid_score"]),
                "preview": build_preview(str(result["text"])),
                "text": str(result["text"]),
            }
        )

    return {
        "query_id": query_id,
        "question": question,
        "answer": answer,
        "sources": sources,
    }
