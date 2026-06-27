from pathlib import Path

from src.db import get_connection, initialize_database
from src.services.feedback_service import (
    add_source_feedback,
    get_feedback_summary_report,
)
from src.services.ingest_service import get_document_chunks, ingest_notes, list_documents


# Service tests use a temporary DB to exercise real service/database behavior
# without touching local data/preplens.db.


def test_ingest_lists_document_and_returns_chunks(
    tmp_path: Path, isolated_db: Path
) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    note_text = "# Dynamic Programming\n\nStore overlapping subproblem results."
    (notes_dir / "dynamic_programming.md").write_text(note_text, encoding="utf-8")

    ingest_report = ingest_notes(str(notes_dir))
    documents_report = list_documents()
    chunks_report = get_document_chunks(1)

    assert isolated_db.exists()
    assert ingest_report == {"document_count": 1, "chunk_count": 1}
    assert documents_report["documents"] == [
        {
            "id": 1,
            "filename": "dynamic_programming.md",
            "file_type": "md",
            "filepath": str(notes_dir / "dynamic_programming.md"),
            "chunk_count": 1,
        }
    ]
    assert chunks_report is not None
    assert chunks_report["document"]["id"] == 1
    assert chunks_report["chunks"][0]["text"] == note_text
    assert chunks_report["chunks"][0]["chunk_index"] == 0


def test_feedback_summary_is_empty_for_fresh_database(isolated_db: Path) -> None:
    summary = get_feedback_summary_report()

    assert isolated_db.exists()
    assert summary == {
        "total_feedback": 0,
        "helpful_count": 0,
        "not_helpful_count": 0,
        "wrong_source_count": 0,
    }


def test_add_feedback_uses_controlled_query_and_chunk(
    tmp_path: Path, isolated_db: Path
) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "linked_lists.md").write_text(
        "Use slow and fast pointers to detect a cycle.",
        encoding="utf-8",
    )
    ingest_notes(str(notes_dir))

    with get_connection() as conn:
        initialize_database(conn)
        query_cursor = conn.execute(
            """
            INSERT INTO queries (query_text, retrieval_method, alpha, top_k, model)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("how do I detect a cycle?", "hybrid", 0.5, 1, "test-model"),
        )
        query_id = int(query_cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO retrieval_results (
                query_id, chunk_id, "rank", keyword_score,
                normalized_keyword_score, semantic_score,
                normalized_semantic_score, hybrid_score, was_cited
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (query_id, 1, 1, 1.0, 1.0, 0.8, 0.8, 0.9, 1),
        )
        conn.commit()

    feedback = add_source_feedback(
        query_id,
        1,
        "helpful",
        "This source explained the pointer pattern.",
    )
    summary = get_feedback_summary_report()

    assert isolated_db.exists()
    assert feedback == {
        "feedback_id": 1,
        "query_id": query_id,
        "chunk_id": 1,
        "feedback_type": "helpful",
        "comment": "This source explained the pointer pattern.",
    }
    assert summary == {
        "total_feedback": 1,
        "helpful_count": 1,
        "not_helpful_count": 0,
        "wrong_source_count": 0,
    }
