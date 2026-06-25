"""Feedback-aware retrieval built on top of hybrid candidate ranking."""

from src.db import get_connection, get_feedback_for_queries, initialize_database
from src.retrieval.embeddings import (
    EMBEDDING_MODEL,
    cosine_similarity,
    generate_embedding,
    load_query_embeddings,
)
from src.retrieval.hybrid import hybrid_search


FEEDBACK_LABEL_VALUES = {
    "helpful": 1.0,
    "not_helpful": -1.0,
    "wrong_source": -1.0,
}


def feedback_search(
    query: str,
    top_k: int = 5,
    candidate_k: int = 20,
    alpha: float = 0.5,
    similarity_threshold: float = 0.65,
    gamma: float = 0.20,
    model: str = EMBEDDING_MODEL,
) -> dict[str, object]:
    """Rerank hybrid candidates using feedback from similar past queries."""
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")
    if candidate_k <= 0:
        raise ValueError("candidate_k must be greater than 0.")
    if candidate_k < top_k:
        raise ValueError("candidate_k must be greater than or equal to top_k.")
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be between 0.0 and 1.0.")
    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("similarity_threshold must be between 0.0 and 1.0.")
    if gamma < 0:
        raise ValueError("gamma must be greater than or equal to 0.")

    with get_connection() as conn:
        initialize_database(conn)
        stored_query_embeddings = load_query_embeddings(conn, model)

    if not stored_query_embeddings:
        raise RuntimeError(
            "No query embeddings found. Run: python3 main.py embed-queries"
        )

    # Hybrid retrieval remains the candidate generator. Feedback can only rerank
    # these already-retrieved chunks, so old labels cannot introduce unrelated
    # chunks outside the current query's lexical/semantic candidate set.
    candidates = hybrid_search(query, alpha=alpha, limit=candidate_k, model=model)
    if not candidates:
        return {
            "results": [],
            "diagnostics": {
                "checked_query_embeddings": len(stored_query_embeddings),
                "similar_query_count": 0,
                "feedback_labels_used": 0,
                "top_similar_queries": [],
                "used_feedback": False,
            },
        }

    query_embedding = generate_embedding(query, model)
    similar_queries = []
    for stored in stored_query_embeddings:
        embedding = stored["embedding"]
        if not isinstance(embedding, list):
            continue

        similarity = cosine_similarity(query_embedding, embedding)
        if similarity >= similarity_threshold:
            similar_queries.append(
                {
                    "query_id": int(stored["query_id"]),
                    "query_text": str(stored["query_text"]),
                    "created_at": str(stored["created_at"]),
                    "similarity": similarity,
                }
            )

    similar_queries.sort(
        key=lambda item: (-float(item["similarity"]), int(item["query_id"]))
    )
    similar_query_ids = [int(item["query_id"]) for item in similar_queries]
    similarity_by_query_id = {
        int(item["query_id"]): float(item["similarity"]) for item in similar_queries
    }

    feedback_scores = {int(candidate["chunk_id"]): 0.0 for candidate in candidates}
    candidate_chunk_ids = set(feedback_scores)
    feedback_labels_used = 0

    with get_connection() as conn:
        initialize_database(conn)
        feedback_rows = get_feedback_for_queries(conn, similar_query_ids)

    for row in feedback_rows:
        chunk_id = int(row["chunk_id"])
        if chunk_id not in candidate_chunk_ids:
            continue

        label_value = FEEDBACK_LABEL_VALUES.get(str(row["feedback_type"]), 0.0)
        if label_value == 0.0:
            continue

        # Feedback is conditioned on similar queries because a chunk can be
        # helpful for one question and distracting for another. The historical
        # query similarity weights how much that past label should matter now.
        feedback_scores[chunk_id] += (
            similarity_by_query_id[int(row["query_id"])] * label_value
        )
        feedback_labels_used += 1

    results = []
    for candidate in candidates:
        chunk_id = int(candidate["chunk_id"])
        feedback_score = feedback_scores[chunk_id]
        # Gamma controls how much source feedback can move the baseline hybrid
        # score. Keeping it small makes this an explainable reranking signal,
        # and the same features could later feed a learned reranker.
        final_score = float(candidate["hybrid_score"]) + gamma * feedback_score
        result = dict(candidate)
        result["feedback_score"] = feedback_score
        result["final_score"] = final_score
        results.append(result)

    results.sort(
        key=lambda result: (-float(result["final_score"]), int(result["chunk_id"]))
    )

    return {
        "results": results[:top_k],
        "diagnostics": {
            "checked_query_embeddings": len(stored_query_embeddings),
            "similar_query_count": len(similar_queries),
            "feedback_labels_used": feedback_labels_used,
            "top_similar_queries": similar_queries[:3],
            "used_feedback": feedback_labels_used > 0,
        },
    }
