"""Reusable embedding workflows for chunk and query similarity tasks."""

from typing import Any

from src.retrieval.embeddings import (
    EMBEDDING_MODEL,
    embed_stored_chunks,
    embed_stored_queries,
    similar_queries,
)
from src.services.search_service import build_preview


def embed_chunks(model: str = EMBEDDING_MODEL) -> dict[str, int]:
    """Generate missing chunk embeddings through the lower-level retrieval module."""
    return embed_stored_chunks(model)


def embed_queries(model: str = EMBEDDING_MODEL) -> dict[str, int]:
    """Generate missing logged-query embeddings through the retrieval module."""
    return embed_stored_queries(model)


def find_similar_queries(
    query: str, model: str = EMBEDDING_MODEL, limit: int = 5
) -> dict[str, Any]:
    """Return logged queries closest in meaning to a new query."""
    results = []
    for rank, result in enumerate(
        similar_queries(query, model=model, limit=limit), start=1
    ):
        results.append(
            {
                "rank": rank,
                "query_id": int(result["query_id"]),
                "query_text": str(result["query_text"]),
                "created_at": str(result["created_at"]),
                "semantic_score": float(result["score"]),
                "preview": build_preview(str(result["query_text"])),
            }
        )

    return {"query": query, "method": "similar_queries", "model": model, "results": results}
