import { useEffect, useState } from "react";
import { fetchMemories, fetchProfile, deleteMemory, patchProfile } from "../services/api";
import { INDUSTRY_CONFIG, getRolesForIndustry } from "../config/industries";

interface Memory {
  id: number;
  content: string;
  category: string;
  importance: number;
  created_at: string;
}

interface ProfileField {
  value?: string;
  confidence?: number;
}

type ProfileData = Record<string, string | string[] | ProfileField>;

const CATEGORY_LABEL: Record<string, string> = {
  fact: "Fact",
  preference: "Preference",
  goal: "Goal",
  context: "Context",
};

const AI_PROFICIENCY_OPTIONS = ["Beginner", "Intermediate", "Advanced"];

interface Props {
  onClose: () => void;
}

export function ProfilePage({ onClose }: Props) {
  const [profile, setProfile] = useState<ProfileData>({});
  const [memories, setMemories] = useState<Memory[]>([]);
  const [tab, setTab] = useState<"profile" | "memories">("profile");
  const [saving, setSaving] = useState(false);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  useEffect(() => {
    fetchProfile().then((d) => setProfile(d.profile || {})).catch(() => {});
    fetchMemories().then((d) => setMemories(d.memories || [])).catch(() => {});
  }, []);

  function fieldDisplay(key: string): string {
    const v = profile[key];
    if (!v) return "—";
    if (Array.isArray(v)) return v.join(", ");
    if (typeof v === "object" && "value" in v) return (v as ProfileField).value || "—";
    return String(v);
  }

  function fieldConfidence(key: string): number {
    const v = profile[key];
    if (typeof v === "object" && !Array.isArray(v) && "confidence" in v) {
      return (v as ProfileField).confidence ?? 1;
    }
    return 1;
  }

  async function saveField(key: string, value: string) {
    setSaving(true);
    try {
      const updated = await patchProfile({ [key]: value });
      setProfile(updated.profile || {});
    } finally {
      setSaving(false);
      setEditingKey(null);
    }
  }

  async function handleDeleteMemory(id: number) {
    await deleteMemory(id);
    setMemories((prev) => prev.filter((m) => m.id !== id));
  }

  const currentIndustry = fieldDisplay("industry") === "—" ? "" : fieldDisplay("industry");
  const editingIndustry = editingKey === "industry" ? editValue : currentIndustry;
  const availableRoles = getRolesForIndustry(editingIndustry);

  return (
    <div className="profile-overlay" onClick={onClose}>
      <div className="profile-modal" onClick={(e) => e.stopPropagation()}>
        <div className="profile-header">
          <h2 className="profile-title">My Profile</h2>
          <button className="profile-close" onClick={onClose}>✕</button>
        </div>

        <div className="profile-tabs">
          <button
            className={`profile-tab ${tab === "profile" ? "active" : ""}`}
            onClick={() => setTab("profile")}
          >
            Profile
          </button>
          <button
            className={`profile-tab ${tab === "memories" ? "active" : ""}`}
            onClick={() => setTab("memories")}
          >
            Memory ({memories.length})
          </button>
        </div>

        {tab === "profile" && (
          <div className="profile-body">
            <p className="profile-desc">What Aura knows about you. Higher confidence = more reliable. Manually edited fields are set to 100%.</p>

            <div className="profile-field">
              <div className="profile-field-meta">
                <span className="profile-field-label">Industry</span>
                <span className="profile-confidence">
                  {Math.round(fieldConfidence("industry") * 100)}%
                </span>
              </div>
              {editingKey === "industry" ? (
                <div className="profile-field-edit">
                  <div className="profile-chip-selector">
                    {INDUSTRY_CONFIG.map((ind) => (
                      <button
                        key={ind.name}
                        className={`chip ${editValue === ind.name ? "selected" : ""}`}
                        onClick={() => setEditValue(ind.name)}
                      >
                        {ind.emoji} {ind.name}
                      </button>
                    ))}
                  </div>
                  <div className="profile-chip-actions">
                    <button
                      className="profile-save-btn"
                      onClick={() => saveField("industry", editValue)}
                      disabled={saving || !editValue}
                    >
                      Save
                    </button>
                    <button className="profile-cancel-btn" onClick={() => setEditingKey(null)}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="profile-field-value">
                  <span>{fieldDisplay("industry")}</span>
                  <button
                    className="profile-edit-btn"
                    onClick={() => {
                      setEditingKey("industry");
                      setEditValue(currentIndustry);
                    }}
                  >
                    Edit
                  </button>
                </div>
              )}
            </div>

            <div className="profile-field">
              <div className="profile-field-meta">
                <span className="profile-field-label">Role</span>
                <span className="profile-confidence">
                  {Math.round(fieldConfidence("role") * 100)}%
                </span>
              </div>
              {editingKey === "role" ? (
                <div className="profile-field-edit">
                  {availableRoles.length > 0 ? (
                    <div className="profile-chip-selector">
                      {availableRoles.map((r) => (
                        <button
                          key={r}
                          className={`chip ${editValue === r ? "selected" : ""}`}
                          onClick={() => setEditValue(r)}
                        >
                          {r}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <input
                      className="profile-edit-input"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") saveField("role", editValue);
                        if (e.key === "Escape") setEditingKey(null);
                      }}
                      placeholder="Enter your role"
                      autoFocus
                    />
                  )}
                  <div className="profile-chip-actions">
                    <button
                      className="profile-save-btn"
                      onClick={() => saveField("role", editValue)}
                      disabled={saving || !editValue}
                    >
                      Save
                    </button>
                    <button className="profile-cancel-btn" onClick={() => setEditingKey(null)}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="profile-field-value">
                  <span>{fieldDisplay("role")}</span>
                  <button
                    className="profile-edit-btn"
                    onClick={() => {
                      setEditingKey("role");
                      const cur = fieldDisplay("role");
                      setEditValue(cur === "—" ? "" : cur);
                    }}
                  >
                    Edit
                  </button>
                </div>
              )}
            </div>

            <div className="profile-field">
              <div className="profile-field-meta">
                <span className="profile-field-label">AI Proficiency</span>
                <span className="profile-confidence">
                  {Math.round(fieldConfidence("ai_proficiency") * 100)}%
                </span>
              </div>
              {editingKey === "ai_proficiency" ? (
                <div className="profile-field-edit">
                  <div className="profile-chip-selector">
                    {AI_PROFICIENCY_OPTIONS.map((opt) => (
                      <button
                        key={opt}
                        className={`chip ${editValue === opt ? "selected" : ""}`}
                        onClick={() => setEditValue(opt)}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                  <div className="profile-chip-actions">
                    <button
                      className="profile-save-btn"
                      onClick={() => saveField("ai_proficiency", editValue)}
                      disabled={saving || !editValue}
                    >
                      Save
                    </button>
                    <button className="profile-cancel-btn" onClick={() => setEditingKey(null)}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="profile-field-value">
                  <span>{fieldDisplay("ai_proficiency")}</span>
                  <button
                    className="profile-edit-btn"
                    onClick={() => {
                      setEditingKey("ai_proficiency");
                      const cur = fieldDisplay("ai_proficiency");
                      setEditValue(cur === "—" ? "" : cur);
                    }}
                  >
                    Edit
                  </button>
                </div>
              )}
            </div>

            <div className="profile-field">
              <div className="profile-field-meta">
                <span className="profile-field-label">Pain Points</span>
                <span className="profile-confidence">
                  {Math.round(fieldConfidence("pain_points") * 100)}%
                </span>
              </div>
              {editingKey === "pain_points" ? (
                <div className="profile-field-edit">
                  <input
                    className="profile-edit-input"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") saveField("pain_points", editValue);
                      if (e.key === "Escape") setEditingKey(null);
                    }}
                    placeholder="Separate multiple items with commas"
                    autoFocus
                  />
                  <button
                    className="profile-save-btn"
                    onClick={() => saveField("pain_points", editValue)}
                    disabled={saving}
                  >
                    Save
                  </button>
                  <button className="profile-cancel-btn" onClick={() => setEditingKey(null)}>
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="profile-field-value">
                  <span>{fieldDisplay("pain_points")}</span>
                  <button
                    className="profile-edit-btn"
                    onClick={() => {
                      setEditingKey("pain_points");
                      const cur = fieldDisplay("pain_points");
                      setEditValue(cur === "—" ? "" : cur);
                    }}
                  >
                    Edit
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {tab === "memories" && (
          <div className="profile-body">
            {memories.length === 0 ? (
              <p className="profile-empty">No memories yet — keep chatting and they'll appear.</p>
            ) : (
              <div className="memories-list">
                {memories.map((m) => (
                  <div key={m.id} className="memory-item">
                    <div className="memory-meta">
                      <span className="memory-category">
                        {CATEGORY_LABEL[m.category] ?? m.category}
                      </span>
                      <span className="memory-importance">Importance {m.importance}</span>
                    </div>
                    <div className="memory-content-row">
                      <span className="memory-text">{m.content}</span>
                      <button
                        className="memory-delete"
                        onClick={() => handleDeleteMemory(m.id)}
                        title="Delete memory"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
