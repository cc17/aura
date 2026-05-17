-- Migration 005: 21 new industry-specific skills for Phase 10
-- Industries: 法律(律师), 医疗, 公司法务, 学生

-- ─── 律师 Skills ───────────────────────────────────────────────────────────────

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'case_summary', '法律', '案件摘要生成', '快速提炼案件核心争议与时间线',
  '输入案件基本信息，自动生成结构化摘要，包括核心争议、关键时间节点、当事人信息与诉求。适合案件开庭前快速梳理或向客户汇报。',
  ARRAY['案件摘要', '案情梳理', '案件整理', '案件概述', '争议焦点'],
  '你是一名资深诉讼律师助理，擅长将复杂案件信息提炼为清晰的结构化摘要。

【案件信息】
{case_info}

【补充说明】
{additional_notes}

请生成以下结构的案件摘要：

## 案件基本信息
- 案件类型：
- 案件当事人：（原告/被告/第三方）
- 涉案金额/标的：

## 核心争议焦点
1.
2.

## 关键时间线
| 时间 | 事件 |
|------|------|

## 我方诉求 / 答辩要点

## 证据清单摘要

## 下一步行动建议

原则：简明扼要，律师可直接用于案件汇报。',
  '{"fields": [{"name": "case_info", "type": "textarea", "label": "案件基本情况（当事人、起因、诉求等）", "required": true, "max_length": 5000}, {"name": "additional_notes", "type": "textarea", "label": "补充说明（可选）", "required": false, "max_length": 2000}]}',
  true, 25, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'legal_document_draft', '法律', '法律文书起草', '一键生成诉状/答辩状/申请书框架',
  '根据案件要素自动生成符合法律规范的文书框架，包括起诉状、答辩状、上诉状等，支持多种文书类型，节省律师起草时间。',
  ARRAY['文书起草', '起诉状', '答辩状', '上诉状', '申请书', '法律文书'],
  '你是一名专业法律文书撰写专家，熟悉各类诉讼文书的格式规范与写作要点。

【文书类型】
{doc_type}

【案件基本信息】
{case_info}

【当事人信息】
{parties_info}

请按照中国法律文书规范起草文书框架：

# {doc_type}

**原告/申请人：**[姓名、身份证号、联系方式]

**被告/被申请人：**[姓名、身份证号/统一社会信用代码、联系方式]

**诉讼请求：**
1.
2.
3.

**事实与理由：**

一、基本事实陈述

二、法律依据
- 适用法条：
- 裁判依据：

三、证据清单

此致
[受理法院名称]

具状人：[签名/盖章]
[日期]

---
> 注：以上为文书框架，请律师根据实际情况补充完善具体内容。',
  '{"fields": [{"name": "doc_type", "type": "select", "label": "文书类型", "required": true, "options": ["起诉状", "答辩状", "上诉状", "反诉状", "强制执行申请书", "财产保全申请书", "撤诉申请书"]}, {"name": "case_info", "type": "textarea", "label": "案件基本情况（事实经过、诉求）", "required": true, "max_length": 3000}, {"name": "parties_info", "type": "text", "label": "当事人基本信息（姓名/公司名）", "required": true, "max_length": 500}]}',
  true, 26, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'judgment_analysis', '法律', '判决书解析', '提炼裁判规则与判决要点',
  '上传或粘贴判决书内容，自动提炼裁判规则、争议焦点认定、法院观点、可引用的类案意义，帮助律师快速理解判决逻辑。',
  ARRAY['判决书', '裁判文书', '判决分析', '裁判规则', '类案研究'],
  '你是一名法律研究专家，擅长分析裁判文书的核心逻辑与判决规律。

【判决书内容】
{judgment_content}

【分析重点】
{analysis_focus}

请提供以下结构化分析：

## 基本信息
- 案号：
- 法院：
- 裁判日期：
- 案件类型：

## 争议焦点梳理
1. 焦点一：[争议点] → 法院认定：
2. 焦点二：[争议点] → 法院认定：

## 裁判规则提炼
> 本案确立/体现的裁判规则：

## 证据认定分析
| 证据 | 法院态度 | 理由 |
|------|----------|------|

## 类案引用价值
- 可引用场景：
- 注意事项：

## 对我方案件的启示',
  '{"fields": [{"name": "judgment_content", "type": "textarea", "label": "判决书内容（粘贴全文或关键段落）", "required": true, "max_length": 20000, "supports_upload": ["pdf", "txt"]}, {"name": "analysis_focus", "type": "text", "label": "重点关注方向（可选，如"证据标准"、"违约金认定"）", "required": false, "max_length": 200}]}',
  true, 27, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'contract_risk_review', '法律', '合同风险审查', '识别风险条款并给出修改建议',
  '粘贴合同文本，自动识别高风险条款（责任免除、违约金过低、管辖约定不当等），并给出专业修改建议，适合律师快速完成初步审查。',
  ARRAY['合同审查', '合同风险', '合同条款', '风险识别', '合同红线'],
  '你是一名资深商事律师，专注合同风险审查，熟悉常见合同陷阱与风险点。

【合同内容】
{contract_content}

【审查重点】
{review_focus}

请提供专业的合同风险审查报告：

## 合同基本信息
- 合同类型：
- 合同主体：
- 主要内容：

## 风险条款清单

### 🔴 高风险条款
| 条款位置 | 原文 | 风险说明 | 修改建议 |
|----------|------|----------|----------|

### 🟡 中风险条款
| 条款位置 | 原文 | 风险说明 | 修改建议 |
|----------|------|----------|----------|

### 🟢 建议补充条款
- 缺失条款一：
- 缺失条款二：

## 整体风险评级
**评级：** [低风险 / 中风险 / 高风险]

