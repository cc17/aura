import { useEffect, useState } from "react";
import { fetchMySkills, fetchSkills, fetchProfile } from "../services/api";
import type { MySkill, SkillDef } from "../services/api";
import { getRelevantAgents } from "../config/agents";
import type { AgentEntry } from "../config/agents";

interface Props {
  onSelectSkill: (skillKey: string) => void;
  onSendMessage: (text: string) => void;
}

const MAX_TOTAL = 6;

export function EmptyStateCards({ onSelectSkill, onSendMessage }: Props) {
  const [pinned, setPinned] = useState<MySkill[]>([]);
  const [recommended, setRecommended] = useState<SkillDef[]>([]);
  const [agents, setAgents] = useState<AgentEntry[]>([]);

  useEffect(() => {
    fetchMySkills()
      .then((skills) => setPinned(skills.filter((s) => s.is_pinned)))
      .catch(() => {});

    fetchSkills().then(setRecommended).catch(() => {});

    fetchProfile()
      .then((d) => {
        const profile = d.profile || {};

        const extractStr = (field: unknown): string | undefined => {
          if (typeof field === "string") return field || undefined;
          if (typeof field === "object" && field !== null && "value" in field)
            return (field as { value?: string }).value || undefined;
          return undefined;
        };

        const industry = extractStr(profile["industry"]);

        const painRaw = profile["pain_points"];
        const painPoints: string[] = Array.isArray(painRaw)
          ? painRaw
          : typeof painRaw === "string" && painRaw
          ? painRaw.split(/[、,，\s]+/).filter(Boolean)
          : extractStr(painRaw)
          ? (extractStr(painRaw) as string).split(/[、,，\s]+/).filter(Boolean)
          : [];

        setAgents(getRelevantAgents(industry, painPoints));
      })
      .catch(() => setAgents(getRelevantAgents()));
  }, []);

  // Build display list: pinned → agents → recommended, capped at MAX_TOTAL
  const pinnedKeys = new Set(pinned.map((s) => s.skill_key));
  const dedupedRecommended = recommended.filter((s) => !pinnedKeys.has(s.skill_key));

  const slots = MAX_TOTAL;
  const pinnedSlots = Math.min(pinned.length, slots);
  const agentSlots = Math.min(agents.length, slots - pinnedSlots);
  const skillSlots = slots - pinnedSlots - agentSlots;

  const visiblePinned = pinned.slice(0, pinnedSlots);
  const visibleAgents = agents.slice(0, agentSlots);
  const visibleSkills = dedupedRecommended.slice(0, skillSlots);

  if (visiblePinned.length + visibleAgents.length + visibleSkills.length === 0) return null;

  return (
    <div className="skill-cards">
      {visiblePinned.map((skill) => (
        <button
          key={skill.skill_key}
          className="skill-card skill-card--pinned"
          onClick={() => onSelectSkill(skill.skill_key)}
        >
          <span className="skill-card-name">{skill.scenario_name}</span>
          {skill.tagline && <span className="skill-card-tagline">{skill.tagline}</span>}
        </button>
      ))}

      {visibleAgents.map((agent) => (
        <button
          key={agent.key}
          className="skill-card skill-card--agent"
          onClick={() => onSendMessage(agent.sampleMessage)}
        >
          <span className="skill-card-name">
            {agent.icon} {agent.label}
          </span>
          <span className="skill-card-tagline">{agent.tagline}</span>
        </button>
      ))}

      {visibleSkills.map((skill) => (
        <button
          key={skill.skill_key}
          className="skill-card"
          onClick={() => onSelectSkill(skill.skill_key)}
        >
          <span className="skill-card-name">{skill.scenario_name}</span>
          {skill.tagline && <span className="skill-card-tagline">{skill.tagline}</span>}
        </button>
      ))}
    </div>
  );
}
