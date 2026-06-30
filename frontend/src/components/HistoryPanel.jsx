import React from "react";

export default function HistoryPanel({
  history,
  isLoading,
  onSelect,
  selectedQueryId,
}) {
  return (
    <aside className="history-panel">
      <div className="history-heading">
        <h2>Recent History</h2>
        {isLoading && <span>Loading...</span>}
      </div>

      {!history.length && !isLoading && (
        <p className="muted">No saved questions yet.</p>
      )}

      <div className="history-list">
        {history.map((item) => (
          <button
            className={item.id === selectedQueryId ? "history-item active" : "history-item"}
            key={item.id}
            type="button"
            onClick={() => onSelect(item.id)}
          >
            <span>#{item.id}</span>
            <strong>{item.preview || item.query_text}</strong>
            <small>{item.created_at}</small>
          </button>
        ))}
      </div>
    </aside>
  );
}