**核心建议：**',
  '{"fields": [{"name": "contract_content", "type": "textarea", "label": "合同内容（粘贴全文或关键条款）", "required": true, "max_length": 20000, "supports_upload": ["pdf", "docx", "txt"]}, {"name": "review_focus", "type": "text", "label": "重点审查方向（如"违约责任"、"付款条款"）", "required": false, "max_length": 300}]}',
  true, 28, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'court_prep_brief', '法律', '庭审要点准备', '质证思路与辩论策略整理',
  '输入案件基本情况和对方证据，生成庭审质证提纲、辩论策略和应对思路，帮助律师在庭审前做好充分准备。',
  ARRAY['庭审准备', '质证提纲', '辩论策略', '开庭准备', '庭审技巧'],
  '你是一名经验丰富的出庭律师，擅长庭审策略制定和临场应对。

【案件类型与我方立场】
{case_stance}

【对方主要证据与主张】
{opposing_evidence}

【补充信息】
{extra_info}

请生成庭审要点准备清单：

## 我方核心主张
1.
2.

## 证据质证要点
| 对方证据 | 质疑方向 | 质疑理由 | 我方应对 |
|----------|----------|----------|----------|

## 我方证据展示策略
| 证据名称 | 证明目的 | 展示要点 |
|----------|----------|----------|

## 预计对方攻击点与应对
| 可能攻击点 | 我方应对话术 |
|------------|--------------|

## 开庭陈述要点（3分钟版本）

## 临场注意事项',
  '{"fields": [{"name": "case_stance", "type": "textarea", "label": "案件类型与我方立场（我是原告/被告，核心主张是什么）", "required": true, "max_length": 2000}, {"name": "opposing_evidence", "type": "textarea", "label": "对方主要证据与主张（已知部分）", "required": true, "max_length": 3000}, {"name": "extra_info", "type": "text", "label": "其他补充信息（可选）", "required": false, "max_length": 500}]}',
  true, 29, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

-- ─── 医疗 Skills ───────────────────────────────────────────────────────────────

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'medical_record_summary', '医疗', '病历摘要生成', '结构化整理病例要点',
  '输入患者基本信息和病情描述，自动生成规范的结构化病历摘要，包括主诉、现病史、查体要点、初步诊断，节省医生记录时间。',
  ARRAY['病历摘要', '病历整理', '病案记录', '住院摘要', '病例整理'],
  '你是一名临床经验丰富的医生，擅长将复杂的病情信息整理为规范的医学文档。

【患者基本信息】
{patient_info}

【主要病情描述】
{clinical_info}

请生成规范的病历摘要：

## 患者基本信息
- 性别/年龄：
- 入院日期：

## 主诉
[用一句话概括主要症状和持续时间]

## 现病史
[时间顺序描述发病过程、症状演变、已做检查和治疗]

## 既往史/个人史/家族史
- 既往史：
- 过敏史：
- 个人史：

## 体格检查要点
- T: &nbsp;&nbsp; P: &nbsp;&nbsp; R: &nbsp;&nbsp; BP:
- 重要阳性体征：
- 重要阴性体征：

## 辅助检查摘要
[关键检验/影像结果]

## 初步诊断
1. [主要诊断]
2. [合并症/并发症]

## 诊疗计划
[初步处理方案]',
  '{"fields": [{"name": "patient_info", "type": "text", "label": "患者基本信息（性别、年龄、入院日期）", "required": true, "max_length": 200}, {"name": "clinical_info", "type": "textarea", "label": "主要病情描述（症状、检查结果、现有诊断等）", "required": true, "max_length": 5000}]}',
  true, 30, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'patient_communication_script', '医疗', '患者沟通话术', '医学术语转患者易懂语言',
  '将医学专业术语和诊断信息转化为患者及家属能理解的通俗语言，生成沟通话术脚本，提升医患沟通质量，降低误解风险。',
  ARRAY['患者沟通', '医患沟通', '病情告知', '知情同意', '患者教育'],
  '你是一名擅长医患沟通的临床医生，能把复杂医学信息用患者能理解的语言准确传达。

【需要告知的医学信息】
{medical_info}

【患者情况】
{patient_context}

【沟通场景】
{communication_scene}

请生成医患沟通话术脚本：

## 沟通目标
[本次沟通要达到的核心目的]

## 开场建立信任
> "您好，[称呼]。我是您的主治医生[姓名]。今天想和您谈谈......"

## 核心信息传达（通俗版）
**医学说法：**[专业术语]
**患者语言：**[通俗解释]

## 患者可能的疑虑与应对
| 患者可能问 | 建议回答 |
|------------|----------|
| | |
| | |

## 注意事项告知
- ⚠️ 必须强调的重点：
- 📋 需要患者配合的事项：

## 结尾确认理解
> "您现在有什么问题想问我吗？......"',
  '{"fields": [{"name": "medical_info", "type": "textarea", "label": "需要告知的医学信息（诊断结果、治疗方案、手术风险等）", "required": true, "max_length": 2000}, {"name": "patient_context", "type": "text", "label": "患者情况（年龄、文化程度、情绪状态）", "required": false, "max_length": 200}, {"name": "communication_scene", "type": "select", "label": "沟通场景", "required": true, "options": ["病情诊断告知", "治疗方案讲解", "手术前谈话", "出院注意事项", "不良预后告知", "用药指导"]}]}',
  true, 31, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'medical_literature_digest', '医疗', '医学文献解读', '提炼研究结论与临床启示',
  '粘贴医学文献摘要或全文，自动提炼研究方法、核心结论、证据级别和临床应用价值，帮助医生高效获取最新临床证据。',
  ARRAY['文献解读', '医学研究', '临床证据', '文献综述', '循证医学'],
  '你是一名循证医学专家，擅长批判性阅读医学文献并提炼临床应用价值。

【文献内容】
{literature_content}

【关注角度】
{focus_angle}

请提供结构化文献解读：

## 文献基本信息
- 发表杂志/年份：
- 研究类型：[RCT / 队列研究 / meta分析 / 病例对照 / 综述 等]
- 证据级别：[I / II / III / IV / V]

## 研究问题（PICO框架）
- P（研究人群）：
- I（干预措施）：
- C（对照组）：
- O（主要结局指标）：

