"""Focused SQLAlchemy Core access helpers for PrepLens database workflows."""

from typing import Any

from sqlalchemy import and_, case, func, insert, literal, or_, select
from sqlalchemy.exc import SQLAlchemyError

from src.config import get_database_url
from src.database.engine import get_engine
from src.database.schema import (
    answers,
    chunk_embeddings,
    chunks,
    documents,
    feedback,
    metadata,
    queries,
    query_embeddings,
    retrieval_results,
)


FEEDBACK_TYPES = {"helpful", "not_helpful", "wrong_source"}


def initialize_schema() -> None:
    """Create all known tables from SQLAlchemy Core metadata."""
    engine = get_engine()
    try:
        metadata.create_all(engine)
    except SQLAlchemyError as exc:
        if get_database_url():
            raise RuntimeError(
                "Unable to initialize the database schema from DATABASE_URL. "
                "Verify that the configured database is reachable and that the "
                "credentials have permission to create or inspect tables."
            ) from exc
        raise


def insert_document_record(filename: str, filepath: str, file_type: str) -> int:
    """Insert one document row and return its generated id."""
    initialize_schema()
    with get_engine().begin() as conn:
        result = conn.execute(
            insert(documents).values(
                filename=filename,
                filepath=filepath,
                file_type=file_type,
            )
        )
        return int(result.inserted_primary_key[0])


def insert_chunk_records(
    document_id: int, chunk_rows: list[dict[str, int | str]]
) -> None:
    """Insert all chunks for a document."""
    if not chunk_rows:
        return

    initialize_schema()
    values = [
        {
            "document_id": document_id,
            "chunk_index": int(chunk["chunk_index"]),
            "text": str(chunk["text"]),
            "start_char": int(chunk["start_char"]),
            "end_char": int(chunk["end_char"]),
        }
        for chunk in chunk_rows
    ]
    with get_engine().begin() as conn:
        conn.execute(insert(chunks), values)


def list_all_chunks() -> list[dict[str, Any]]:
    """Return every stored chunk with the filename needed for search results."""
    initialize_schema()
    statement = (
        select(
            chunks.c.id,
            chunks.c.chunk_index,
            chunks.c.text,
            documents.c.filename,
        )
        .select_from(chunks.join(documents, documents.c.id == chunks.c.document_id))
        .order_by(chunks.c.id)
    )
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(statement).mappings().all()]


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


def list_chunks_missing_embeddings(model: str) -> list[dict[str, Any]]:
    """Return chunks without an embedding for the requested model."""
    initialize_schema()
    joined = chunks.outerjoin(
        chunk_embeddings,
        and_(
            chunk_embeddings.c.chunk_id == chunks.c.id,
            chunk_embeddings.c.model == model,
        ),
    )
    statement = (
        select(chunks.c.id, chunks.c.text)
        .select_from(joined)
        .where(chunk_embeddings.c.id.is_(None))
        .order_by(chunks.c.id)
    )
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(statement).mappings().all()]


def count_chunk_records() -> int:
    """Return the number of stored chunks."""
    initialize_schema()
    statement = select(func.count().label("chunk_count")).select_from(chunks)
    with get_engine().connect() as conn:
        return int(conn.execute(statement).scalar_one())


def save_chunk_embedding(chunk_id: int, model: str, embedding_json: str) -> None:
    """Store one serialized embedding for a chunk and model."""
    initialize_schema()
    with get_engine().begin() as conn:
        conn.execute(
            insert(chunk_embeddings).values(
                chunk_id=chunk_id,
                model=model,
                embedding_json=embedding_json,
            )
        )


def list_chunk_embeddings(model: str) -> list[dict[str, Any]]:
    """Return stored chunk embeddings with chunk metadata."""
    initialize_schema()
    statement = (
        select(
            chunks.c.id.label("chunk_id"),
            chunks.c.chunk_index,
            chunks.c.text,
            documents.c.filename,
            chunk_embeddings.c.embedding_json,
        )
        .select_from(
            chunk_embeddings.join(chunks, chunks.c.id == chunk_embeddings.c.chunk_id)
            .join(documents, documents.c.id == chunks.c.document_id)
        )
        .where(chunk_embeddings.c.model == model)
        .order_by(chunks.c.id)
    )
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(statement).mappings().all()]


