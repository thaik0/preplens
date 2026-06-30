import pytest

from src.generation.answer import (
    build_grounded_answer_prompt,
    get_cited_chunk_ids,
    get_cited_source_numbers,
    map_cited_source_numbers_to_chunk_ids,
    validate_answer_citations,
)


def retrieved_chunks() -> list[dict[str, int | str | float]]:
    return [
        {
            "chunk_id": 96,
            "filename": "basic-graphs.md",
            "chunk_index": 4,
            "text": "DFS on an adjacency list visits neighbors recursively.",
        },
        {
            "chunk_id": 21,
            "filename": "advanced-graphs.md",
            "chunk_index": 2,
            "text": "Use a visited set to avoid revisiting graph nodes.",
        },
        {
            "chunk_id": 15,
            "filename": "basic-graphs.md",
            "chunk_index": 1,
            "text": "A stack can drive iterative DFS.",
        },
    ]


def test_prompt_uses_source_numbers_and_keeps_chunk_ids_as_metadata() -> None:
    prompt = build_grounded_answer_prompt("How do I run DFS?", retrieved_chunks())

    assert "[1] basic-graphs.md, chunk_id=96" in prompt
    assert "[2] advanced-graphs.md, chunk_id=21" in prompt
    assert "Do not cite chunk IDs." in prompt


def test_source_number_citations_are_validated_instead_of_chunk_ids() -> None:
    answer = "Run DFS from the start node and mark each neighbor visited [1]."

    validate_answer_citations(answer, retrieved_chunks())

    assert get_cited_source_numbers(answer) == {1}


def test_chunk_id_citations_are_not_valid_source_number_citations() -> None:
    answer = "Run DFS from the start node [96]."

    with pytest.raises(RuntimeError, match="not retrieved: 96"):
        validate_answer_citations(answer, retrieved_chunks())


def test_unlisted_source_number_fails_validation() -> None:
    answer = "Use visited to avoid cycles [4]."

    with pytest.raises(RuntimeError, match="not retrieved: 4"):
        validate_answer_citations(answer, retrieved_chunks())


def test_cited_source_numbers_map_back_to_real_chunk_ids() -> None:
    answer = "Use a visited set before recursing into neighbors [2]."

    assert map_cited_source_numbers_to_chunk_ids(answer, retrieved_chunks()) == {21}
    assert get_cited_chunk_ids(answer, retrieved_chunks()) == {21}


def test_legacy_chunk_citations_still_map_for_stored_answers() -> None:
    answer = "Use a visited set before recursing into neighbors [chunk 21]."

    assert get_cited_chunk_ids(answer, retrieved_chunks()) == {21}