## 核心结论
> [一句话概括最重要的发现]

**统计学结果：**[关键数据，如HR、OR、NNT等]

## 研究局限性
1.
2.

## 临床启示
**可以改变实践的结论：**
**暂不推荐改变实践的原因（如有）：**
**适用人群：**

## 与现有指南的关系',
  '{"fields": [{"name": "literature_content", "type": "textarea", "label": "文献内容（摘要或全文）", "required": true, "max_length": 15000, "supports_upload": ["pdf", "txt"]}, {"name": "focus_angle", "type": "text", "label": "重点关注角度（如"治疗效果"、"安全性"、"亚组分析"）", "required": false, "max_length": 200}]}',
  true, 32, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'discharge_summary_draft', '医疗', '出院小结起草', '规范出院记录与随访建议',
  '根据住院病历信息自动生成规范的出院小结草稿，包括住院经过、治疗效果、出院医嘱和随访安排，减轻医生文书负担。',
  ARRAY['出院小结', '出院记录', '出院医嘱', '随访计划', '出院总结'],
  '你是一名临床医生，擅长撰写规范、完整的出院小结文档。

【住院基本信息】
{admission_info}

【主要诊疗经过】
{treatment_course}

【出院情况】
{discharge_status}

请生成规范的出院小结草稿：

## 出院小结

**患者姓名：**　　　　**住院号：**
**入院日期：**　　　　**出院日期：**　　　　**住院天数：**
**科室：**　　　　　　**主治医生：**

### 入院诊断
1.

### 出院诊断
1.

### 诊疗经过
[按时间顺序描述主要检查结果、治疗措施、病情变化、手术/操作情况]

### 出院情况
- 症状：
- 体征：
- 复查指标：

### 出院医嘱
**药物治疗：**
| 药名 | 剂量 | 用法 | 疗程 |
|------|------|------|------|

**生活指导：**
- 饮食：
- 活动：
- 注意事项：

**随访安排：**
- 复诊时间：
- 复查项目：
- 紧急就医指征：',
  '{"fields": [{"name": "admission_info", "type": "text", "label": "住院基本信息（姓名、入院日期、出院日期、科室）", "required": true, "max_length": 300}, {"name": "treatment_course", "type": "textarea", "label": "主要诊疗经过（诊断、治疗措施、检查结果）", "required": true, "max_length": 5000}, {"name": "discharge_status", "type": "textarea", "label": "出院情况与出院医嘱要点", "required": true, "max_length": 2000}]}',
  true, 33, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'clinical_case_discussion', '医疗', '病例讨论整理', '鉴别诊断思路与诊疗方案',
  '输入患者病情，生成系统性鉴别诊断思路、进一步检查建议和诊疗方案，适用于疑难病例讨论、教学查房或住院医师培训。',
  ARRAY['病例讨论', '鉴别诊断', '疑难病例', '教学查房', '诊疗思路'],
  '你是一名临床经验丰富的主任医师，擅长系统性分析疑难病例，引导科室团队进行高质量的病例讨论。

【患者病情摘要】
{case_summary}

【已完成的检查结果】
{test_results}

【讨论重点】
{discussion_focus}

请生成病例讨论框架：

## 病例摘要（2分钟版）

## 定性诊断方向
| 诊断方向 | 支持依据 | 不支持依据 | 可能性 |
|----------|----------|------------|--------|
| | | | 高/中/低 |
| | | | 高/中/低 |

## 进一步检查建议
**优先级高（48小时内）：**
1.
2.

**可择期完成：**
1.

## 当前治疗方案建议
- 对症处理：
- 针对性治疗：
- 监测指标：

## 预后评估与风险点
- 主要风险：
- 需警惕的并发症：

## 讨论要点（用于教学）
1. 本案例的教学价值：
2. 值得思考的问题：',
  '{"fields": [{"name": "case_summary", "type": "textarea", "label": "患者病情摘要（主诉、现病史、体征）", "required": true, "max_length": 3000}, {"name": "test_results", "type": "textarea", "label": "已完成的检查结果", "required": false, "max_length": 3000}, {"name": "discussion_focus", "type": "text", "label": "讨论重点（如"明确诊断"、"调整治疗方案"）", "required": false, "max_length": 200}]}',
  true, 34, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

-- ─── 公司法务 Skills ───────────────────────────────────────────────────────────

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'contract_review_report', '公司法务', '合同审查报告', '标注风险条款 + 修改建议',
  '针对公司法务场景优化的合同审查工具，从甲方视角分析合同风险，生成专业审查报告，包含条款标注、风险分级和修改意见。',
  ARRAY['合同审查报告', '合同审阅', '法务审查', '合同批注', '甲方视角'],
  '你是一名公司法务总监，专注从公司利益角度进行合同审查，善于识别商业风险和法律风险。

【合同内容】
{contract_content}

【我方角色与核心诉求】
{our_position}

请生成法务审查报告：

# 合同审查报告

**合同名称：**
**审查日期：**
**审查人：**

## 一、合同概况
- 合同性质：
- 交易对手方：
- 主要标的及金额：
- 合同期限：

## 二、整体风险评级
**综合风险等级：** 🔴高风险 / 🟡中风险 / 🟢低风险

## 三、重要条款审查

### 3.1 付款条款
**原文：**
**问题：**
**修改建议：**

### 3.2 违约责任条款
**原文：**
**问题：**
**修改建议：**

### 3.3 争议解决条款
**原文：**
**问题：**
**修改建议：**

### 3.4 其他重要条款
[列明其他需关注条款]

## 四、缺失条款建议补充
1.
2.

