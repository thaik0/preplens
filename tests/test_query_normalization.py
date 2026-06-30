from src.retrieval.keyword import score_chunks
from src.retrieval.query_normalization import normalize_retrieval_query


def test_normalize_retrieval_query_removes_conversation_and_expands_dfs() -> None:
    normalized = normalize_retrieval_query(
        "how do i conduct DFS on a adjacency list?"
    )
    tokens = normalized.split()

    for expected in [
        "dfs",
        "adjacency",
        "list",
        "graph",
        "traversal",
        "visited",
        "recursion",
        "stack",
        "neighbors",
    ]:
        assert expected in tokens

    for stopword in ["how", "do", "i"]:
        assert stopword not in tokens


def test_natural_language_dfs_query_prefers_graph_chunk_over_dp_helper() -> None:
    chunks = [
        {
            "id": 1,
            "filename": "basic-graphs.md",
            "chunk_index": 0,
            "text": "DFS graph adjacency list visited neighbors recursion stack",
        },
        {
            "id": 2,
            "filename": "dynamic_programming.md",
            "chunk_index": 0,
            "text": "Use dfs(r, c) as a recursive helper for grid dynamic programming.",
        },
    ]

    results = score_chunks(
        "how do i conduct DFS on a adjacency list?",
        chunks,
        limit=2,
    )

    assert results[0]["filename"] == "basic-graphs.md"
    assert results[1]["filename"] == "dynamic_programming.md"
