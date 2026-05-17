-- Fix skills that failed due to Chinese curly quotes in JSON labels

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
  '{"fields": [{"name": "judgment_content", "type": "textarea", "label": "判决书内容（粘贴全文或关键段落）", "required": true, "max_length": 20000, "supports_upload": ["pdf", "txt"]}, {"name": "analysis_focus", "type": "text", "label": "重点关注方向（可选，如：证据标准、违约金认定）", "required": false, "max_length": 200}]}'::jsonb,
  true, 27, false, 1
) ON CONFLICT (skill_key) DO UPDATE SET
  input_schema = EXCLUDED.input_schema,
  updated_at = now();

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
  '{"fields": [{"name": "contract_content", "type": "textarea", "label": "合同内容（粘贴全文或关键条款）", "required": true, "max_length": 20000, "supports_upload": ["pdf", "docx", "txt"]}, {"name": "review_focus", "type": "text", "label": "重点审查方向（如：违约责任、付款条款）", "required": false, "max_length": 300}]}'::jsonb,
  true, 28, false, 1
) ON CONFLICT (skill_key) DO UPDATE SET
  input_schema = EXCLUDED.input_schema,
  updated_at = now();

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
  '{"fields": [{"name": "literature_content", "type": "textarea", "label": "文献内容（摘要或全文）", "required": true, "max_length": 15000, "supports_upload": ["pdf", "txt"]}, {"name": "focus_angle", "type": "text", "label": "重点关注角度（如：治疗效果、安全性、亚组分析）", "required": false, "max_length": 200}]}'::jsonb,
  true, 32, false, 1
) ON CONFLICT (skill_key) DO UPDATE SET
  input_schema = EXCLUDED.input_schema,
  updated_at = now();

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
  '{"fields": [{"name": "case_summary", "type": "textarea", "label": "患者病情摘要（主诉、现病史、体征）", "required": true, "max_length": 3000}, {"name": "test_results", "type": "textarea", "label": "已完成的检查结果", "required": false, "max_length": 3000}, {"name": "discussion_focus", "type": "text", "label": "讨论重点（如：明确诊断、调整治疗方案）", "required": false, "max_length": 200}]}'::jsonb,
  true, 34, false, 1
) ON CONFLICT (skill_key) DO UPDATE SET
  input_schema = EXCLUDED.input_schema,
  updated_at = now();

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
  '{"fields": [{"name": "transaction_type", "type": "select", "label": "交易类型", "required": true, "options": ["股权收购", "资产收购", "增资入股", "战略投资", "合并重组", "供应商合作尽调"]}, {"name": "target_info", "type": "textarea", "label": "目标公司基本情况（行业、规模、主营业务）", "required": true, "max_length": 1000}, {"name": "focus_areas", "type": "text", "label": "重点关注领域（如：知识产权、劳动风险）", "required": false, "max_length": 300}]}'::jsonb,
  true, 38, false, 1
) ON CONFLICT (skill_key) DO UPDATE SET
  input_schema = EXCLUDED.input_schema,
  updated_at = now();

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
  '{"fields": [{"name": "essay_theme", "type": "textarea", "label": "申论材料核心主题（简述材料主要内容和背景）", "required": true, "max_length": 1000}, {"name": "essay_requirement", "type": "textarea", "label": "题目要求（完整题目要求）", "required": true, "max_length": 500}, {"name": "word_count", "type": "text", "label": "字数要求（如：1000-1200字）", "required": false, "max_length": 50}]}'::jsonb,
  true, 43, false, 1
) ON CONFLICT (skill_key) DO UPDATE SET
  input_schema = EXCLUDED.input_schema,
  updated_at = now();
