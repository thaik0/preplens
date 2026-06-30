"""SQLAlchemy Core table metadata matching the current SQLite schema.

PrepLens intentionally uses SQLAlchemy Core rather than the ORM at this stage.
The tables below mirror the existing SQLite schema without adding migrations or
new database objects.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    text,
)


metadata = MetaData()

documents = Table(
    "documents",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("filename", Text, nullable=False),
    Column("filepath", Text, nullable=False),
    Column("file_type", Text, nullable=False),
    Column("created_at", Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    sqlite_autoincrement=True,
)

chunks = Table(
    "chunks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("document_id", Integer, ForeignKey("documents.id"), nullable=False),
    Column("chunk_index", Integer, nullable=False),
    Column("text", Text, nullable=False),
    Column("start_char", Integer, nullable=False),
    Column("end_char", Integer, nullable=False),
    sqlite_autoincrement=True,
)

chunk_embeddings = Table(
    "chunk_embeddings",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("chunk_id", Integer, ForeignKey("chunks.id"), nullable=False),
    Column("model", Text, nullable=False),
    Column("embedding_json", Text, nullable=False),
    Column("created_at", Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("chunk_id", "model"),
    sqlite_autoincrement=True,
)

queries = Table(
    "queries",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("query_text", Text, nullable=False),
    Column("retrieval_method", Text, nullable=False),
    Column("alpha", Float, nullable=False),
    Column("top_k", Integer, nullable=False),
    Column("model", Text, nullable=False),
    Column("created_at", Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    sqlite_autoincrement=True,
)

query_embeddings = Table(
    "query_embeddings",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("query_id", Integer, ForeignKey("queries.id"), nullable=False),
    Column("model", Text, nullable=False),
    Column("embedding_json", Text, nullable=False),
    Column("created_at", Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("query_id", "model"),
    sqlite_autoincrement=True,
)

answers = Table(
    "answers",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("query_id", Integer, ForeignKey("queries.id"), nullable=False, unique=True),
    Column("answer_text", Text, nullable=False),
    Column("created_at", Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    sqlite_autoincrement=True,
)

retrieval_results = Table(
    "retrieval_results",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("query_id", Integer, ForeignKey("queries.id"), nullable=False),
    Column("chunk_id", Integer, ForeignKey("chunks.id"), nullable=False),
    Column("rank", Integer, nullable=False),
    Column("keyword_score", Float, nullable=False),
    Column("normalized_keyword_score", Float, nullable=False),
    Column("semantic_score", Float, nullable=False),
    Column("normalized_semantic_score", Float, nullable=False),
    Column("hybrid_score", Float, nullable=False),
    Column("was_cited", Integer, nullable=False),
    CheckConstraint("was_cited IN (0, 1)"),
    sqlite_autoincrement=True,
)

feedback = Table(
    "feedback",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("query_id", Integer, ForeignKey("queries.id"), nullable=False),
    Column("chunk_id", Integer, ForeignKey("chunks.id"), nullable=False),
    Column("feedback_type", Text, nullable=False),
    Column("comment", Text),
    Column("created_at", Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    CheckConstraint("feedback_type IN ('helpful', 'not_helpful', 'wrong_source')"),
    sqlite_autoincrement=True,
)