## 五、审查结论与建议
**总体建议：** 可签署 / 修改后签署 / 不建议签署
**优先修改事项：**',
  '{"fields": [{"name": "contract_content", "type": "textarea", "label": "合同内容", "required": true, "max_length": 20000, "supports_upload": ["pdf", "docx", "txt"]}, {"name": "our_position", "type": "textarea", "label": "我方角色与核心诉求（如：我方为采购方，重点关注交货期和质量保证）", "required": true, "max_length": 500}]}',
  true, 35, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'compliance_risk_scan', '公司法务', '合规风险排查', '识别业务流程中的合规隐患',
  '描述业务场景，自动识别潜在的合规风险点（数据合规、反腐、劳动法、广告法等），给出风险评级和整改建议，适合法务日常合规检查。',
  ARRAY['合规风险', '合规检查', '法务合规', '风险排查', '合规审查'],
  '你是一名资深合规专员，熟悉中国各类监管法规，擅长从法务视角识别业务操作中的合规隐患。

【业务场景描述】
{business_scenario}

【所在行业/监管环境】
{regulatory_context}

请进行合规风险排查：

## 合规风险排查报告

### 识别到的合规风险点

#### 🔴 高风险（需立即整改）
| 风险点 | 涉及法规 | 可能后果 | 整改建议 |
|--------|----------|----------|----------|

#### 🟡 中风险（需关注）
| 风险点 | 涉及法规 | 可能后果 | 整改建议 |
|--------|----------|----------|----------|

#### 🟢 低风险（建议优化）
| 风险点 | 建议 |
|--------|------|

### 重点法规速查
| 适用法规 | 关键条款 | 合规要求 |
|----------|----------|----------|

### 建议优先整改清单
1. [最紧急]
2.
3.

### 合规改进建议',
  '{"fields": [{"name": "business_scenario", "type": "textarea", "label": "业务场景描述（具体操作流程或业务模式）", "required": true, "max_length": 3000}, {"name": "regulatory_context", "type": "text", "label": "所在行业或特定监管背景（如：金融、医疗、互联网平台）", "required": false, "max_length": 200}]}',
  true, 36, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'legal_letter_draft', '公司法务', '法务函件起草', '专业维权通知类函件',
  '根据法务场景自动生成专业函件草稿，包括律师函、催告函、解除合同通知、侵权警告函等，格式规范、措辞专业。',
  ARRAY['律师函', '催告函', '法务函', '法律信函', '维权通知', '解除合同通知'],
  '你是一名专业公司法务，擅长起草各类法务函件，措辞严谨且有威慑力。

【函件类型】
{letter_type}

【事件背景与诉求】
{case_background}

【对方信息】
{recipient_info}

请起草专业法务函件：

---

[公司抬头/LOGO位置]

**{letter_type}**

[收件方名称]：

**一、基本事实**

[客观陈述事实经过]

**二、法律依据**

根据《[适用法律]》第[X]条之规定，[法律依据阐述]。

**三、我方诉求**

依据上述事实及法律规定，现正式通知贵方：
1.
2.

如贵方未能在收到本函后 **[X]个工作日** 内予以回复并采取相应措施，我方将依法采取进一步法律行动，由此产生的一切法律责任及损失，由贵方自行承担。

特此函告。

[发函方名称]（盖章）
法定代表人/授权代理人：
[日期]

---
> 注：本函件草稿，请法务/律师根据实际情况修改后使用。',
  '{"fields": [{"name": "letter_type", "type": "select", "label": "函件类型", "required": true, "options": ["律师函", "催告函", "解除合同通知书", "侵权警告函", "付款催告函", "违约通知函", "保全证据通知"]}, {"name": "case_background", "type": "textarea", "label": "事件背景与我方诉求", "required": true, "max_length": 2000}, {"name": "recipient_info", "type": "text", "label": "对方名称（公司全称或个人姓名）", "required": true, "max_length": 200}]}',
  true, 37, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'due_diligence_list', '公司法务', '尽职调查清单', '交易尽调清单与风险摘要',
  '根据交易类型自动生成定制化尽职调查清单，涵盖法律、财务、税务等维度，帮助法务团队高效开展并购、投资前的尽调工作。',
  ARRAY['尽职调查', '尽调清单', '并购尽调', '投资尽调', 'DD清单'],
  '你是一名资深并购法务，有丰富的交易尽职调查经验，熟悉各类交易的核心风险点。

【交易类型】
{transaction_type}

【目标公司基本情况】
{target_info}

【重点关注领域】
{focus_areas}

请生成定制化尽职调查清单：

# 尽职调查清单
**目标公司：** [名称]
**交易类型：** {transaction_type}
**调查日期：**

## 一、企业基础信息
- [ ] 营业执照及历次变更记录
- [ ] 公司章程及历次修订
- [ ] 股权结构及实际控制人认定
- [ ] 历次股权变动记录
- [ ] 三会文件（股东会/董事会/监事会）

## 二、法律诉讼及合规
- [ ] 未决诉讼、仲裁案件清单
- [ ] 行政处罚记录
- [ ] 监管调查及整改情况
- [ ] 反腐合规制度及执行情况
- [ ] 劳动争议及集体纠纷

## 三、核心合同与业务
- [ ] 主要客户合同（TOP10）
- [ ] 主要供应商合同
- [ ] 重大采购及服务协议
- [ ] 独家协议、竞业限制安排
- [ ] 关联方交易清单

## 四、知识产权
- [ ] 商标注册情况
- [ ] 专利清单（已申请/已授权）
- [ ] 软件著作权
- [ ] 域名注册情况

## 五、人力资源
- [ ] 核心人员劳动合同
- [ ] 员工人数及薪酬体系
- [ ] 离职补偿安排
- [ ] 竞业限制协议

## 六、重点风险提示
[根据交易类型列出需要重点关注的风险]

