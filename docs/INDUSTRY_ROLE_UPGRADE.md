# Industry & Role Upgrade 设计文档

> 状态：设计已确认，已实现（阶段 10）

---

## 一、目标

1. 重点覆盖四个垂直行业：**律师、医生、公司法务、学生**
2. 行业与岗位联动：选择行业后，岗位选项自动切换为该行业专属岗位
3. 为每个行业/岗位配套专属 Skill（共新增 21 个），形成有差异化的体验
4. 痛点选项也随行业动态调整

---

## 二、行业 & 岗位矩阵

| 行业 | 可选岗位 |
|---|---|
| 法律 | 诉讼律师、非诉律师、实习律师、律所合伙人 |
| 医疗 | 住院医师、主治医师、科室主任、全科医生 |
| 公司法务 | 法务专员、法务经理、法务总监、合规专员 |
| 学生 | 大学生、研究生、博士生、留学生 |
| 互联网 | 产品经理、研发工程师、运营、市场、设计师 |
| 金融 | 分析师、基金经理、投行、风控、销售 |
| 其他 | 管理者、职员、自由职业、创业者、其他 |

---

## 三、新增 Skill 清单（21 个）

### 律师（5 个）

| skill_key | 名称 | 定位 |
|---|---|---|
| case_summary | 案件摘要生成 | 快速提炼案件核心争议与时间线 |
| legal_document_draft | 法律文书起草 | 起诉状、答辩状等文书框架 |
| judgment_analysis | 判决书解析 | 提炼裁判规则与判决要点 |
| contract_risk_review | 合同风险审查 | 识别风险条款并建议修改 |
| court_prep_brief | 庭审要点准备 | 质证思路与辩论策略整理 |

### 医疗（5 个）

| skill_key | 名称 | 定位 |
|---|---|---|
| medical_record_summary | 病历摘要生成 | 结构化整理病例要点 |
| patient_communication_script | 患者沟通话术 | 医学术语转患者易懂语言 |
| medical_literature_digest | 医学文献解读 | 提炼研究结论与临床启示 |
| discharge_summary_draft | 出院小结起草 | 规范出院记录与随访建议 |
| clinical_case_discussion | 病例讨论整理 | 鉴别诊断思路与诊疗方案 |

### 公司法务（5 个）

| skill_key | 名称 | 定位 |
|---|---|---|
| contract_review_report | 合同审查报告 | 标注风险条款+修改建议 |
| compliance_risk_scan | 合规风险排查 | 识别业务流程合规隐患 |
| legal_letter_draft | 法务函件起草 | 维权通知类专业函件 |
| due_diligence_list | 尽职调查清单 | 交易尽调清单与风险摘要 |
| regulatory_policy_brief | 监管政策解读 | 新政策对业务的影响要点 |

### 学生（6 个）

| skill_key | 名称 | 定位 |
|---|---|---|
| exam_study_plan | 备考计划生成 | 个性化备考时间表与策略 |
| resume_optimizer | 简历优化助手 | 求职简历亮点提炼与重构 |
| thesis_outline_gen | 论文大纲生成 | 学术论文结构规划 |
| civil_exam_essay | 申论写作框架 | 公务员考试申论文章结构 |
| job_cover_letter | 求职信生成 | 定制化实习/校招投递邮件 |
| study_abroad_essay | 留学文书润色 | PS/SOP 结构优化与语言提升 |

---

## 四、前端改动

### OnboardingModal
- 行业列表改为带 emoji 的图标卡片
- 选择行业后，岗位区域动态更新为该行业的专属岗位
- 切换行业自动重置岗位选择
- 痛点选项随行业动态切换

### ProfilePage
- 画像 tab 的行业/岗位字段：点击"编辑"改为 chip 选择器（不再是文本输入框）
- 行业与岗位联动：编辑行业时同步重置岗位

### 共享配置
`frontend/src/config/industries.ts` — 统一维护行业→岗位→痛点映射

---

## 五、Skill-Role 映射优先级

每个 skill 通过 `skill_role_mapping` 表与 industry+role 绑定，priority 三档：
- `essential`：该岗位最核心的 skill，默认 chatbox 优先展示
- `recommended`：推荐使用
- `optional`：可选
