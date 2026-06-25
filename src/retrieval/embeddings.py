"""OpenAI embedding helpers and simple semantic ranking for PrepLens.

An embedding is a list of numbers representing the meaning of a text string.
PrepLens stores embeddings for chunks and logged queries so it can compare text
by meaning without generating an answer.
"""

import json
import math
import os
import sqlite3
from typing import Any

from src.db import (
    count_chunks,
    count_queries,
    get_chunk_embeddings,
    get_chunks_without_embeddings,
    get_connection,
    get_queries_without_embeddings,
    get_query_embeddings,
    initialize_database,
    insert_chunk_embedding,
    insert_query_embedding,
)


EMBEDDING_MODEL = "text-embedding-3-small"


def create_openai_client() -> Any:
    """Create an OpenAI client using an API key from the environment."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it first, for example: "
            'export OPENAI_API_KEY="your_api_key"'
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The OpenAI package is not installed. Run: "
            "python3 -m pip install -r requirements.txt"
        ) from exc

    return OpenAI(api_key=api_key)


def generate_embedding(
    text: str, model: str = EMBEDDING_MODEL, client: Any | None = None
) -> list[float]:
    """Generate one embedding vector for a non-empty text string."""
    if not text.strip():
        raise ValueError("Cannot generate an embedding for empty text.")

    if client is None:
        client = create_openai_client()

    try:
        response = client.embeddings.create(input=text, model=model)
    except Exception as exc:
        raise RuntimeError(f"Could not generate embedding: {exc}") from exc

    return list(response.data[0].embedding)


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    """Measure vector alignment, which ranks semantically related text higher.

    Cosine similarity compares direction rather than raw vector size, making it
    a natural fit for comparing the query embedding with chunk embeddings.
    """
    if len(vector_a) != len(vector_b):
        raise ValueError("Embeddings must have the same number of dimensions.")

    magnitude_a = math.sqrt(sum(value * value for value in vector_a))
    magnitude_b = math.sqrt(sum(value * value for value in vector_b))
    if magnitude_a == 0 or magnitude_b == 0:
        raise ValueError("Cannot compare a zero-length embedding.")

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    return dot_product / (magnitude_a * magnitude_b)


def store_embedding(
    conn: sqlite3.Connection, chunk_id: int, model: str, embedding: list[float]
) -> None:
    """Serialize an embedding as JSON before saving it in SQLite."""
    insert_chunk_embedding(conn, chunk_id, model, json.dumps(embedding))


def store_query_embedding(
    conn: sqlite3.Connection, query_id: int, model: str, embedding: list[float]
) -> None:
    """Serialize a logged query embedding before saving it in SQLite."""
    insert_query_embedding(conn, query_id, model, json.dumps(embedding))


def load_embeddings(
    conn: sqlite3.Connection, model: str
) -> list[dict[str, int | str | list[float]]]:
    """Load stored JSON vectors with the chunk fields needed for search output."""
    embeddings: list[dict[str, int | str | list[float]]] = []
    for row in get_chunk_embeddings(conn, model):
        try:
            embedding = json.loads(str(row["embedding_json"]))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Stored embedding for chunk {row['chunk_id']} is not valid JSON."
            ) from exc

        if not isinstance(embedding, list) or not all(
            isinstance(value, (int, float)) for value in embedding
        ):
            raise ValueError(
                f"Stored embedding for chunk {row['chunk_id']} is not a number list."
            )

        embeddings.append(
            {
                "chunk_id": int(row["chunk_id"]),
                "filename": str(row["filename"]),
                "chunk_index": int(row["chunk_index"]),
                "text": str(row["text"]),
                "embedding": [float(value) for value in embedding],
            }
        )
    return embeddings


def load_query_embeddings(
    conn: sqlite3.Connection, model: str
) -> list[dict[str, int | str | list[float]]]:
    """Load stored JSON vectors with query fields needed for inspection."""
    embeddings: list[dict[str, int | str | list[float]]] = []
    for row in get_query_embeddings(conn, model):
        try:
            embedding = json.loads(str(row["embedding_json"]))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Stored embedding for query {row['query_id']} is not valid JSON."
            ) from exc

        if not isinstance(embedding, list) or not all(
            isinstance(value, (int, float)) for value in embedding
        ):
            raise ValueError(
                f"Stored embedding for query {row['query_id']} is not a number list."
            )

        embeddings.append(
            {
                "query_id": int(row["query_id"]),
                "query_text": str(row["query_text"]),
                "created_at": str(row["created_at"]),
                "embedding": [float(value) for value in embedding],
            }
        )
    return embeddings


def embed_stored_chunks(model: str = EMBEDDING_MODEL) -> dict[str, int]:
    """Create and store embeddings for chunks that are missing this model."""
    with get_connection() as conn:
        initialize_database(conn)
        missing_chunks = get_chunks_without_embeddings(conn, model)
        skipped_count = count_chunks(conn) - len(missing_chunks)

        if not missing_chunks:
            return {"created_count": 0, "skipped_count": skipped_count}

        client = create_openai_client()
        for chunk in missing_chunks:
            embedding = generate_embedding(str(chunk["text"]), model, client)
            store_embedding(conn, int(chunk["id"]), model, embedding)

        conn.commit()

    return {"created_count": len(missing_chunks), "skipped_count": skipped_count}


def embed_stored_queries(model: str = EMBEDDING_MODEL) -> dict[str, int]:
    """Create and store embeddings for logged queries missing this model."""
    with get_connection() as conn:
        initialize_database(conn)
        missing_queries = get_queries_without_embeddings(conn, model)
        skipped_count = count_queries(conn) - len(missing_queries)

        if not missing_queries:
            return {"created_count": 0, "skipped_count": skipped_count}

        # Already embedded queries are skipped because embeddings are stable for
        # a fixed text/model pair, and skipping avoids repeated API cost.
        client = create_openai_client()
        for query in missing_queries:
            embedding = generate_embedding(str(query["query_text"]), model, client)
            store_query_embedding(conn, int(query["id"]), model, embedding)

        conn.commit()

    return {"created_count": len(missing_queries), "skipped_count": skipped_count}


def semantic_search(
    query: str, model: str = EMBEDDING_MODEL, limit: int = 5
) -> list[dict[str, int | str | float]]:
    """Return the top chunk embeddings that are closest in meaning to a query."""
    if limit <= 0:
        raise ValueError("limit must be greater than 0.")

    with get_connection() as conn:
        initialize_database(conn)
        stored_embeddings = load_embeddings(conn, model)

    if not stored_embeddings:
        return []

    query_embedding = generate_embedding(query, model)
    results: list[dict[str, int | str | float]] = []
    for stored in stored_embeddings:
        embedding = stored["embedding"]
        if not isinstance(embedding, list):
            continue

        results.append(
            {
                "chunk_id": int(stored["chunk_id"]),
                "filename": str(stored["filename"]),
                "chunk_index": int(stored["chunk_index"]),
                "score": cosine_similarity(query_embedding, embedding),
                "text": str(stored["text"]),
            }
        )

    return sorted(
        results,
        key=lambda result: (-float(result["score"]), int(result["chunk_id"])),
    )[:limit]


def similar_queries(
    query: str, model: str = EMBEDDING_MODEL, limit: int = 5
) -> list[dict[str, int | str | float]]:
    """Return past logged queries closest in meaning to an input query."""
    if limit <= 0:
        raise ValueError("limit must be greater than 0.")

    with get_connection() as conn:
        initialize_database(conn)
        stored_embeddings = load_query_embeddings(conn, model)

    if not stored_embeddings:
        return []

    # Comparing a new query to past query embeddings is the raw material for
    # future feedback-aware retrieval: similar past questions can reveal which
    # retrieved chunks users marked helpful or wrong_source.
    query_embedding = generate_embedding(query, model)
    results: list[dict[str, int | str | float]] = []
    for stored in stored_embeddings:
        embedding = stored["embedding"]
        if not isinstance(embedding, list):
            continue

        results.append(
            {
                "query_id": int(stored["query_id"]),
                "query_text": str(stored["query_text"]),
                "created_at": str(stored["created_at"]),
                "score": cosine_similarity(query_embedding, embedding),
            }
        )

    return sorted(
        results,
        key=lambda result: (-float(result["score"]), int(result["query_id"])),
    )[:limit]