## 七、特殊核查事项
[根据目标公司情况列出特殊要点]',
  '{"fields": [{"name": "transaction_type", "type": "select", "label": "交易类型", "required": true, "options": ["股权收购", "资产收购", "增资入股", "战略投资", "合并重组", "供应商合作尽调"]}, {"name": "target_info", "type": "textarea", "label": "目标公司基本情况（行业、规模、主营业务）", "required": true, "max_length": 1000}, {"name": "focus_areas", "type": "text", "label": "重点关注领域（如"知识产权"、"劳动风险"）", "required": false, "max_length": 300}]}',
  true, 38, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'regulatory_policy_brief', '公司法务', '监管政策解读', '新政策对业务的影响要点',
  '粘贴监管新规或政策文件，快速解读核心要点，分析对公司业务的具体影响，生成业务部门易读的政策简报。',
  ARRAY['政策解读', '监管新规', '合规简报', '政策分析', '法规研究'],
  '你是一名资深法务研究员，擅长将晦涩的监管政策转化为业务团队能理解和执行的合规指引。

【政策文件内容】
{policy_content}

【公司主要业务范围】
{business_scope}

请生成政策解读简报：

# 监管政策解读简报

**政策名称：**
**发布机构：**
**生效日期：**
**解读日期：**

## 一、政策背景
[为什么出台这个政策，监管意图]

## 二、核心变化（与原有规定对比）
| 事项 | 原有规定 | 新规要求 | 变化程度 |
|------|----------|----------|----------|

## 三、对我司业务的影响分析

### 直接影响业务
| 业务线 | 影响描述 | 影响程度 |
|--------|----------|----------|

### 需要调整的现有实践
1.
2.

## 四、合规整改要求
**必须完成（法定要求）：**
- [ ]
- [ ]

**建议优化（最佳实践）：**
- [ ]

## 五、整改时间表
| 事项 | 负责部门 | 完成期限 |
|------|----------|----------|

## 六、待进一步明确的问题
[监管机构尚未明确的灰色地带]',
  '{"fields": [{"name": "policy_content", "type": "textarea", "label": "政策文件内容（粘贴全文或核心条款）", "required": true, "max_length": 20000, "supports_upload": ["pdf", "txt"]}, {"name": "business_scope", "type": "textarea", "label": "公司主要业务范围（帮助定向分析影响）", "required": true, "max_length": 500}]}',
  true, 39, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

-- ─── 学生 Skills ───────────────────────────────────────────────────────────────

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'exam_study_plan', '学生', '备考计划生成', '个性化备考时间表与策略',
  '输入考试信息和自身情况，生成个性化备考计划，包括阶段目标、每日安排、重点突破方向和学习资源建议，让备考更有节奏。',
  ARRAY['备考计划', '学习计划', '考研计划', '考公计划', '备考攻略', '学习安排'],
  '你是一名经验丰富的学习规划师，帮助学生制定科学、可执行的备考计划。

【目标考试信息】
{exam_info}

【个人基本情况】
{personal_info}

【距离考试时间】
{time_remaining}

请生成个性化备考计划：

## 备考全局分析
- **考试难点：**
- **你的薄弱环节：**
- **核心策略：**

## 备考阶段划分

### 阶段一：基础构建期（[时间段]）
**目标：**
**每日安排：**
| 时间 | 科目/内容 | 时长 | 方法 |
|------|-----------|------|------|
**阶段里程碑：**

### 阶段二：强化提升期（[时间段]）
**目标：**
**重点突破：**
**刷题计划：**

### 阶段三：冲刺巩固期（[时间段]）
**目标：**
**模拟考试安排：**
**错题复盘：**

## 推荐学习资源
- 教材/用书：
- 网课推荐：
- 题库建议：

## 高效学习技巧
1.
2.
3.

## 注意事项与避坑指南
- ⚠️ 常见误区：
- 💡 经验建议：',
  '{"fields": [{"name": "exam_info", "type": "text", "label": "目标考试（如：2025年考研、国家公务员考试、CPA等）", "required": true, "max_length": 200}, {"name": "personal_info", "type": "textarea", "label": "个人情况（学历背景、现有水平、每天可学习时长）", "required": true, "max_length": 1000}, {"name": "time_remaining", "type": "text", "label": "距离考试还有多长时间", "required": true, "max_length": 100}]}',
  true, 40, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'resume_optimizer', '学生', '简历优化助手', '求职简历亮点提炼与重构',
  '粘贴现有简历或描述个人经历，自动识别亮点、重构表达方式，用 STAR 法则和量化数据强化每条经历，帮助你的简历脱颖而出。',
  ARRAY['简历优化', '简历修改', '求职简历', '简历润色', '校招简历'],
  '你是一名有10年校园招聘经验的 HR 专家，熟悉大厂和各行业招聘标准，擅长帮学生把平淡的经历改写成有竞争力的简历。

【当前简历内容 / 个人经历描述】
{resume_content}

【目标岗位/行业】
{target_position}

请对简历进行全面优化：

## 简历诊断
**整体评分：** [X/10]
**核心问题：**
1.
2.

## 优化建议

### 个人简介优化
**原文：**
**优化版：**（突出[核心竞争力]，20字以内）

### 经历条目逐条优化
**[经历名称]**
| | 原内容 | 优化版 |
|-|--------|--------|
| 描述 | | |
**优化说明：**（用了 STAR 法则的哪些要素）

（其余经历同上格式）

### 技能/获奖模块建议
- 建议保留：
- 建议删除：
- 建议补充：

## 关键词优化（针对 {target_position}）
**JD高频词（建议体现）：**

## 最终版一句话 Profile
> [为你定制的简历开头金句]

## 还需要补充的内容
- [ ]
- [ ] ',
  '{"fields": [{"name": "resume_content", "type": "textarea", "label": "当前简历内容或个人经历描述", "required": true, "max_length": 5000, "supports_upload": ["pdf", "docx", "txt"]}, {"name": "target_position", "type": "text", "label": "目标岗位/行业（如：互联网产品实习、央企管培生、法律实习）", "required": true, "max_length": 200}]}',
  true, 41, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'thesis_outline_gen', '学生', '论文大纲生成', '学术论文结构规划',
  '输入论文题目和研究方向，自动生成符合学术规范的论文大纲，包括各章节结构、核心论点和内容提示，帮助你快速启动论文写作。',
  ARRAY['论文大纲', '毕业论文', '学术论文', '论文框架', '论文结构'],
  '你是一名经验丰富的学术导师，熟悉各学科论文写作规范，擅长帮助学生构建逻辑清晰、结构完整的论文框架。

