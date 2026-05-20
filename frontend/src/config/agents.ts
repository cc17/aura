export interface AgentEntry {
  key: string;
  icon: string;
  label: string;
  tagline: string;
  sampleMessage: string;
  universal: boolean;         // true = always a candidate (no gating)
  painPointKeywords: string[];
  roleKeywords: string[];
}

export const AGENT_ENTRIES: AgentEntry[] = [
  {
    key: "career",
    icon: "💼",
    label: "求职 / 简历",
    tagline: "找工作、改简历、分析 JD",
    sampleMessage: "帮我看看求职方向，我想了解一下适合我的岗位",
    universal: false,
    painPointKeywords: ["简历", "求职", "找工作", "投递", "offer", "跳槽", "转行", "面试", "招聘", "实习"],
    roleKeywords: ["应届", "实习生", "待业", "毕业生", "大学生"],
  },
  {
    key: "gaokao",
    icon: "🎓",
    label: "高考志愿",
    tagline: "分数查院校、专业就业前景",
    sampleMessage: "帮我填高考志愿",
    universal: false,
    painPointKeywords: ["高考", "志愿", "报考", "选专业", "备考"],
    roleKeywords: ["高中生", "高三", "考生"],
  },
  {
    key: "ppt",
    icon: "📊",
    label: "做 PPT",
    tagline: "输入主题，自动生成幻灯片",
    sampleMessage: "帮我做一个PPT",
    universal: true,
    painPointKeywords: ["汇报", "演示", "ppt", "幻灯", "周报", "述职", "提案"],
    roleKeywords: ["运营", "产品", "经理", "总监", "主管"],
  },
  {
    key: "research",
    icon: "🔍",
    label: "调研分析",
    tagline: "收集信息、市场分析、行业报告",
    sampleMessage: "帮我调研一个话题",
    universal: true,
    painPointKeywords: ["调研", "分析", "报告", "资料", "信息收集", "竞品", "市场", "数据"],
    roleKeywords: ["分析师", "运营", "策略", "研究员"],
  },
];

// Weights: pain points are the strongest signal, role is secondary
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

  // Universal agents always show; targeted agents require a score > 0
  const candidates = scored.filter(({ agent, score }) => agent.universal || score > 0);

  return candidates.sort((a, b) => b.score - a.score).map(({ agent }) => agent);
}

// Score a skill by matching its text against user profile signals
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
