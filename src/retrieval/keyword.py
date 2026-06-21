"""Small, dependency-free keyword search over stored chunk text."""

from collections import Counter
import re
from typing import Mapping


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


def tokenize(text: str) -> list[str]:
    """Lowercase text, remove basic punctuation, and omit common stopwords."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [word for word in words if word not in STOPWORDS]


def score_chunks(
    query: str, chunks: list[Mapping[str, int | str]], limit: int = 5
) -> list[dict[str, int | str]]:
    """Rank chunks by the number of times their query keywords occur.

    The score is the sum of the term frequencies for unique query keywords.
    This keeps the first search layer easy to inspect before adding a more
    sophisticated retrieval method later.
    """
    if limit <= 0:
        raise ValueError("limit must be greater than 0.")

    query_terms = set(tokenize(query))
    if not query_terms:
        raise ValueError("Search query must include at least one keyword.")

    results: list[dict[str, int | str]] = []
    for chunk in chunks:
        term_counts = Counter(tokenize(str(chunk["text"])))
        # A chunk earns one point for each occurrence of a query keyword.
        score = sum(term_counts[term] for term in query_terms)
        if score == 0:
            continue

        results.append(
            {
                "chunk_id": int(chunk["id"]),
                "filename": str(chunk["filename"]),
                "chunk_index": int(chunk["chunk_index"]),
                "score": score,
                "text": str(chunk["text"]),
            }
        )

    return sorted(
        results,
        key=lambda result: (-int(result["score"]), int(result["chunk_id"])),
    )[:limit]