【论文题目】
{thesis_title}

【研究背景与主要观点】
{research_background}

【论文类型与学历层次】
{thesis_type}

请生成学术论文大纲：

## 论文基本信息
- **题目：** {thesis_title}
- **类型：** {thesis_type}
- **研究问题：** [核心研究问题]
- **研究方法：** [定性/定量/混合]

## 论文大纲

### 摘要（Abstract）
[提示：研究背景→研究方法→主要发现→结论，约300字]

### 第一章 绪论
1.1 研究背景与意义
1.2 研究问题与目标
1.3 研究方法与技术路线
1.4 论文结构安排

### 第二章 文献综述
2.1 [核心概念界定]
2.2 [相关理论梳理]
2.3 [研究现状评述]
2.4 [研究空白与本文定位]

### 第三章 [核心章节标题]
3.1
3.2
3.3

### 第四章 [实证/案例/分析章节]
4.1
4.2
4.3

### 第五章 结论与展望
5.1 主要研究结论
5.2 理论贡献
5.3 实践启示
5.4 研究局限与未来展望

### 参考文献
[提示：建议引用文献数量：本科30+，硕士50+，博士100+]

### 附录（如有）

## 写作提示
- 核心论点：
- 需要重点论证的部分：
- 建议收集的数据/资料：',
  '{"fields": [{"name": "thesis_title", "type": "text", "label": "论文题目（或初步设想的题目）", "required": true, "max_length": 300}, {"name": "research_background", "type": "textarea", "label": "研究背景与主要观点（简述研究问题和初步思路）", "required": true, "max_length": 2000}, {"name": "thesis_type", "type": "select", "label": "论文类型与学历层次", "required": true, "options": ["本科毕业论文", "硕士学位论文", "博士学位论文", "课程论文/小论文", "期刊投稿论文"]}]}',
  true, 42, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'civil_exam_essay', '学生', '申论写作框架', '公务员考试申论文章结构',
  '输入申论题目和材料要点，快速生成符合考试评分标准的申论文章框架，包括标题、开头、分论点和结尾，帮助你在有限时间内写出高分申论。',
  ARRAY['申论写作', '公务员考试', '国考申论', '省考申论', '申论框架', '申论模板'],
  '你是一名公务员考试培训专家，深谙申论评分逻辑，帮助考生快速构建高分文章框架。

【申论材料核心主题】
{essay_theme}

【题目要求】
{essay_requirement}

【字数要求】
{word_count}

请生成申论写作框架：

## 审题分析
- **核心议题：**
- **文章角度：**
- **关键词：**

## 文章框架

### 标题建议（3个选项）
1. [建议一]
2. [建议二]
3. [建议三]

### 开头段（约150字）
**开头方式：** [名言引用/现象导入/数据切入/对比引入]
**参考写法：**
[开头示范文字]

### 主体论证

#### 分论点一：[标题]
**论点：**
**论据1（理论依据）：**
**论据2（事例支撑）：**
**论证逻辑：**

#### 分论点二：[标题]
**论点：**
**论据1：**
**论据2：**

#### 分论点三：[标题]（如需要）
**论点：**
**论据：**

### 结尾段（约100字）
**结尾方式：** [总结升华/呼吁行动/展望未来]
**参考写法：**
[结尾示范文字]

## 高分关键词清单
[适合本题的政务语言/政策词汇]

## 写作注意事项
- ⚠️ 避免：
- ✅ 强调：',
  '{"fields": [{"name": "essay_theme", "type": "textarea", "label": "申论材料核心主题（简述材料主要内容和背景）", "required": true, "max_length": 1000}, {"name": "essay_requirement", "type": "textarea", "label": "题目要求（完整题目要求，如"请结合材料，围绕XX主题写一篇文章"）", "required": true, "max_length": 500}, {"name": "word_count", "type": "text", "label": "字数要求（如：1000-1200字）", "required": false, "max_length": 50}]}',
  true, 43, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'job_cover_letter', '学生', '求职信生成', '定制化实习/校招投递邮件',
  '输入岗位信息和个人背景，生成针对性强的求职信/投递邮件，突出与岗位的匹配度，帮助你获得更多面试机会。',
  ARRAY['求职信', '投递邮件', '实习申请', '校招邮件', '自我推荐信'],
  '你是一名经验丰富的职业规划顾问，帮助学生写出既真实又有竞争力的求职信。

【目标职位信息】
{job_info}

【个人背景与亮点】
{personal_background}

【求职信类型】
{letter_type}

请生成定制化求职信：

---

**主题行：** [姓名] | [学校+专业] | 应聘[职位名称] | [学历]

**收件方：**[招聘负责人/HR]您好，

**开头段（引起兴趣）：**
我是[学校][专业][年级]的[姓名]，在[某渠道]看到[公司名]招聘[职位]的信息，深感与我的背景和志向高度契合，因此投递此信。

**匹配度展示段（最重要）：**
贵司对[岗位要求X]的需要，与我的[相关经历/技能]高度吻合：

- **[技能/经历一]：** [具体说明，带数据]
- **[技能/经历二]：** [具体说明]
- **[技能/经历三]：** [具体说明]

**对公司的了解与热情段：**
我关注[公司名]已久，尤其[具体产品/业务/价值观]令我印象深刻。[1-2句真实感受]

**结尾与行动号召：**
期待有机会与您进一步交流，详细介绍我的背景。随信附上简历，如有需要，我可以随时配合安排面试。

谢谢您抽出时间阅读此信！

此致
[姓名]
[联系方式]
[日期]

---
**版本B（更简洁风格）：**
[提供一个更简短的备选版本]

