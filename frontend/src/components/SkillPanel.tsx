import { useState } from "react";
import type { FormEvent } from "react";

interface FieldDef {
  name: string;
  type: "text" | "textarea" | "url";
  label: string;
  required: boolean;
}

interface Skill {
  skill_key: string;
  scenario_name: string;
  description: string;
  input_schema: { fields: FieldDef[] };
}

interface Props {
  skill: Skill;
  onSubmit: (skillKey: string, inputData: Record<string, string>) => void;
  onClose: () => void;
}

export function SkillPanel({ skill, onSubmit, onClose }: Props) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const fields: FieldDef[] = skill.input_schema?.fields || [];

  function handleChange(name: string, value: string) {
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    onSubmit(skill.skill_key, values);
  }

  return (
    <div className="skill-panel">
      <div className="skill-panel-header">
        <div>
          <span className="skill-card-label">Skill</span>
          <span className="skill-panel-title">{skill.scenario_name}</span>
        </div>
        <button className="skill-panel-close" onClick={onClose} disabled={loading}>✕</button>
      </div>

      <p className="skill-panel-desc">{skill.description}</p>

      <form className="skill-panel-form" onSubmit={handleSubmit}>
        {fields.map((field) => (
          <div key={field.name} className="skill-field">
            <label className="skill-field-label">
              {field.label}
              {field.required && <span className="skill-required">*</span>}
            </label>
            {field.type === "textarea" ? (
              <textarea
                className="skill-textarea"
                placeholder={field.label}
                value={values[field.name] || ""}
                onChange={(e) => handleChange(field.name, e.target.value)}
                required={field.required}
                rows={4}
              />
            ) : (
              <input
                className="skill-input"
                type={field.type === "url" ? "url" : "text"}
                placeholder={field.label}
                value={values[field.name] || ""}
                onChange={(e) => handleChange(field.name, e.target.value)}
                required={field.required}
              />
            )}
          </div>
        ))}

        <button type="submit" className="skill-submit" disabled={loading}>
          {loading ? "Running…" : "Run Skill"}
        </button>
      </form>
    </div>
  );
}
