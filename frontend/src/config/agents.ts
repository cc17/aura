export interface AgentEntry {
  key: string;
  icon: string;
  label: string;
  tagline: string;
  sampleMessage: string;
  industries: string[];       // empty = always show
  painPointKeywords: string[]; // boost this agent when user's pain_points match
}

export const AGENT_ENTRIES: AgentEntry[] = [
  {
    key: "career",
    icon: "💼",
    label: "求职 / 简历",
    tagline: "找工作、改简历、分析 JD",
    sampleMessage: "帮我看看求职方向，我想了解一下适合我的岗位",
    industries: ["学生", "互联网", "金融", "其他"],
    painPointKeywords: ["简历", "求职", "找工作", "投递", "offer", "跳槽", "转行", "面试"],
  },
  {
    key: "gaokao",
    icon: "🎓",
    label: "高考志愿",
    tagline: "分数查院校、专业就业前景",
    sampleMessage: "帮我填高考志愿",
    industries: ["学生"],
    painPointKeywords: ["高考", "志愿", "报考", "选专业", "备考"],
  },
  {
    key: "ppt",
    icon: "📊",
    label: "做 PPT",
    tagline: "输入主题，自动生成幻灯片",
    sampleMessage: "帮我做一个PPT",
    industries: [],
    painPointKeywords: ["汇报", "演示", "ppt", "幻灯"],
  },
  {
    key: "research",
    icon: "🔍",
    label: "调研分析",
    tagline: "收集信息、市场分析、行业报告",
    sampleMessage: "帮我调研一个话题",
    industries: [],
    painPointKeywords: ["调研", "分析", "报告", "资料", "信息收集"],
  },
];

export function getRelevantAgents(industry?: string, painPoints?: string[]): AgentEntry[] {
  const painText = (painPoints ?? []).join(" ").toLowerCase();

  const candidates = AGENT_ENTRIES.filter((a) => {
    if (a.industries.length === 0) return true;
    if (industry && a.industries.includes(industry)) return true;
    // Pain point match overrides industry filter
    if (painText && a.painPointKeywords.some((kw) => painText.includes(kw))) return true;
    return false;
  });

  if (!painText) return candidates;

  return [...candidates].sort((a, b) => {
    const scoreA = a.painPointKeywords.filter((kw) => painText.includes(kw)).length;
    const scoreB = b.painPointKeywords.filter((kw) => painText.includes(kw)).length;
    return scoreB - scoreA;
  });
}
