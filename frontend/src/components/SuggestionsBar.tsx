import { useEffect, useState } from "react";
import { fetchLatestSuggestions } from "../services/api";

interface Suggestion {
  type: "question" | "skill";
  text: string;
  skill_key: string | null;
}

interface Props {
  /** Refreshes suggestions when this key changes (e.g. pass last assistant message id). */
  refreshKey: string | null;
  onSendQuestion: (text: string) => void;
  onOpenSkill: (skillKey: string) => void;
}

export function SuggestionsBar({ refreshKey, onSendQuestion, onOpenSkill }: Props) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [lastKey, setLastKey] = useState<string | null>(null);

  useEffect(() => {
    if (!refreshKey || refreshKey === lastKey) return;

    // Poll up to 3 times (suggestions arrive async ~1-3s after response)
    let attempts = 0;
    const poll = async () => {
      try {
        const data = await fetchLatestSuggestions();
        if (data.message_id === refreshKey && data.suggestions.length > 0) {
          setSuggestions(data.suggestions);
          setLastKey(refreshKey);
          return;
        }
      } catch { /* ignore */ }

      attempts++;
      if (attempts < 4) setTimeout(poll, 1500);
    };

    // Small delay to let the background task finish
    const t = setTimeout(poll, 1000);
    return () => clearTimeout(t);
  }, [refreshKey, lastKey]);

  if (suggestions.length === 0) return null;

  return (
    <div className="suggestions-bar">
      <span className="suggestions-label">💡 你可能还想…</span>
      <div className="suggestions-list">
        {suggestions.map((s, i) => (
          <button
            key={i}
            className={`suggestion-chip suggestion-chip--${s.type}`}
            onClick={() => {
              if (s.type === "skill" && s.skill_key) {
                onOpenSkill(s.skill_key);
              } else {
                onSendQuestion(s.text);
              }
            }}
          >
            {s.type === "skill" && <span className="suggestion-skill-dot" />}
            {s.text}
          </button>
        ))}
      </div>
    </div>
  );
}
