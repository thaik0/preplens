"""Pydantic request and response models for the local PrepLens API."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str


class DocumentSummary(BaseModel):
    id: int
    filename: str
    file_type: str
    filepath: str
    chunk_count: int


class DocumentsResponse(BaseModel):
    documents: list[DocumentSummary]


class DocumentInfo(BaseModel):
    id: int
    filename: str
    filepath: str


class DocumentChunk(BaseModel):
    chunk_index: int
    text: str
    start_char: int
    end_char: int


class DocumentChunksResponse(BaseModel):
    document: DocumentInfo
    chunks: list[DocumentChunk]


class HybridSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1)
    alpha: float = Field(0.5, ge=0.0, le=1.0)


class FeedbackSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1)
    alpha: float = Field(0.5, ge=0.0, le=1.0)
    candidate_k: int = Field(20, ge=1)
    similarity_threshold: float = Field(0.65, ge=0.0, le=1.0)
    gamma: float = Field(0.2, ge=0.0)


class SearchResponse(BaseModel):
    query: str
    method: str
    results: list[dict[str, Any]]


class FeedbackSearchResponse(SearchResponse):
    alpha: float
    top_k: int
    candidate_k: int
    similarity_threshold: float
    gamma: float
    model: str
    diagnostics: dict[str, Any]


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1)
    alpha: float = Field(0.5, ge=0.0, le=1.0)
    model: str | None = None


class AskResponse(BaseModel):
    query_id: int | None
    question: str
    answer: str
    sources: list[dict[str, Any]]


class HistoryResponse(BaseModel):
    queries: list[dict[str, Any]]


class QueryDetailsResponse(BaseModel):
    query: dict[str, Any]
    retrieved_chunks: list[dict[str, Any]]


class FeedbackRequest(BaseModel):
    query_id: int = Field(..., ge=1)
    chunk_id: int = Field(..., ge=1)
    feedback_type: Literal["helpful", "not_helpful", "wrong_source"]
    comment: str | None = None


class FeedbackResponse(BaseModel):
    status: str
    feedback_id: int
    query_id: int
    chunk_id: int
    feedback_type: str
    comment: str | None = None


class FeedbackSummaryResponse(BaseModel):
    total_feedback: int
    helpful_count: int
    not_helpful_count: int
    wrong_source_count: int


class ErrorDetail(BaseModel):
    error: str
    message: str
    setup_command: str | None = None
