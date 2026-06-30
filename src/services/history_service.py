"""Reusable query-history inspection workflows."""

from typing import Any

from src.database.access import get_query_details, list_recent_queries
from src.generation.answer import get_cited_chunk_ids
from src.services.search_service import build_preview


def list_query_history(limit: int = 10) -> dict[str, Any]:
    """Return recent saved ask queries in API-friendly form."""
    queries = []
    for query in list_recent_queries(limit=limit):
        queries.append(
            {
                "id": int(query["id"]),
                "query_text": str(query["query_text"]),
                "retrieval_method": str(query["retrieval_method"]),
                "model": str(query["model"]),
                "created_at": str(query["created_at"]),
                "preview": build_preview(str(query["query_text"]), 100),
            }
        )
    return {"queries": queries}


def show_query_details(query_id: int) -> dict[str, Any] | None:
    """Return one saved question with answer, retrieved chunks, and feedback."""
    query, results = get_query_details(query_id)
    if query is None:
        return None

    retrieved_chunks = []
    for result in results:
        retrieved_chunks.append(
            {
                "rank": int(result["rank"]),
                "chunk_id": int(result["chunk_id"]),
                "document_name": str(result["filename"]),
                "chunk_index": int(result["chunk_index"]),
                "hybrid_score": float(result["hybrid_score"]),
                "was_cited": bool(result["was_cited"]),
                "feedback": str(result["feedback"]) or "",
                "preview": build_preview(str(result["text"])),
                "text": str(result["text"]),
            }
        )

    answer_text = str(query["answer_text"] or "")
    return {
        "query": {
            "id": int(query["id"]),
            "query_text": str(query["query_text"]),
            "retrieval_method": str(query["retrieval_method"]),
            "alpha": float(query["alpha"]),
            "top_k": int(query["top_k"]),
            "model": str(query["model"]),
            "created_at": str(query["created_at"]),
            "answer_text": answer_text,
            "cited_chunk_ids": sorted(get_cited_chunk_ids(answer_text)),
        },
        "retrieved_chunks": retrieved_chunks,
    }
