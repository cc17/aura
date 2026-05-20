export interface AgentEntry {
  key: string;
  icon: string;
  label: string;
  tagline: string;
  sampleMessage: string;
  universal: boolean;
  painPointKeywords: string[];
  roleKeywords: string[];
}

export const AGENT_ENTRIES: AgentEntry[] = [
  {
    key: "career",
    icon: "💼",
    label: "Job Search",
    tagline: "Job search, resume review, JD analysis",
    sampleMessage: "Help me explore career options and find roles that fit me",
    universal: false,
    painPointKeywords: ["resume", "job", "career", "application", "offer", "interview", "hiring", "internship", "recruitment"],
    roleKeywords: ["graduate", "intern", "student", "job seeker"],
  },
  {
    key: "gaokao",
    icon: "🎓",
    label: "College Admissions",
    tagline: "Find schools by score, explore majors and career prospects",
    sampleMessage: "Help me with college admissions and choosing a major",
    universal: false,
    painPointKeywords: ["college", "admissions", "major", "university", "gaokao", "exam"],
    roleKeywords: ["high school", "student", "applicant"],
  },
  {
    key: "ppt",
    icon: "📊",
    label: "Make Slides",
    tagline: "Enter a topic, generate slides automatically",
    sampleMessage: "Help me create a presentation",
    universal: true,
    painPointKeywords: ["presentation", "slides", "ppt", "deck", "report", "meeting"],
    roleKeywords: ["manager", "product", "operations", "director"],
  },
  {
    key: "research",
    icon: "🔍",
    label: "Research",
    tagline: "Gather information, market analysis, industry reports",
    sampleMessage: "Help me research a topic",
    universal: true,
    painPointKeywords: ["research", "analysis", "report", "market", "data", "competitive", "industry"],
    roleKeywords: ["analyst", "researcher", "strategy", "operations"],
  },
];

const W_PAIN = 3;
const W_ROLE = 2;

function scoreAgent(agent: AgentEntry, painText: string, roleText: string): number {
  const pain = agent.painPointKeywords.filter((kw) => painText.includes(kw)).length * W_PAIN;
  const role = agent.roleKeywords.filter((kw) => roleText.includes(kw)).length * W_ROLE;
  return pain + role;
}

export function getRelevantAgents(
  _industry?: string,
  role?: string,
  painPoints?: string[],
): AgentEntry[] {
  const painText = (painPoints ?? []).join(" ").toLowerCase();
  const roleText = (role ?? "").toLowerCase();

  const scored = AGENT_ENTRIES.map((a) => ({
    agent: a,
    score: scoreAgent(a, painText, roleText),
  }));

  const candidates = scored.filter(({ agent, score }) => agent.universal || score > 0);

  return candidates.sort((a, b) => b.score - a.score).map(({ agent }) => agent);
}

export function scoreSkill(
  skill: { scenario_name: string; tagline?: string | null },
  industry?: string,
  role?: string,
  painPoints?: string[],
): number {
  const text = `${skill.scenario_name} ${skill.tagline ?? ""}`.toLowerCase();
  let score = 0;
  for (const kw of painPoints ?? []) {
    if (text.includes(kw.toLowerCase())) score += W_PAIN;
  }
  if (role && text.includes(role.toLowerCase())) score += W_ROLE;
  if (industry && text.includes(industry.toLowerCase())) score += 1;
  return score;
}
