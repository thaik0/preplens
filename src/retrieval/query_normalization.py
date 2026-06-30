"""Deterministic query normalization for retrieval scoring."""

import re


STOPWORDS = {
    "how",
    "do",
    "i",
    "me",
    "my",
    "a",
    "an",
    "the",
    "on",
    "in",
    "to",
    "of",
    "for",
    "with",
    "is",
    "are",
    "can",
    "should",
    "would",
    "could",
    "please",
}

TECHNICAL_TERMS = {
    "dfs",
    "bfs",
    "graph",
    "adjacency",
    "list",
    "tree",
    "dp",
    "dynamic",
    "programming",
    "recursion",
    "stack",
    "queue",
    "visited",
    "cycle",
    "topological",
}


def _append_unique(tokens: list[str], additions: list[str]) -> None:
    seen = set(tokens)
    for token in additions:
        if token not in seen:
            tokens.append(token)
            seen.add(token)


def normalize_retrieval_query(query: str) -> str:
    """Return a compact retrieval-only query with deterministic expansions."""
    raw_tokens = re.findall(r"[a-z0-9]+", query.lower())
    normalized_tokens = [
        token
        for token in raw_tokens
        if token not in STOPWORDS or token in TECHNICAL_TERMS
    ]
    raw_token_set = set(raw_tokens)

    if "dfs" in raw_token_set:
        _append_unique(
            normalized_tokens,
            ["graph", "traversal", "visited", "recursion", "stack"],
        )
    if "bfs" in raw_token_set:
        _append_unique(
            normalized_tokens,
            ["graph", "traversal", "visited", "queue", "shortest", "path"],
        )
    if "adjacency list" in query.lower() or {
        "adjacency",
        "list",
    }.issubset(raw_token_set):
        _append_unique(normalized_tokens, ["graph", "neighbors"])
    if "cycle" in raw_token_set:
        _append_unique(normalized_tokens, ["graph", "detection", "visited"])
    if "topological" in raw_token_set:
        _append_unique(
            normalized_tokens,
            ["directed", "graph", "dag", "indegree"],
        )

    return " ".join(normalized_tokens)