def list_queries_missing_embeddings(model: str) -> list[dict[str, Any]]:
    """Return logged queries without an embedding for the requested model."""
    initialize_schema()
    joined = queries.outerjoin(
        query_embeddings,
        and_(
            query_embeddings.c.query_id == queries.c.id,
            query_embeddings.c.model == model,
        ),
    )
    statement = (
        select(queries.c.id, queries.c.query_text)
        .select_from(joined)
        .where(query_embeddings.c.id.is_(None))
        .order_by(queries.c.id)
    )
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(statement).mappings().all()]


def count_query_records() -> int:
    """Return the number of logged ask queries."""
    initialize_schema()
    statement = select(func.count().label("query_count")).select_from(queries)
    with get_engine().connect() as conn:
        return int(conn.execute(statement).scalar_one())


def save_query_embedding(query_id: int, model: str, embedding_json: str) -> None:
    """Store one serialized embedding for a logged query and model."""
    initialize_schema()
    with get_engine().begin() as conn:
        conn.execute(
            insert(query_embeddings).values(
                query_id=query_id,
                model=model,
                embedding_json=embedding_json,
            )
        )


def list_query_embeddings(model: str) -> list[dict[str, Any]]:
    """Return stored query embeddings with query metadata."""
    initialize_schema()
    statement = (
        select(
            queries.c.id.label("query_id"),
            queries.c.query_text,
            queries.c.created_at,
            query_embeddings.c.embedding_json,
        )
        .select_from(
            query_embeddings.join(queries, queries.c.id == query_embeddings.c.query_id)
        )
        .where(query_embeddings.c.model == model)
        .order_by(queries.c.id)
    )
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(statement).mappings().all()]


def list_feedback_for_queries(query_ids: list[int]) -> list[dict[str, Any]]:
    """Return feedback labels attached to the provided logged query IDs."""
    if not query_ids:
        return []

    initialize_schema()
    statement = (
        select(feedback.c.query_id, feedback.c.chunk_id, feedback.c.feedback_type)
        .where(feedback.c.query_id.in_(query_ids))
        .order_by(feedback.c.query_id, feedback.c.id)
    )
    with get_engine().connect() as conn:
        return [dict(row) for row in conn.execute(statement).mappings().all()]


def log_ask_run_record(
    query_text: str,
    alpha: float,
    top_k: int,
    model: str,
    answer_text: str,
    results: list[dict[str, int | str | float]],
) -> int:
    """Save one completed ask run and return its query id."""
    from src.generation.answer import get_cited_chunk_ids

    initialize_schema()
    cited_chunk_ids = get_cited_chunk_ids(answer_text)

    with get_engine().begin() as conn:
        query_result = conn.execute(
            insert(queries).values(
                query_text=query_text,
                retrieval_method="hybrid",
                alpha=alpha,
                top_k=top_k,
                model=model,
            )
        )
        query_id = int(query_result.inserted_primary_key[0])

        conn.execute(
            insert(answers).values(query_id=query_id, answer_text=answer_text)
        )

        # Store this retrieval snapshot per query because future embeddings or
        # scoring changes could rank the same chunks differently.
        retrieval_rows = [
            {
                "query_id": query_id,
                "chunk_id": int(result["chunk_id"]),
                "rank": rank,
                "keyword_score": float(result["keyword_score"]),
                "normalized_keyword_score": float(
                    result["normalized_keyword_score"]
                ),
                "semantic_score": float(result["semantic_score"]),
                "normalized_semantic_score": float(
                    result["normalized_semantic_score"]
                ),
                "hybrid_score": float(result["hybrid_score"]),
                # Every row was retrieved; this flag records which retrieved
                # chunks were cited in the generated answer.
                "was_cited": 1 if int(result["chunk_id"]) in cited_chunk_ids else 0,
            }
            for rank, result in enumerate(results, start=1)
        ]
        if retrieval_rows:
            conn.execute(insert(retrieval_results), retrieval_rows)

    return query_id


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
    feedback_text = func.coalesce(
        func.aggregate_strings(feedback_item, "; "),
        "",
    ).label("feedback")
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
