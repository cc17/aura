import { useState } from "react";
import { apiFetch } from "../services/api";

export function FeedbackButton() {
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);

  async function handleSubmit() {
    if (rating === 0) return;
    setSending(true);
    try {
      await apiFetch("/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, comment, context: "general" }),
      });
      setSent(true);
      setTimeout(() => {
        setOpen(false);
        setSent(false);
        setRating(0);
        setComment("");
      }, 1500);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button
        className="feedback-fab"
        onClick={() => setOpen(true)}
        title="Send feedback"
      >
        💬
      </button>

      {open && (
        <div className="feedback-overlay" onClick={() => setOpen(false)}>
          <div className="feedback-modal" onClick={(e) => e.stopPropagation()}>
            <div className="feedback-header">
              <span className="feedback-title">Feedback</span>
              <button className="feedback-close" onClick={() => setOpen(false)}>✕</button>
            </div>

            {sent ? (
              <p className="feedback-sent">Thanks for your feedback! 🎉</p>
            ) : (
              <>
                <p className="feedback-label">How was your experience?</p>
                <div className="feedback-stars">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      className={`feedback-star ${n <= rating ? "active" : ""}`}
                      onClick={() => setRating(n)}
                    >
                      ★
                    </button>
                  ))}
                </div>

                <textarea
                  className="feedback-textarea"
                  placeholder="Anything else? (optional)"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={3}
                />

                <button
                  className="feedback-submit"
                  onClick={handleSubmit}
                  disabled={rating === 0 || sending}
                >
                  {sending ? "Submitting…" : "Submit"}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
