import { useEffect, useRef, useState } from "react";
import { fetchRecommendations, postSkillEvents } from "../services/api";
import type { AgentCard, MySkill, RecommendationResponse, SkillDef } from "../services/api";

interface Props {
  onSelectSkill: (skillKey: string) => void;
  onSendMessage: (text: string) => void;
  onFillTemplate: (text: string) => void;
}

export function EmptyStateCards({ onSelectSkill, onSendMessage, onFillTemplate }: Props) {
  const [recs, setRecs] = useState<RecommendationResponse>({ pinned: [], agents: [], skills: [] });
  const sessionId = useRef(crypto.randomUUID());
  const impressionFired = useRef(false);

  useEffect(() => {
    fetchRecommendations().then(setRecs).catch(() => {});
  }, []);

  // Fire one batch of impression events once the first non-empty response arrives
  useEffect(() => {
    const { pinned, agents, skills } = recs;
    if (pinned.length + agents.length + skills.length === 0 || impressionFired.current) return;
    impressionFired.current = true;

    const sid = sessionId.current;
    const events = [
      ...pinned.map((s: MySkill, i: number) => ({
        item_type: "skill" as const,
        item_key: s.skill_key,
        signal_type: "impressioned",
        context: { position: i, bucket: "pinned" },
        session_id: sid,
      })),
      ...agents.map((a: AgentCard, i: number) => ({
        item_type: "agent" as const,
        item_key: a.key,
        signal_type: "impressioned",
        context: { position: pinned.length + i, bucket: "agent" },
        session_id: sid,
      })),
      ...skills.map((s: SkillDef, i: number) => ({
        item_type: "skill" as const,
        item_key: s.skill_key,
        signal_type: "impressioned",
        context: { position: pinned.length + agents.length + i, bucket: "recommended" },
        session_id: sid,
      })),
    ];
    postSkillEvents(events);
  }, [recs]);

  const handleSkillClick = (skill: SkillDef | MySkill, bucket: string, position: number) => {
    postSkillEvents([{
      item_type: "skill",
      item_key: skill.skill_key,
      signal_type: "clicked",
      context: { position, bucket },
      session_id: sessionId.current,
    }]);
    if (skill.starter_text) {
      onFillTemplate(skill.starter_text);
    } else {
      onSelectSkill(skill.skill_key);
    }
  };

  const handleAgentClick = (agentKey: string, message: string, position: number) => {
    postSkillEvents([{
      item_type: "agent",
      item_key: agentKey,
      signal_type: "clicked",
      context: { position },
      session_id: sessionId.current,
    }]);
    onSendMessage(message);
  };

  const { pinned, agents, skills } = recs;
  if (pinned.length + agents.length + skills.length === 0) return null;

  return (
    <div className="skill-cards">
      {pinned.map((skill, i) => (
        <button
          key={skill.skill_key}
          className="skill-card skill-card--pinned"
          onClick={() => handleSkillClick(skill, "pinned", i)}
        >
          <span className="skill-card-name">{skill.scenario_name}</span>
          {skill.tagline && <span className="skill-card-tagline">{skill.tagline}</span>}
        </button>
      ))}

      {agents.map((agent, i) => (
        <button
          key={agent.key}
          className="skill-card skill-card--agent"
          onClick={() => handleAgentClick(agent.key, agent.sampleMessage, pinned.length + i)}
        >
          <span className="skill-card-name">
            {agent.icon} {agent.label}
          </span>
          <span className="skill-card-tagline">{agent.tagline}</span>
        </button>
      ))}

      {skills.map((skill, i) => (
        <button
          key={skill.skill_key}
          className="skill-card"
          onClick={() => handleSkillClick(skill, "recommended", pinned.length + agents.length + i)}
        >
          <span className="skill-card-name">{skill.scenario_name}</span>
          {skill.tagline && <span className="skill-card-tagline">{skill.tagline}</span>}
        </button>
      ))}
    </div>
  );
}