## 投递建议
- **邮件主题格式：**
- **附件命名：**
- **投递时机：**',
  '{"fields": [{"name": "job_info", "type": "textarea", "label": "目标职位信息（公司名、职位、主要职责要求）", "required": true, "max_length": 1000}, {"name": "personal_background", "type": "textarea", "label": "个人背景与亮点（学校、专业、相关经历、技能）", "required": true, "max_length": 2000}, {"name": "letter_type", "type": "select", "label": "类型", "required": true, "options": ["实习申请", "校招应届生", "转岗/跨行申请", "科研/学术职位"]}]}',
  true, 44, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

INSERT INTO industry_skills (skill_key, industry, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, enabled, display_order, is_universal, layer)
VALUES (
  'study_abroad_essay', '学生', '留学文书润色', 'PS/SOP 结构优化与语言提升',
  '提交个人陈述(PS)或目的陈述(SOP)草稿，获得结构优化建议、语言润色和针对目标院校的定制建议，提升留学申请竞争力。',
  ARRAY['留学文书', '个人陈述', 'PS润色', 'SOP写作', '留学申请', '研究计划'],
  '你是一名有10年留学申请文书指导经验的顾问，帮助过数百名学生成功申请全球Top50院校，熟悉各类项目对文书的期望。

【文书类型与目标学校/项目】
{target_info}

【文书草稿】
{essay_draft}

【申请背景】
{application_background}

请提供全面的文书优化建议：

## 整体评估
**文书强项：**
**需要改进的问题：**
1.
2.

## 结构优化建议

### 开头（Hook）
**当前：** [原文开头]
**问题：**
**优化建议：**

### 主体逻辑
**叙事主线是否清晰：** 是/否
**建议调整的顺序或重点：**

### 为什么选择这个项目（Why This Program）
**当前有/无此部分**
**建议：**

### 结尾
**当前：**
**优化建议：** 结尾要回扣主题，展现未来愿景

## 关键段落润色
[选择最需要润色的1-2段，提供具体改写建议]

**原文：**
> [原文段落]

**润色版：**
> [改写后的段落]

**改动说明：** [解释改动逻辑]

## 针对 [目标学校/项目] 的定制建议
- 该项目看重：
- 建议在文书中体现：
- 避免：

## 下一步建议
- [ ]
- [ ] ',
  '{"fields": [{"name": "target_info", "type": "text", "label": "文书类型与目标学校/项目（如：申请哥大教育学硕士的SOP）", "required": true, "max_length": 200}, {"name": "essay_draft", "type": "textarea", "label": "文书草稿（中英文均可）", "required": true, "max_length": 8000}, {"name": "application_background", "type": "textarea", "label": "申请背景（本科院校、GPA、研究经历等）", "required": false, "max_length": 500}]}',
  true, 45, false, 1
) ON CONFLICT (skill_key) DO NOTHING;

-- ─── skill_role_mapping ────────────────────────────────────────────────────────
-- 律师 skills × 4 roles

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '诉讼律师', 'essential', 1 FROM industry_skills WHERE skill_key = 'case_summary'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '诉讼律师', 'essential', 2 FROM industry_skills WHERE skill_key = 'court_prep_brief'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '诉讼律师', 'essential', 3 FROM industry_skills WHERE skill_key = 'judgment_analysis'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '诉讼律师', 'recommended', 4 FROM industry_skills WHERE skill_key = 'legal_document_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '诉讼律师', 'optional', 5 FROM industry_skills WHERE skill_key = 'contract_risk_review'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '非诉律师', 'essential', 1 FROM industry_skills WHERE skill_key = 'contract_risk_review'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '非诉律师', 'essential', 2 FROM industry_skills WHERE skill_key = 'legal_document_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '非诉律师', 'recommended', 3 FROM industry_skills WHERE skill_key = 'case_summary'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '非诉律师', 'recommended', 4 FROM industry_skills WHERE skill_key = 'judgment_analysis'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '非诉律师', 'optional', 5 FROM industry_skills WHERE skill_key = 'court_prep_brief'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '实习律师', 'essential', 1 FROM industry_skills WHERE skill_key = 'case_summary'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '实习律师', 'essential', 2 FROM industry_skills WHERE skill_key = 'legal_document_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '实习律师', 'recommended', 3 FROM industry_skills WHERE skill_key = 'judgment_analysis'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '实习律师', 'recommended', 4 FROM industry_skills WHERE skill_key = 'contract_risk_review'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '实习律师', 'optional', 5 FROM industry_skills WHERE skill_key = 'court_prep_brief'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '律所合伙人', 'essential', 1 FROM industry_skills WHERE skill_key = 'case_summary'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '律所合伙人', 'essential', 2 FROM industry_skills WHERE skill_key = 'contract_risk_review'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '律所合伙人', 'recommended', 3 FROM industry_skills WHERE skill_key = 'judgment_analysis'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '律所合伙人', 'recommended', 4 FROM industry_skills WHERE skill_key = 'court_prep_brief'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '法律', '律所合伙人', 'optional', 5 FROM industry_skills WHERE skill_key = 'legal_document_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

