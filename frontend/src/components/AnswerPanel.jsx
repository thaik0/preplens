import React from "react";
import SourcesList from "./SourcesList";

export default function AnswerPanel({ result }) {
  if (!result) {
    return (
      <section className="empty-state">
        Ask a question to see a grounded answer and the source chunks PrepLens
        retrieved.
      </section>
    );
  }

  return (
    <section className="answer-panel">
      <div className="answer-header">
        <div>
          <h2>Answer</h2>
          <p>{result.question}</p>
        </div>
        <span>Query #{result.query_id ?? "unsaved"}</span>
      </div>

      <div className="answer-text">
        {result.answer || "No answer was generated for this question."}
      </div>

      <SourcesList sources={result.sources || []} queryId={result.query_id} />
    </section>
  );
}
