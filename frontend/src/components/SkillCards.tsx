import { useEffect, useState } from "react";
import { fetchSkills } from "../services/api";

interface Skill {
  skill_key: string;
  scenario_name: string;
  tagline: string | null;
  description: string;
}

interface Props {
  onSelect: (skill: Skill) => void;
}

const MAX_VISIBLE = 6;

export function SkillCards({ onSelect }: Props) {
  const [skills, setSkills] = useState<Skill[]>([]);

  useEffect(() => {
    fetchSkills().then(setSkills).catch(() => {});
  }, []);

  if (skills.length === 0) return null;

  return (
    <div className="skill-cards">
      {skills.slice(0, MAX_VISIBLE).map((skill) => (
        <button
          key={skill.skill_key}
          className="skill-card"
          onClick={() => onSelect(skill)}
        >
          <span className="skill-card-name">{skill.scenario_name}</span>
          {skill.tagline && (
            <span className="skill-card-tagline">{skill.tagline}</span>
          )}
        </button>
      ))}
    </div>
  );
}
