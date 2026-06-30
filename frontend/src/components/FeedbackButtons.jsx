import React, { useState } from "react";
import { submitFeedback } from "../api";

const FEEDBACK_OPTIONS = [
  { label: "Helpful", value: "helpful" },
  { label: "Not helpful", value: "not_helpful" },
  { label: "Wrong source", value: "wrong_source" },
];

export default function FeedbackButtons({ queryId, chunkId }) {
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleFeedback(feedbackType) {
    if (!queryId || !chunkId || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setStatus("");
    try {
      await submitFeedback(queryId, chunkId, feedbackType, "");
      setStatus("Saved");
    } catch (err) {
      setStatus(err.message || "Could not save feedback");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="feedback-row">
      {FEEDBACK_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => handleFeedback(option.value)}
          disabled={!queryId || isSubmitting}
        >
          {option.label}
        </button>
      ))}
      {status && <span>{status}</span>}
    </div>
  );
}
