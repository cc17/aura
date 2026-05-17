export interface IndustryConfig {
  name: string;
  emoji: string;
  roles: string[];
  painPoints: string[];
}

export const INDUSTRY_CONFIG: IndustryConfig[] = [
  {
    name: "法律",
    emoji: "⚖️",
    roles: ["诉讼律师", "非诉律师", "实习律师", "律所合伙人"],
    painPoints: ["合同审查", "文书起草", "判决研究", "庭审准备", "客户沟通", "案件管理"],
  },
  {
    name: "医疗",
    emoji: "🏥",
    roles: ["住院医师", "主治医师", "科室主任", "全科医生"],
    painPoints: ["病历书写", "患者沟通", "文献学习", "出院小结", "病例讨论", "工作量大"],
  },
  {
    name: "公司法务",
    emoji: "🏛️",
    roles: ["法务专员", "法务经理", "法务总监", "合规专员"],
    painPoints: ["合同审查", "合规排查", "函件起草", "尽职调查", "政策解读", "跨部门协作"],
  },
  {
    name: "学生",
    emoji: "🎓",
    roles: ["大学生", "研究生", "博士生", "留学生"],
    painPoints: ["备考计划", "论文写作", "简历投递", "申论练习", "求职信", "留学申请"],
  },
  {
    name: "互联网",
    emoji: "💻",
    roles: ["产品经理", "研发工程师", "运营", "市场", "设计师"],
    painPoints: ["写周报", "会议纪要", "需求整理", "跟进 bug", "协调跨部门", "OKR 复盘"],
  },
  {
    name: "金融",
    emoji: "📈",
    roles: ["分析师", "基金经理", "投行", "风控", "销售"],
    painPoints: ["研究报告", "数据分析", "客户汇报", "合规文件", "市场跟踪", "风险评估"],
  },
  {
    name: "其他",
    emoji: "🌐",
    roles: ["管理者", "职员", "自由职业", "创业者", "其他"],
    painPoints: ["写作整理", "时间管理", "学习提升", "沟通协作", "项目推进", "其他"],
  },
];

export function getRolesForIndustry(industry: string): string[] {
  return INDUSTRY_CONFIG.find((c) => c.name === industry)?.roles ?? [];
}

export function getPainPointsForIndustry(industry: string): string[] {
  return INDUSTRY_CONFIG.find((c) => c.name === industry)?.painPoints ?? [];
}
