"""Hybrid retrieval that combines keyword matches with semantic similarity."""

from src.database.access import (
    list_all_chunks,
    list_chunks_missing_embeddings,
)
from src.retrieval.embeddings import (
    EMBEDDING_MODEL,
    cosine_similarity,
    generate_embedding,
    load_embeddings,
)
from src.retrieval.keyword import score_chunks
from src.retrieval.query_normalization import normalize_retrieval_query


def normalize_scores(scores: dict[int, float]) -> dict[int, float]:
    """Scale scores to the 0-to-1 range while preserving their ordering."""
    if not scores:
        return {}

    minimum = min(scores.values())
    maximum = max(scores.values())
    if minimum == maximum:
        if maximum == 0:
            return {chunk_id: 0.0 for chunk_id in scores}
        return {chunk_id: 1.0 for chunk_id in scores}

    # Keyword counts and cosine similarity use different raw scales, so both
    # need normalization before one score can be meaningfully added to another.
    return {
        chunk_id: (score - minimum) / (maximum - minimum)
        for chunk_id, score in scores.items()
    }


def hybrid_search(
    query: str, alpha: float = 0.5, limit: int = 5, model: str = EMBEDDING_MODEL
) -> list[dict[str, int | str | float]]:
    """Rank fully embedded chunks using normalized keyword and semantic scores."""
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be between 0.0 and 1.0.")
    if limit <= 0:
        raise ValueError("limit must be greater than 0.")

    chunks = list_all_chunks()
    missing_embeddings = list_chunks_missing_embeddings(model)
    if missing_embeddings:
        raise RuntimeError(
            f"Embeddings are missing for {len(missing_embeddings)} chunks. "
            "Run: python3 main.py embed-chunks"
        )
    stored_embeddings = load_embeddings(None, model)

    if not chunks:
        return []

    normalized_query = normalize_retrieval_query(query) or query.strip().lower()
    keyword_results = score_chunks(normalized_query, chunks, limit=len(chunks))
    keyword_scores = {
        int(result["chunk_id"]): float(result["score"])
        for result in keyword_results
    }
    for chunk in chunks:
        keyword_scores.setdefault(int(chunk["id"]), 0.0)

    query_embedding = generate_embedding(normalized_query, model)
    semantic_scores = {
        int(stored["chunk_id"]): cosine_similarity(
            query_embedding, stored["embedding"]
        )
        for stored in stored_embeddings
        if isinstance(stored["embedding"], list)
    }

    normalized_keyword_scores = normalize_scores(keyword_scores)
    normalized_semantic_scores = normalize_scores(semantic_scores)
    results: list[dict[str, int | str | float]] = []

    for chunk in chunks:
        chunk_id = int(chunk["id"])
        keyword_score = keyword_scores[chunk_id]
        semantic_score = semantic_scores[chunk_id]
        normalized_keyword_score = normalized_keyword_scores[chunk_id]
        normalized_semantic_score = normalized_semantic_scores[chunk_id]

        # Alpha controls the balance: 1.0 uses only keyword scores, while 0.0
        # uses only semantic scores. Combining both can preserve exact terms
        # while still finding chunks that express the same idea differently.
        hybrid_score = (
            alpha * normalized_keyword_score
            + (1.0 - alpha) * normalized_semantic_score
        )
        results.append(
            {
                "chunk_id": chunk_id,
                "filename": str(chunk["filename"]),
                "chunk_index": int(chunk["chunk_index"]),
                "keyword_score": keyword_score,
                "normalized_keyword_score": normalized_keyword_score,
                "semantic_score": semantic_score,
                "normalized_semantic_score": normalized_semantic_score,
                "hybrid_score": hybrid_score,
                "text": str(chunk["text"]),
            }
        )

    return sorted(
        results,
        key=lambda result: (-float(result["hybrid_score"]), int(result["chunk_id"])),
    )[:limit]
