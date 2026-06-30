const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let body = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    body = await response.json();
  }

  if (!response.ok) {
    const detail = body?.detail;
    const message = detail?.message || detail?.error || response.statusText;
    throw new Error(message);
  }

  return body;
}

export function askQuestion(question, options = {}) {
  return request("/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      top_k: options.top_k ?? 5,
      alpha: options.alpha ?? 0.5,
      model: options.model ?? null,
    }),
  });
}

export function submitFeedback(queryId, chunkId, feedbackType, comment = "") {
  return request("/feedback", {
    method: "POST",
    body: JSON.stringify({
      query_id: queryId,
      chunk_id: chunkId,
      feedback_type: feedbackType,
      comment,
    }),
  });
}

export function getHistory(limit = 10) {
  return request(`/history?limit=${encodeURIComponent(limit)}`);
}

export function getQueryDetail(queryId) {
  return request(`/queries/${encodeURIComponent(queryId)}`);
}

export function getHealth() {
  return request("/health");
}
