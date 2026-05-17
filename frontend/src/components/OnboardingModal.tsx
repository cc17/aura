import { useState } from "react";
import { submitOnboarding } from "../services/api";
import { INDUSTRY_CONFIG, getRolesForIndustry, getPainPointsForIndustry } from "../config/industries";

interface Props {
  onComplete: () => void;
}

const AI_LEVELS = [
  { value: "新手", label: "新手（刚开始用 AI）" },
  { value: "入门", label: "入门（用了 1-6 个月）" },
  { value: "熟练", label: "熟练（用了半年以上）" },
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
      setError("提交失败，请重试");
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
            <h2 className="modal-title">你是做什么工作的？</h2>
            <p className="modal-sub">帮我更好地理解你的工作场景</p>

            <div className="option-group">
              <p className="option-label">所在行业</p>
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
                <p className="option-label">你的岗位</p>
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
              下一步
            </button>
          </div>
        )}

        {step === 1 && (
          <div className="modal-step">
            <h2 className="modal-title">你最希望我帮你解决？</h2>
            <p className="modal-sub">可多选，之后随时可以修改</p>
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
              <button className="modal-back" onClick={() => setStep(0)}>上一步</button>
              <button
                className="modal-next"
                disabled={painPoints.length === 0}
                onClick={() => setStep(2)}
              >
                下一步
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="modal-step">
            <h2 className="modal-title">你用 AI 多久了？</h2>
            <p className="modal-sub">方便我调整回答的深度</p>
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
              <button className="modal-back" onClick={() => setStep(1)}>上一步</button>
              <button
                className="modal-next"
                disabled={!aiProficiency || loading}
                onClick={handleFinish}
              >
                {loading ? "保存中…" : "开始使用"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
