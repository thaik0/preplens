"""Thin FastAPI layer over the PrepLens service modules."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
import time
from typing import Any, TypeVar

from fastapi import FastAPI, HTTPException, Query

from src.config import get_database_url
from src.database.access import initialize_schema
from src.generation.answer import DEFAULT_ANSWER_MODEL
from src.services.ask_service import ask_question
from src.services.feedback_service import (
    add_source_feedback,
    get_feedback_summary_report,
)
from src.services.history_service import list_query_history, show_query_details
from src.services.ingest_service import get_document_chunks, list_documents
from src.services.search_service import feedback_chunk_search, hybrid_chunk_search

from .schemas import (
    AskRequest,
    AskResponse,
    DocumentChunksResponse,
    DocumentsResponse,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackSearchRequest,
    FeedbackSearchResponse,
    FeedbackSummaryResponse,
    HealthResponse,
    HistoryResponse,
    HybridSearchRequest,
    QueryDetailsResponse,
    SearchResponse,
)


T = TypeVar("T")

POSTGRES_SCHEMA_INIT_ATTEMPTS = 10
POSTGRES_SCHEMA_INIT_DELAY_SECONDS = 2.0


def _initialize_external_schema_with_retries(
    attempts: int = POSTGRES_SCHEMA_INIT_ATTEMPTS,
    delay_seconds: float = POSTGRES_SCHEMA_INIT_DELAY_SECONDS,
) -> None:
    """Initialize external database schema, retrying while Postgres starts."""
    if not get_database_url():
        return

    last_error: RuntimeError | None = None
    for attempt in range(1, attempts + 1):
        try:
            initialize_schema()
            return
        except RuntimeError as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(delay_seconds)

    if last_error is not None:
        raise last_error


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _initialize_external_schema_with_retries()
    yield


app = FastAPI(title="PrepLens API", version="0.1.0", lifespan=lifespan)


def _error_detail(
    error: str, message: str, setup_command: str | None = None
) -> dict[str, str]:
    detail = {"error": error, "message": message}
    if setup_command is not None:
        detail["setup_command"] = setup_command
    return detail


def _normalize_ask_model(model: str | None) -> str:
    # Swagger may send placeholder strings; normalize them to the service default.
    if model is None:
        return DEFAULT_ANSWER_MODEL

    normalized = model.strip()
    if normalized == "" or normalized.lower() == "string":
        return DEFAULT_ANSWER_MODEL

    return normalized


def _service_call(callback: Callable[[], T]) -> T:
    try:
        return callback()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error_detail("invalid_request", str(exc)),
        ) from exc
    except RuntimeError as exc:
        message = str(exc)
        if "OPENAI_API_KEY is not set" in message:
            raise HTTPException(
                status_code=503,
                detail=_error_detail(
                    "openai_api_key_missing",
                    message,
                    'export OPENAI_API_KEY="your_api_key"',
                ),
            ) from exc
        if "embed-chunks" in message:
            raise HTTPException(
                status_code=409,
                detail=_error_detail(
                    "chunk_embeddings_missing",
                    message,
                    "python3 main.py embed-chunks",
                ),
            ) from exc
        if "embed-queries" in message:
            raise HTTPException(
                status_code=409,
                detail=_error_detail(
                    "query_embeddings_missing",
                    message,
                    "python3 main.py embed-queries",
                ),
            ) from exc
        raise HTTPException(
            status_code=500,
            detail=_error_detail("service_error", message),
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=_error_detail("file_error", str(exc)),
        ) from exc


@app.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok", "app": "PrepLens"}


@app.get("/documents", response_model=DocumentsResponse)
def documents() -> dict[str, Any]:
    return _service_call(list_documents)


@app.get("/documents/{document_id}/chunks", response_model=DocumentChunksResponse)
def document_chunks(document_id: int) -> dict[str, Any]:
    report = _service_call(lambda: get_document_chunks(document_id))
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=_error_detail(
                "not_found",
                f"No document found with id {document_id}.",
            ),
        )
    return report


@app.post("/search/hybrid", response_model=SearchResponse)
def search_hybrid(request: HybridSearchRequest) -> dict[str, Any]:
    return _service_call(
        lambda: hybrid_chunk_search(
            request.query,
            alpha=request.alpha,
            limit=request.top_k,
        )
    )


@app.post("/search/feedback", response_model=FeedbackSearchResponse)
def search_feedback(request: FeedbackSearchRequest) -> dict[str, Any]:
    return _service_call(
        lambda: feedback_chunk_search(
            request.query,
            top_k=request.top_k,
            candidate_k=request.candidate_k,
            alpha=request.alpha,
            similarity_threshold=request.similarity_threshold,
            gamma=request.gamma,
        )
    )


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> dict[str, Any]:
    return _service_call(
        lambda: ask_question(
            request.question,
            top_k=request.top_k,
            alpha=request.alpha,
            model=_normalize_ask_model(request.model),
        )
    )


@app.get("/history", response_model=HistoryResponse)
def history(limit: int = Query(10, ge=1)) -> dict[str, Any]:
    return _service_call(lambda: list_query_history(limit=limit))


@app.get("/queries/{query_id}", response_model=QueryDetailsResponse)
def query_details(query_id: int) -> dict[str, Any]:
    report = _service_call(lambda: show_query_details(query_id))
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=_error_detail(
                "not_found",
                f"No saved query found with id {query_id}.",
            ),
        )
    return report


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> dict[str, Any]:
    report = _service_call(
        lambda: add_source_feedback(
            request.query_id,
            request.chunk_id,
            request.feedback_type,
            request.comment,
        )
    )
    return {"status": "saved", **report}


@app.get("/feedback/summary", response_model=FeedbackSummaryResponse)
def feedback_summary() -> dict[str, int]:
    return _service_call(get_feedback_summary_report)
