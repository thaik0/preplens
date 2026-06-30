"""Focused SQLAlchemy Core access helpers for low-risk database workflows."""

from typing import Any

from sqlalchemy import and_, case, func, insert, literal, or_, select

from src.database.engine import get_engine
from src.database.schema import (
    answers,
    chunks,
    documents,
    feedback,
    metadata,
    queries,
    retrieval_results,
)


FEEDBACK_TYPES = {"helpful", "not_helpful", "wrong_source"}


def initialize_schema() -> None:
    """Create all known tables from SQLAlchemy Core metadata."""
    engine = get_engine()
    metadata.create_all(engine)


def list_documents_with_chunk_counts() -> list[dict[str, Any]]:
    """Return ingested documents with chunk counts."""
    initialize_schema()
    statement = (
        select(
            documents.c.id,
            documents.c.filename,
            documents.c.file_type,
            documents.c.filepath,
            func.count(chunks.c.id).label("chunk_count"),
        )
        .select_from(documents.outerjoin(chunks, chunks.c.document_id == documents.c.id))
        .group_by(documents.c.id)
        .order_by(documents.c.id)
    )
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(statement).mappings().all()]


def get_document_with_chunks(document_id: int) -> dict[str, Any] | None:
    """Return one document and its chunks, or None when it is missing."""
    initialize_schema()
    document_statement = (
        select(documents.c.id, documents.c.filename, documents.c.filepath)
        .where(documents.c.id == document_id)
    )
    chunks_statement = (
        select(chunks.c.chunk_index, chunks.c.text, chunks.c.start_char, chunks.c.end_char)
        .where(chunks.c.document_id == document_id)
        .order_by(chunks.c.chunk_index)
    )
    with get_engine().connect() as conn:
        document = conn.execute(document_statement).mappings().first()
        if document is None:
            return None
        chunk_rows = conn.execute(chunks_statement).mappings().all()

    return {
        "document": dict(document),
        "chunks": [dict(row) for row in chunk_rows],
    }


def list_recent_queries(limit: int = 10) -> list[dict[str, Any]]:
    """Return recent query records for history views."""
    if limit <= 0:
        raise ValueError("limit must be greater than 0.")

    initialize_schema()
    statement = (
        select(
            queries.c.id,
            queries.c.query_text,
            queries.c.retrieval_method,
            queries.c.model,
            queries.c.created_at,
        )
        .order_by(queries.c.created_at.desc(), queries.c.id.desc())
        .limit(limit)
    )
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(statement).mappings().all()]


def get_query_details(query_id: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Return one saved query and the retrieval rows attached to it."""
    initialize_schema()
    query_statement = (
        select(
            queries.c.id,
            queries.c.query_text,
            queries.c.retrieval_method,
            queries.c.alpha,
            queries.c.top_k,
            queries.c.model,
            queries.c.created_at,
            answers.c.answer_text,
        )
        .select_from(queries.outerjoin(answers, answers.c.query_id == queries.c.id))
        .where(queries.c.id == query_id)
    )

    feedback_item = feedback.c.feedback_type + case(
        (
            or_(feedback.c.comment.is_(None), feedback.c.comment == ""),
            literal(""),
        ),
        else_=literal(": ") + feedback.c.comment,
    )
    feedback_text = func.coalesce(func.group_concat(feedback_item, "; "), "").label(
        "feedback"
    )
    results_statement = (
        select(
            retrieval_results.c.rank,
            retrieval_results.c.chunk_id,
            retrieval_results.c.hybrid_score,
            retrieval_results.c.was_cited,
            chunks.c.chunk_index,
            chunks.c.text,
            documents.c.filename,
            feedback_text,
        )
        .select_from(
            retrieval_results.join(chunks, chunks.c.id == retrieval_results.c.chunk_id)
            .join(documents, documents.c.id == chunks.c.document_id)
            .outerjoin(
                feedback,
                and_(
                    feedback.c.query_id == retrieval_results.c.query_id,
                    feedback.c.chunk_id == retrieval_results.c.chunk_id,
                ),
            )
        )
        .where(retrieval_results.c.query_id == query_id)
        .group_by(
            retrieval_results.c.id,
            retrieval_results.c.rank,
            retrieval_results.c.chunk_id,
            retrieval_results.c.hybrid_score,
            retrieval_results.c.was_cited,
            chunks.c.chunk_index,
            chunks.c.text,
            documents.c.filename,
        )
        .order_by(retrieval_results.c.rank)
    )

    with get_engine().connect() as conn:
        query = conn.execute(query_statement).mappings().first()
        if query is None:
            return None, []
        results = conn.execute(results_statement).mappings().all()

    return dict(query), [dict(row) for row in results]


def add_feedback(
    query_id: int, chunk_id: int, feedback_type: str, comment: str | None = None
) -> int:
    """Save feedback for a chunk retrieved by a saved query."""
    if feedback_type not in FEEDBACK_TYPES:
        allowed_types = ", ".join(sorted(FEEDBACK_TYPES))
        raise ValueError(f"feedback_type must be one of: {allowed_types}.")

    initialize_schema()
    with get_engine().begin() as conn:
        query_exists = conn.execute(
            select(queries.c.id).where(queries.c.id == query_id)
        ).first()
        if query_exists is None:
            raise ValueError(f"No saved query found with id {query_id}.")

        was_retrieved = conn.execute(
            select(retrieval_results.c.id).where(
                and_(
                    retrieval_results.c.query_id == query_id,
                    retrieval_results.c.chunk_id == chunk_id,
                )
            )
        ).first()
        if was_retrieved is None:
            raise ValueError(
                f"Chunk {chunk_id} was not retrieved for query ID {query_id}."
            )

        result = conn.execute(
            insert(feedback).values(
                query_id=query_id,
                chunk_id=chunk_id,
                feedback_type=feedback_type,
                comment=comment or None,
            )
        )
        return int(result.inserted_primary_key[0])


def get_feedback_summary() -> dict[str, int]:
    """Return aggregate counts for each supported feedback type."""
    initialize_schema()
    statement = select(
        func.count().label("total_feedback"),
        func.coalesce(
            func.sum(case((feedback.c.feedback_type == "helpful", 1), else_=0)),
            0,
        ).label("helpful_count"),
        func.coalesce(
            func.sum(case((feedback.c.feedback_type == "not_helpful", 1), else_=0)),
            0,
        ).label("not_helpful_count"),
        func.coalesce(
            func.sum(case((feedback.c.feedback_type == "wrong_source", 1), else_=0)),
            0,
        ).label("wrong_source_count"),
    ).select_from(feedback)
    with get_engine().connect() as conn:
        row = conn.execute(statement).mappings().one()
    return {key: int(value) for key, value in dict(row).items()}
