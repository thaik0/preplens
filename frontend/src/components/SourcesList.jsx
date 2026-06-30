import React from "react";
import FeedbackButtons from "./FeedbackButtons";

function formatScore(score) {
  if (typeof score !== "number") {
    return null;
  }
  return score.toFixed(3);
}

export default function SourcesList({ sources, queryId }) {
  if (!sources.length) {
    return <p className="muted">No sources were returned.</p>;
  }

  return (
    <section className="sources-section">
      <h3>Retrieved Sources</h3>
      <div className="source-list">
        {sources.map((source) => {
          const score = formatScore(source.hybrid_score);
          return (
            <article className="source-card" key={`${source.chunk_id}-${source.rank}`}>
              <div className="source-meta">
                <strong>
                  {source.rank ? `#${source.rank} ` : ""}
                  {source.document_name || "Unknown document"}
                </strong>
                <span>Chunk {source.chunk_index ?? source.chunk_id}</span>
              </div>

              <p>{source.preview || source.text || "No preview available."}</p>

              <div className="source-footer">
                {score && <span>Hybrid score {score}</span>}
                {source.was_cited && <span>Cited</span>}
                {source.feedback && <span>Feedback: {source.feedback}</span>}
              </div>

              <FeedbackButtons queryId={queryId} chunkId={source.chunk_id} />
            </article>
          );
        })}
      </div>
    </section>
  );
}
