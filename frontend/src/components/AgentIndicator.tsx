const AGENT_LABELS: Record<string, string> = {
  general_agent:  "General",
  resume_agent:   "Resume",
  ppt_agent:      "Slides",
  research_agent: "Research",
  gaokao_agent:   "Gaokao",
};

interface AgentIndicatorProps {
  activeAgent: string | null;
}

export function AgentIndicator({ activeAgent }: AgentIndicatorProps) {
  if (!activeAgent) return null;

  const label = AGENT_LABELS[activeAgent] || activeAgent;

  return (
    <div className="agent-indicator">
      <div className="agent-indicator-item">
        <span className="agent-dot" />
        <span>{label} Agent</span>
      </div>
    </div>
  );
}
