import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  askQuestion,
  getHealth,
  getHistory,
  getQueryDetail,
} from "./api";
import AnswerPanel from "./components/AnswerPanel";
import AskPanel from "./components/AskPanel";
import HistoryPanel from "./components/HistoryPanel";
import "./App.css";

function normalizeQueryDetail(detail) {
  return {
    query_id: detail.query.id,
    question: detail.query.query_text,
    answer: detail.query.answer_text,
    sources: detail.retrieved_chunks,
    created_at: detail.query.created_at,
  };
}

function App() {
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [health, setHealth] = useState("checking");
  const [isAsking, setIsAsking] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState("");

  async function refreshHistory() {
    setIsLoadingHistory(true);
    try {
      const data = await getHistory(10);
      setHistory(data.queries || []);
    } catch (err) {
      setError(err.message || "Could not load recent history.");
    } finally {
      setIsLoadingHistory(false);
    }
  }

  useEffect(() => {
    getHealth()
      .then(() => setHealth("online"))
      .catch(() => setHealth("offline"));
    refreshHistory();
  }, []);

  async function handleAsk(question) {
    setIsAsking(true);
    setError("");
    try {
      const data = await askQuestion(question, {
        top_k: 5,
        alpha: 0.5,
        model: null,
      });
      setResult(data);
      await refreshHistory();
    } catch (err) {
      setError(err.message || "Could not ask PrepLens.");
    } finally {
      setIsAsking(false);
    }
  }

  async function handleSelectHistory(queryId) {
    setError("");
    try {
      const detail = await getQueryDetail(queryId);
      setResult(normalizeQueryDetail(detail));
    } catch (err) {
      setError(err.message || "Could not load that query.");
    }
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <h1>PrepLens</h1>
          <p>
            A local, source-grounded interview prep assistant for asking your
            study notes questions and checking the retrieved evidence.
          </p>
        </div>
        <span className={`status-pill status-${health}`}>API {health}</span>
      </section>

      <div className="app-layout">
        <section className="workspace">
          <AskPanel onAsk={handleAsk} isLoading={isAsking} />

          {error && <div className="error-banner">{error}</div>}
          {isAsking && <div className="loading-banner">Retrieving sources and drafting an answer...</div>}

          <AnswerPanel result={result} />
        </section>

        <HistoryPanel
          history={history}
          isLoading={isLoadingHistory}
          onSelect={handleSelectHistory}
          selectedQueryId={result?.query_id}
        />
      </div>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
