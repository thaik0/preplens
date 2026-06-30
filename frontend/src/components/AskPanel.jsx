import React, { useState } from "react";

export default function AskPanel({ onAsk, isLoading }) {
  const [question, setQuestion] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isLoading) {
      return;
    }
    onAsk(trimmed);
  }

  return (
    <form className="ask-panel" onSubmit={handleSubmit}>
      <label htmlFor="question">Question</label>
      <textarea
        id="question"
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="How do I detect a cycle in a linked list?"
        rows={4}
      />
      <button type="submit" disabled={isLoading || !question.trim()}>
        {isLoading ? "Asking..." : "Ask"}
      </button>
    </form>
  );
}
