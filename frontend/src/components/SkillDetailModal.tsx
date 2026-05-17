import { useState } from "react";
import type { MarketSkill } from "../services/api";

interface Props {
  skill: MarketSkill;
  onAdd: (skillKey: string) => Promise<void>;
  onRemove: (skillKey: string) => Promise<void>;
  onClose: () => void;
}

export function SkillDetailModal({ skill, onAdd, onRemove, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [added, setAdded] = useState(skill.is_added);

  const fields = skill.input_schema?.fields ?? [];

  const handleToggle = async () => {
    setLoading(true);
    try {
      if (added) {
        await onRemove(skill.skill_key);
        setAdded(false);
      } else {
        await onAdd(skill.skill_key);
        setAdded(true);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="skill-detail-modal" onClick={(e) => e.stopPropagation()}>
        <button className="skill-detail-close" onClick={onClose} title="关闭">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
        </button>

        <div className="skill-detail-header">
          <h2 className="skill-detail-name">{skill.scenario_name}</h2>
          {skill.tagline && <p className="skill-detail-tagline">{skill.tagline}</p>}
          <div className="skill-detail-tags">
            {skill.industry && <span className="skill-tag">{skill.industry}</span>}
            {skill.role && <span className="skill-tag">{skill.role}</span>}
          </div>
        </div>

        <p className="skill-detail-desc">{skill.description}</p>

        {fields.length > 0 && (
          <div className="skill-detail-fields">
            <div className="skill-detail-fields-title">需要填写</div>
            <ul className="skill-detail-fields-list">
              {fields.map((f) => (
                <li key={f.name}>
                  <span className="skill-field-name">{f.label}</span>
                  {f.required && <span className="skill-field-required">必填</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        <button
          className={`skill-detail-btn ${added ? "skill-detail-btn--added" : ""}`}
          onClick={handleToggle}
          disabled={loading}
        >
          {loading ? "处理中…" : added ? "✓ 已添加  点击移除" : "+ 添加到我的技能"}
        </button>
      </div>
    </div>
  );
}
