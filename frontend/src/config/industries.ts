export interface IndustryConfig {
  name: string;
  emoji: string;
  roles: string[];
  painPoints: string[];
}

export const INDUSTRY_CONFIG: IndustryConfig[] = [
  {
    name: "Legal",
    emoji: "⚖️",
    roles: ["Litigation Lawyer", "Corporate Lawyer", "Legal Intern", "Law Firm Partner"],
    painPoints: ["Contract Review", "Legal Drafting", "Case Research", "Trial Prep", "Client Communication", "Case Management"],
  },
  {
    name: "Healthcare",
    emoji: "🏥",
    roles: ["Resident Doctor", "Attending Physician", "Department Head", "General Practitioner"],
    painPoints: ["Medical Records", "Patient Communication", "Literature Review", "Discharge Summary", "Case Discussion", "High Workload"],
  },
  {
    name: "Corporate Legal",
    emoji: "🏛️",
    roles: ["Legal Specialist", "Legal Manager", "General Counsel", "Compliance Officer"],
    painPoints: ["Contract Review", "Compliance Check", "Letter Drafting", "Due Diligence", "Policy Interpretation", "Cross-team Collaboration"],
  },
  {
    name: "Student",
    emoji: "🎓",
    roles: ["Undergraduate", "Graduate", "PhD", "International Student"],
    painPoints: ["Exam Prep", "Thesis Writing", "Job Applications", "Essay Practice", "Cover Letters", "Study Abroad"],
  },
  {
    name: "Tech",
    emoji: "💻",
    roles: ["Product Manager", "Engineer", "Operations", "Marketing", "Designer"],
    painPoints: ["Weekly Reports", "Meeting Notes", "Requirements Doc", "Bug Tracking", "Cross-team Coordination", "OKR Review"],
  },
  {
    name: "Finance",
    emoji: "📈",
    roles: ["Analyst", "Fund Manager", "Investment Banking", "Risk", "Sales"],
    painPoints: ["Research Reports", "Data Analysis", "Client Presentations", "Compliance Docs", "Market Tracking", "Risk Assessment"],
  },
  {
    name: "Other",
    emoji: "🌐",
    roles: ["Manager", "Staff", "Freelancer", "Entrepreneur", "Other"],
    painPoints: ["Writing & Editing", "Time Management", "Learning", "Communication", "Project Execution", "Other"],
  },
];

export function getRolesForIndustry(industry: string): string[] {
  return INDUSTRY_CONFIG.find((c) => c.name === industry)?.roles ?? [];
}

export function getPainPointsForIndustry(industry: string): string[] {
  return INDUSTRY_CONFIG.find((c) => c.name === industry)?.painPoints ?? [];
}