-- 医疗 skills × 4 roles

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '住院医师', 'essential', 1 FROM industry_skills WHERE skill_key = 'medical_record_summary'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '住院医师', 'essential', 2 FROM industry_skills WHERE skill_key = 'discharge_summary_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '住院医师', 'recommended', 3 FROM industry_skills WHERE skill_key = 'clinical_case_discussion'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '住院医师', 'recommended', 4 FROM industry_skills WHERE skill_key = 'patient_communication_script'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '住院医师', 'optional', 5 FROM industry_skills WHERE skill_key = 'medical_literature_digest'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '主治医师', 'essential', 1 FROM industry_skills WHERE skill_key = 'clinical_case_discussion'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '主治医师', 'essential', 2 FROM industry_skills WHERE skill_key = 'medical_record_summary'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '主治医师', 'recommended', 3 FROM industry_skills WHERE skill_key = 'patient_communication_script'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '主治医师', 'recommended', 4 FROM industry_skills WHERE skill_key = 'medical_literature_digest'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '主治医师', 'optional', 5 FROM industry_skills WHERE skill_key = 'discharge_summary_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '科室主任', 'essential', 1 FROM industry_skills WHERE skill_key = 'clinical_case_discussion'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '科室主任', 'essential', 2 FROM industry_skills WHERE skill_key = 'medical_literature_digest'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '科室主任', 'recommended', 3 FROM industry_skills WHERE skill_key = 'patient_communication_script'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '科室主任', 'recommended', 4 FROM industry_skills WHERE skill_key = 'medical_record_summary'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '科室主任', 'optional', 5 FROM industry_skills WHERE skill_key = 'discharge_summary_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '全科医生', 'essential', 1 FROM industry_skills WHERE skill_key = 'patient_communication_script'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '全科医生', 'essential', 2 FROM industry_skills WHERE skill_key = 'medical_record_summary'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '全科医生', 'recommended', 3 FROM industry_skills WHERE skill_key = 'discharge_summary_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '全科医生', 'recommended', 4 FROM industry_skills WHERE skill_key = 'clinical_case_discussion'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '医疗', '全科医生', 'optional', 5 FROM industry_skills WHERE skill_key = 'medical_literature_digest'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

-- 公司法务 skills × 4 roles

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务专员', 'essential', 1 FROM industry_skills WHERE skill_key = 'contract_review_report'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务专员', 'essential', 2 FROM industry_skills WHERE skill_key = 'legal_letter_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务专员', 'recommended', 3 FROM industry_skills WHERE skill_key = 'compliance_risk_scan'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务专员', 'recommended', 4 FROM industry_skills WHERE skill_key = 'regulatory_policy_brief'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务专员', 'optional', 5 FROM industry_skills WHERE skill_key = 'due_diligence_list'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务经理', 'essential', 1 FROM industry_skills WHERE skill_key = 'contract_review_report'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务经理', 'essential', 2 FROM industry_skills WHERE skill_key = 'compliance_risk_scan'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务经理', 'recommended', 3 FROM industry_skills WHERE skill_key = 'regulatory_policy_brief'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务经理', 'recommended', 4 FROM industry_skills WHERE skill_key = 'due_diligence_list'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务经理', 'optional', 5 FROM industry_skills WHERE skill_key = 'legal_letter_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务总监', 'essential', 1 FROM industry_skills WHERE skill_key = 'compliance_risk_scan'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务总监', 'essential', 2 FROM industry_skills WHERE skill_key = 'regulatory_policy_brief'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务总监', 'essential', 3 FROM industry_skills WHERE skill_key = 'due_diligence_list'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务总监', 'recommended', 4 FROM industry_skills WHERE skill_key = 'contract_review_report'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '法务总监', 'optional', 5 FROM industry_skills WHERE skill_key = 'legal_letter_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '合规专员', 'essential', 1 FROM industry_skills WHERE skill_key = 'compliance_risk_scan'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '合规专员', 'essential', 2 FROM industry_skills WHERE skill_key = 'regulatory_policy_brief'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '合规专员', 'recommended', 3 FROM industry_skills WHERE skill_key = 'contract_review_report'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '合规专员', 'recommended', 4 FROM industry_skills WHERE skill_key = 'legal_letter_draft'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '公司法务', '合规专员', 'optional', 5 FROM industry_skills WHERE skill_key = 'due_diligence_list'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

-- 学生 skills × 4 roles

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '大学生', 'essential', 1 FROM industry_skills WHERE skill_key = 'resume_optimizer'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '大学生', 'essential', 2 FROM industry_skills WHERE skill_key = 'job_cover_letter'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '大学生', 'recommended', 3 FROM industry_skills WHERE skill_key = 'exam_study_plan'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '大学生', 'recommended', 4 FROM industry_skills WHERE skill_key = 'civil_exam_essay'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '大学生', 'optional', 5 FROM industry_skills WHERE skill_key = 'thesis_outline_gen'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '大学生', 'optional', 6 FROM industry_skills WHERE skill_key = 'study_abroad_essay'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '研究生', 'essential', 1 FROM industry_skills WHERE skill_key = 'thesis_outline_gen'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '研究生', 'essential', 2 FROM industry_skills WHERE skill_key = 'exam_study_plan'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '研究生', 'recommended', 3 FROM industry_skills WHERE skill_key = 'resume_optimizer'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '研究生', 'recommended', 4 FROM industry_skills WHERE skill_key = 'job_cover_letter'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '研究生', 'optional', 5 FROM industry_skills WHERE skill_key = 'study_abroad_essay'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '研究生', 'optional', 6 FROM industry_skills WHERE skill_key = 'civil_exam_essay'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '博士生', 'essential', 1 FROM industry_skills WHERE skill_key = 'thesis_outline_gen'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '博士生', 'recommended', 2 FROM industry_skills WHERE skill_key = 'resume_optimizer'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '博士生', 'recommended', 3 FROM industry_skills WHERE skill_key = 'job_cover_letter'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '博士生', 'optional', 4 FROM industry_skills WHERE skill_key = 'exam_study_plan'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '博士生', 'optional', 5 FROM industry_skills WHERE skill_key = 'study_abroad_essay'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '留学生', 'essential', 1 FROM industry_skills WHERE skill_key = 'study_abroad_essay'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '留学生', 'essential', 2 FROM industry_skills WHERE skill_key = 'resume_optimizer'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '留学生', 'recommended', 3 FROM industry_skills WHERE skill_key = 'thesis_outline_gen'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '留学生', 'recommended', 4 FROM industry_skills WHERE skill_key = 'job_cover_letter'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '留学生', 'optional', 5 FROM industry_skills WHERE skill_key = 'exam_study_plan'
ON CONFLICT (skill_id, industry, role) DO NOTHING;

INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT id, '学生', '留学生', 'optional', 6 FROM industry_skills WHERE skill_key = 'civil_exam_essay'
ON CONFLICT (skill_id, industry, role) DO NOTHING;
