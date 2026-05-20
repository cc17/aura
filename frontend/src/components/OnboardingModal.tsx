import { useState } from "react";
import { submitOnboarding } from "../services/api";
import { INDUSTRY_CONFIG, getRolesForIndustry, getPainPointsForIndustry } from "../config/industries";

interface Props {
  onComplete: () => void;
}

const AI_LEVELS = [
  { value: "Beginner", label: "Beginner (just getting started)" },
  { value: "Intermediate", label: "Intermediate (1–6 months)" },
  { value: "Advanced", label: "Advanced (6+ months)" },
];

export function OnboardingModal({ onComplete }: Props) {
  const [step, setStep] = useState(0);
  const [industry, setIndustry] = useState("");
  const [role, setRole] = useState("");
  const [painPoints, setPainPoints] = useState<string[]>([]);
  const [aiProficiency, setAiProficiency] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleSelectIndustry(ind: string) {
    setIndustry(ind);
    setRole("");
    setPainPoints([]);
  }

  function togglePainPoint(p: string) {
    setPainPoints((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  }

  async function handleFinish() {
    if (!aiProficiency) return;
    setLoading(true);
    setError("");
    try {
      await submitOnboarding({
        industry,
        role,
        pain_points: painPoints,
        ai_proficiency: aiProficiency,
      });
      onComplete();
    } catch {
      setError("Failed to save, please try again");
    } finally {
      setLoading(false);
    }
  }

  const availableRoles = getRolesForIndustry(industry);
  const availablePainPoints = getPainPointsForIndustry(industry);

  return (
    <div className="modal-overlay">
      <div className="modal-card">
        <div className="modal-progress">
          {[0, 1, 2].map((i) => (
            <div key={i} className={`progress-dot ${i <= step ? "active" : ""}`} />
          ))}
        </div>

        {step === 0 && (
          <div className="modal-step">
            <h2 className="modal-title">What do you do?</h2>
            <p className="modal-sub">Help me understand your work context</p>

            <div className="option-group">
              <p className="option-label">Industry</p>
              <div className="industry-cards">
                {INDUSTRY_CONFIG.map((ind) => (
                  <button
                    key={ind.name}
                    className={`industry-card ${industry === ind.name ? "selected" : ""}`}
                    onClick={() => handleSelectIndustry(ind.name)}
                  >
                    <span className="industry-card-emoji">{ind.emoji}</span>
                    <span className="industry-card-name">{ind.name}</span>
                  </button>
                ))}
              </div>
            </div>

            {industry && (
              <div className="option-group">
                <p className="option-label">Your role</p>
                <div className="option-chips">
                  {availableRoles.map((r) => (
                    <button
                      key={r}
                      className={`chip ${role === r ? "selected" : ""}`}
                      onClick={() => setRole(r)}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <button
              className="modal-next"
              disabled={!industry || !role}
              onClick={() => setStep(1)}
            >
              Next
            </button>
          </div>
        )}

        {step === 1 && (
          <div className="modal-step">
            <h2 className="modal-title">What would you like help with most?</h2>
            <p className="modal-sub">Select all that apply — you can change these later</p>
            <div className="option-chips">
              {availablePainPoints.map((p) => (
                <button
                  key={p}
                  className={`chip ${painPoints.includes(p) ? "selected" : ""}`}
                  onClick={() => togglePainPoint(p)}
                >
                  {p}
                </button>
              ))}
            </div>
            <div className="modal-nav">
              <button className="modal-back" onClick={() => setStep(0)}>Back</button>
              <button
                className="modal-next"
                disabled={painPoints.length === 0}
                onClick={() => setStep(2)}
              >
                Next
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="modal-step">
            <h2 className="modal-title">How long have you been using AI?</h2>
            <p className="modal-sub">This helps me calibrate my responses</p>
            <div className="option-list">
              {AI_LEVELS.map((lv) => (
                <button
                  key={lv.value}
                  className={`option-item ${aiProficiency === lv.value ? "selected" : ""}`}
                  onClick={() => setAiProficiency(lv.value)}
                >
                  {lv.label}
                </button>
              ))}
            </div>
            {error && <div className="auth-error">{error}</div>}
            <div className="modal-nav">
              <button className="modal-back" onClick={() => setStep(1)}>Back</button>
              <button
                className="modal-next"
                disabled={!aiProficiency || loading}
                onClick={handleFinish}
              >
                {loading ? "Saving…" : "Get started"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
