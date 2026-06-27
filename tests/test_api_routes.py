from fastapi.testclient import TestClient

import src.api.app as api_app


client = TestClient(api_app.app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "PrepLens"}


def test_documents_returns_structured_json(monkeypatch) -> None:
    monkeypatch.setattr(
        api_app,
        "list_documents",
        lambda: {
            "documents": [
                {
                    "id": 1,
                    "filename": "dynamic_programming.md",
                    "file_type": ".md",
                    "filepath": "notes/dynamic_programming.md",
                    "chunk_count": 2,
                }
            ]
        },
    )

    response = client.get("/documents")

    assert response.status_code == 200
    body = response.json()
    assert "documents" in body
    assert body["documents"][0]["filename"] == "dynamic_programming.md"
    assert body["documents"][0]["chunk_count"] == 2


def test_feedback_summary_returns_structured_json(monkeypatch) -> None:
    monkeypatch.setattr(
        api_app,
        "get_feedback_summary_report",
        lambda: {
            "total_feedback": 3,
            "helpful_count": 1,
            "not_helpful_count": 1,
            "wrong_source_count": 1,
        },
    )

    response = client.get("/feedback/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_feedback": 3,
        "helpful_count": 1,
        "not_helpful_count": 1,
        "wrong_source_count": 1,
    }


def test_history_returns_structured_json(monkeypatch) -> None:
    monkeypatch.setattr(
        api_app,
        "list_query_history",
        lambda limit=10: {
            "queries": [
                {
                    "id": 7,
                    "query_text": "what is dynamic programming?",
                    "retrieval_method": "hybrid",
                    "model": "gpt-4o-mini",
                    "created_at": "2026-06-27 10:00:00",
                    "preview": "what is dynamic programming?",
                }
            ]
        },
    )

    response = client.get("/history")

    assert response.status_code == 200
    body = response.json()
    assert "queries" in body
    assert body["queries"][0]["id"] == 7
    assert body["queries"][0]["retrieval_method"] == "hybrid"


def test_feedback_rejects_invalid_feedback_type() -> None:
    response = client.post(
        "/feedback",
        json={"query_id": 1, "chunk_id": 1, "feedback_type": "irrelevant"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_ask_requires_question() -> None:
    response = client.post("/ask", json={"top_k": 5, "alpha": 0.5})

    assert response.status_code == 422
    assert "detail" in response.json()


def test_hybrid_search_requires_query() -> None:
    response = client.post("/search/hybrid", json={"top_k": 5, "alpha": 0.5})

    assert response.status_code == 422
    assert "detail" in response.json()


def test_document_chunks_returns_404_when_document_missing(monkeypatch) -> None:
    monkeypatch.setattr(api_app, "get_document_chunks", lambda document_id: None)

    response = client.get("/documents/999999/chunks")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "not_found"


def test_query_details_returns_404_when_query_missing(monkeypatch) -> None:
    monkeypatch.setattr(api_app, "show_query_details", lambda query_id: None)

    response = client.get("/queries/999999")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "not_found"


def test_ask_returns_monkeypatched_service_response(monkeypatch) -> None:
    def fake_ask_question(question, top_k=5, alpha=0.5, model=None):
        return {
            "query_id": 123,
            "question": question,
            "answer": "Dynamic programming is ... [chunk 1]",
            "sources": [
                {
                    "rank": 1,
                    "chunk_id": 1,
                    "document_name": "dynamic_programming.md",
                    "chunk_index": 0,
                    "hybrid_score": 0.93,
                    "preview": "Dynamic programming stores overlapping subproblems.",
                }
            ],
        }

    monkeypatch.setattr(api_app, "ask_question", fake_ask_question)

    response = client.post(
        "/ask",
        json={"question": "what is dynamic programming?", "top_k": 1, "alpha": 0.7},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query_id"] == 123
    assert body["question"] == "what is dynamic programming?"
    assert body["answer"] == "Dynamic programming is ... [chunk 1]"
    assert body["sources"][0]["chunk_id"] == 1


def test_hybrid_search_returns_monkeypatched_service_response(monkeypatch) -> None:
    def fake_hybrid_chunk_search(query, alpha=0.5, limit=5):
        return {
            "query": query,
            "method": "hybrid",
            "results": [
                {
                    "rank": 1,
                    "chunk_id": 4,
                    "document_name": "linked_lists.md",
                    "chunk_index": 2,
                    "hybrid_score": 0.88,
                    "preview": "Use slow and fast pointers to detect a cycle.",
                }
            ],
        }

    monkeypatch.setattr(api_app, "hybrid_chunk_search", fake_hybrid_chunk_search)

    response = client.post(
        "/search/hybrid",
        json={"query": "cycle detection", "top_k": 1, "alpha": 0.6},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "cycle detection"
    assert body["method"] == "hybrid"
    assert body["results"][0]["chunk_id"] == 4


def test_feedback_returns_monkeypatched_service_response(monkeypatch) -> None:
    def fake_add_source_feedback(query_id, chunk_id, feedback_type, comment=None):
        return {
            "feedback_id": 55,
            "query_id": query_id,
            "chunk_id": chunk_id,
            "feedback_type": feedback_type,
            "comment": comment,
        }

    monkeypatch.setattr(api_app, "add_source_feedback", fake_add_source_feedback)

    response = client.post(
        "/feedback",
        json={
            "query_id": 123,
            "chunk_id": 1,
            "feedback_type": "helpful",
            "comment": "Good source.",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "saved",
        "feedback_id": 55,
        "query_id": 123,
        "chunk_id": 1,
        "feedback_type": "helpful",
        "comment": "Good source.",
    }
