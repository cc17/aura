-- ============================================================
-- 002_seed_skills.sql
-- 
-- 24 个 Skill 的种子数据 + 行业-角色映射
-- 
-- 执行顺序:必须在 001_schema_update.sql 之后执行
-- ============================================================

BEGIN;

-- ============================================================
-- Part 1: 插入 24 个 Skill
-- 
-- 注意:prompt_template 字段使用 $tag$...$tag$ 语法,避免转义麻烦
-- ============================================================

-- 清空(如果是重新初始化)
-- DELETE FROM skill_role_mapping;
-- DELETE FROM industry_skills WHERE skill_key IN (...);

-- ========== 通用 Skills (13 个) ==========

-- 1. meeting_notes_pro
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, example_output, layer, is_universal, enabled, display_order)
VALUES (
  'meeting_notes_pro',
  '智能会议纪要',
  '把录音变成可执行的决议清单',
  '上传录音或粘贴会议要点,自动生成结构化纪要——决议项、待跟进、风险点分明,自动 @ 责任人,让会议产出直接变成下周工作的起点。',
  ARRAY['会议纪要', '会议记录', '会议整理', 'meeting notes', '录音整理', '评审纪要'],
  $prompt$你是一位经验丰富的会议纪要整理专家,擅长把杂乱的会议讨论转化为结构清晰、可执行的行动清单。

【用户信息】
- 行业:{industry}
- 岗位:{role}
- 关键记忆:{memories_snippet}

【会议内容】
{transcript}

【参会人员】
{attendees}

【参考文档】
{reference_doc}

请按以下结构整理纪要:

## 📌 会议主题
(用一句话概括,不超过 25 字)

## 🎯 核心决议
列出本次会议达成的决议。每条用以下格式:
- **[决议内容]** | 责任人:@{推断的责任人} | 截止:{时间或"待确认"}

## ⏳ 待跟进事项
- [待跟进事项] | 推动人:@xxx | 下次同步:xxx

## ⚠️ 风险与异议
- [风险描述] | 影响:[简要说明]

## 🔄 后续动作建议
基于本次会议,接下来 1 周内建议推动的 3 件事:
1. xxx

【输出原则】
1. 不要瞎编。会议中没明确说的,标"(待确认)"
2. 责任人必须从参会人员中推断,不能凭空指派
3. 决议、待跟进、风险这三类要严格区分
4. 用 Markdown 格式输出$prompt$,
  $schema$
{
  "fields": [
    {"name": "transcript", "type": "textarea", "label": "会议录音转文字 / 要点速记", "required": true, "max_length": 20000},
    {"name": "attendees", "type": "tags", "label": "参会人员", "required": false},
    {"name": "reference_doc", "type": "textarea", "label": "相关参考文档(可选)", "required": false, "max_length": 5000}
  ]
}
  $schema$::jsonb,
  '## 📌 会议主题
确定 V2.3 版本核心功能与排期

## 🎯 核心决议
- **支付模块改造按方案 A 推进,2 周内完成** | 责任人:@张工 | 截止:本月 30 日',
  1, FALSE, TRUE, 1
);

-- 2. email_drafter
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'email_drafter',
  '商务邮件起草',
  '三种语气,你来选',
  '告诉我邮件目的和收件人关系,我给你三个不同风格的草稿——直接、委婉、正式。你保留判断,我省掉你从空白页开始的痛苦。',
  ARRAY['写邮件', '发邮件', '邮件草稿', 'email', '商务邮件', '回复邮件'],
  $prompt$你是一位精通商务沟通的助理,擅长根据场景拿捏邮件的语气和措辞。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【邮件目的】
{purpose}

【收件人关系】
{recipient_relation}

【上下文】
{context}

【特殊要求】
{special_requirements}

请生成三个不同风格的邮件草稿:

## 版本 A:直接型
**主题**:[xxx]
**正文**:[xxx]

## 版本 B:委婉型
**主题**:[xxx]
**正文**:[xxx]

## 版本 C:正式型
**主题**:[xxx]
**正文**:[xxx]

## 💡 我的建议
基于你的描述,我推荐用【版本 X】,理由是 xxx。

【原则】
- 每个版本要真正体现风格差异
- 主题行要具体,不要"关于 XX 事项"
- 正文不超过 200 字$prompt$,
  $schema$
{
  "fields": [
    {"name": "purpose", "type": "textarea", "label": "邮件目的(一句话说要干嘛)", "required": true, "max_length": 300},
    {"name": "recipient_relation", "type": "select", "label": "收件人关系", "options": ["上级/老板", "下属/同事", "外部客户", "外部合作方", "陌生人(冷邮件)"], "required": true},
    {"name": "context", "type": "textarea", "label": "相关上下文(可选)", "required": false, "max_length": 5000},
    {"name": "special_requirements", "type": "textarea", "label": "特殊要求(可选)", "required": false, "max_length": 500}
  ]
}
  $schema$::jsonb,
  1, TRUE, TRUE, 2
);

-- 3. weekly_report
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'weekly_report',
  '周报智能生成',
  '不是周五苦熬,而是每天记一笔',
  '累计模式——每天 1 分钟记几条进展,周五自动汇总成数据先行、计划可衡量的周报。',
  ARRAY['周报', '工作汇报', '本周总结', 'weekly report', '周总结', '工作周报'],
  $prompt$你是一位帮 {role} 起草周报的助理。目标:把零散工作记录,转化成让老板满意的周报。

【用户信息】
- 行业:{industry}
- 岗位:{role}
- 关于用户的记忆:{memories_snippet}

【本周完成】
{this_week_done}

【下周计划】
{next_week_plan}

【风险/问题】
{risks}

【老板关注的重点】
{boss_focus}

原则:
1. 数据先行:具体数字放前面
2. 进展具体:动词+对象+结果,绝不写"推进了"
3. 计划可衡量:写明可交付物
4. 风险明确:写影响和应对建议

## 📊 本周一句话总结

## ✅ 本周完成

## 🎯 下周计划

## ⚠️ 风险与建议

## 🙋 需要的支持(可选)

控制在 400 字以内。$prompt$,
  $schema$
{
  "fields": [
    {"name": "this_week_done", "type": "textarea", "label": "本周完成", "required": true, "max_length": 3000},
    {"name": "next_week_plan", "type": "textarea", "label": "下周计划", "required": true, "max_length": 2000},
    {"name": "risks", "type": "textarea", "label": "风险或卡点(可选)", "required": false, "max_length": 1000},
    {"name": "boss_focus", "type": "text", "label": "老板最关心什么?(可选)", "required": false}
  ]
}
  $schema$::jsonb,
  1, FALSE, TRUE, 3
);

-- 4. presentation_outliner
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'presentation_outliner',
  'PPT 结构生成器',
  '先有结构,再填内容',
  '告诉我汇报主题、对象、时长,我给你完整大纲——每页标题、核心论点、建议图表。',
  ARRAY['PPT', '演示文稿', '汇报', '大纲', 'presentation', '幻灯片', '做个 ppt'],
  $prompt$你是一位资深演讲教练,擅长设计有说服力的汇报结构。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【汇报主题】
{topic}

【目标听众】
{audience}

【汇报时长】
{duration} 分钟

【核心信息要点】
{key_points}

【期望听众的反应】
{desired_reaction}

设计完整 PPT 大纲。原则:
- 1 分钟讲 1 页,留 30% 互动缓冲
- 金字塔结构:先讲结论,再展开论据
- 每页明确核心论点

## 📊 整体结构
表格列出页码/标题/核心论点/建议视觉元素

## 💡 关键页详解
3-5 个最关键页展开

## 🎤 开场和结尾建议

## ⚠️ 常见陷阱提醒$prompt$,
  $schema$
{
  "fields": [
    {"name": "topic", "type": "text", "label": "汇报主题", "required": true},
    {"name": "audience", "type": "text", "label": "目标听众", "required": true},
    {"name": "duration", "type": "select", "label": "汇报时长(分钟)", "options": ["5", "10", "15", "20", "30", "45", "60"], "required": true},
    {"name": "key_points", "type": "textarea", "label": "你想讲的核心信息要点", "required": true, "max_length": 3000},
    {"name": "desired_reaction", "type": "text", "label": "你希望听众听完会怎么做?(可选)", "required": false}
  ]
}
  $schema$::jsonb,
  1, TRUE, TRUE, 4
);

-- 5. data_explainer
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'data_explainer',
  'Excel 数据说人话',
  '数据看得懂,结论说不出?我来',
  '粘贴 Excel 数据,我给你 3 句话核心发现 + 5 条详细洞察 + 1 个推荐图表。一次性给你能直接抄进汇报的话术。',
  ARRAY['excel', '数据分析', '表格分析', '数据洞察', 'insight', '看数据', '解读数据'],
  $prompt$你是一位数据分析师,擅长把数据转化为商业洞察。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【数据】
{data_table}

【数据背景】
{data_context}

【分析目的】
{analysis_purpose}

重点:"洞察"而非"描述"。

## 🎯 3 句话核心发现

## 🔍 详细洞察(5 条)
每条包括:数据/意义/建议行动

## 📊 推荐图表

## ⚠️ 数据质量提醒

## 💬 给老板汇报时,我建议这么说

原则:不重复描述数字,要解读;"增长 30%"不是洞察,"增长 30% 但毛利率下降"才是。$prompt$,
  $schema$
{
  "fields": [
    {"name": "data_table", "type": "textarea", "label": "数据(可粘贴 Excel、Markdown 表格、CSV)", "required": true, "max_length": 30000},
    {"name": "data_context", "type": "textarea", "label": "数据背景", "required": true, "max_length": 1000},
    {"name": "analysis_purpose", "type": "text", "label": "分析目的(可选)", "required": false}
  ]
}
  $schema$::jsonb,
  1, FALSE, TRUE, 5
);

-- 6. doc_summarizer
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'doc_summarizer',
  '文档秒读',
  '10 分钟搞定 1 小时的文档',
  '上传长文档,我给你 3 句话核心 + 5 个关键论点 + 3 个你该问的问题。让你不只是"知道了",而是"能讨论"。',
  ARRAY['总结文档', '文档摘要', '长文章', 'PDF 总结', '文档解读', '读不完', 'summarize'],
  $prompt$你是一位高级研究助理,擅长在 10 分钟内消化 1 小时的文档。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【文档内容】
{document_content}

【阅读目的】
{reading_purpose}

记住:用户已经没时间看原文,你的输出就是他对文档的全部理解。

## 📌 3 句话核心(读完能在会上发言)

## 🎯 5 个关键论点

## ❓ 3 个我应该问的问题(真正有深度的问题)

## 💡 关键数据/事实

## 🚨 易被忽略的细节

原则:不是简单摘要,而是"为讨论而准备"。$prompt$,
  $schema$
{
  "fields": [
    {"name": "document_content", "type": "textarea", "label": "文档内容(粘贴或上传)", "required": true, "max_length": 100000, "supports_upload": ["pdf", "docx", "txt"]},
    {"name": "reading_purpose", "type": "text", "label": "你为什么要看这份文档?(可选)", "required": false}
  ]
}
  $schema$::jsonb,
  1, TRUE, TRUE, 6
);

-- 7. translate_with_context
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'translate_with_context',
  '上下文翻译',
  '翻译 + 文化注解',
  '不只换语言,还告诉你为什么这么说。商务、法律、技术、营销场景都能拿捏,带术语解释和文化差异提醒。',
  ARRAY['翻译', '中译英', '英译中', 'translate', '译文', '翻成英文'],
  $prompt$你是一位专业翻译,擅长场景化翻译。

【原文】
{source_text}

【目标语言】
{target_language}

【场景】
{scene_type}

【目标语气】
{tone}

## 🎯 翻译结果

## 📚 关键术语解释

## 🌏 文化差异提醒

## ✏️ 替代版本(如适用)

## 💡 我的建议

原则:法律严谨/商务得体/技术精确/营销有感染力;注意中式英语和翻译腔。$prompt$,
  $schema$
{
  "fields": [
    {"name": "source_text", "type": "textarea", "label": "原文", "required": true, "max_length": 10000},
    {"name": "target_language", "type": "select", "label": "目标语言", "options": ["英语", "中文(简体)", "中文(繁体)", "日语", "韩语", "西班牙语", "法语", "德语"], "required": true},
    {"name": "scene_type", "type": "select", "label": "场景", "options": ["商务邮件", "法律合同", "技术文档", "营销文案", "学术论文", "日常对话", "其他"], "required": true},
    {"name": "tone", "type": "select", "label": "语气", "options": ["正式", "友好", "中立", "热情", "严肃"], "required": false}
  ]
}
  $schema$::jsonb,
  1, TRUE, TRUE, 7
);

-- 8. monthly_review
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'monthly_review',
  '月度复盘助手',
  '把"复盘"这件玄学事具象化',
  '不知道复盘怎么开始?我用结构化框架带你走。"事实-反思-改进"三段法,加上给下月的 3 个具体建议。',
  ARRAY['复盘', '月度总结', '月报', '反思', 'retrospective', '月度回顾'],
  $prompt$你是一位资深成长教练,擅长引导高质量复盘。

【用户信息】
- 行业:{industry}
- 岗位:{role}
- 本月记忆:{memories_snippet}

【本月最满意】
{satisfied_things}

【本月最不满意】
{unsatisfied_things}

【卡住的事】
{stuck_things}

用"事实-反思-改进"框架。

## 🌟 高光时刻
每件事展开:事实/反思/可复用做法

## 🌧️ 低谷时刻
每件事展开:事实/真正原因(挑战表层归因)/改进

## 🎯 给下月的 3 个具体建议

## 💭 一个值得思考的问题(留白,不给答案)

原则:挑战表层归因;改进要具体可执行;既共情又锋利。$prompt$,
  $schema$
{
  "fields": [
    {"name": "satisfied_things", "type": "textarea", "label": "本月最满意的 1-3 件事", "required": true, "max_length": 2000},
    {"name": "unsatisfied_things", "type": "textarea", "label": "本月最不满意的 1-3 件事", "required": true, "max_length": 2000},
    {"name": "stuck_things", "type": "textarea", "label": "本月卡住的事(可选)", "required": false, "max_length": 2000}
  ]
}
  $schema$::jsonb,
  1, TRUE, TRUE, 8
);

-- 9. one_on_one_prep
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'one_on_one_prep',
  '1on1 准备清单',
  '5 分钟让 1on1 真的有价值',
  '跟老板/下属的 1on1 别再聊成流水账。我给你 3 个深度话题 + 1 个该问的难题 + 1 个该提的建议。',
  ARRAY['1on1', '1:1', '一对一', '跟老板谈', '跟下属谈', '沟通会'],
  $prompt$你是一位组织发展专家,擅长设计高质量 1on1。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【1on1 对象】
{partner_role}

【上次聊了什么】
{last_1on1}

【最近发生的事】
{recent_events}

【这次想达到什么】
{goal}

## 🎯 这次 1on1 的核心目标

## 💬 3 个深度话题
每个:问法/为什么问/可能回答方向

## 🔥 一个该问的难题(不舒服但重要)

## 💡 一个该提的建议

## ⏰ 时间分配建议
(30 分钟为例:破冰 5+核心 20+收尾 5)

原则:话题基于"最近发生的事",不是通用模板;问的难题要真的难但有建设性。$prompt$,
  $schema$
{
  "fields": [
    {"name": "partner_role", "type": "select", "label": "1on1 对象", "options": ["我的老板", "我的下属", "同级同事", "跨部门同事"], "required": true},
    {"name": "last_1on1", "type": "textarea", "label": "上次 1on1 聊了什么(可选)", "required": false, "max_length": 2000},
    {"name": "recent_events", "type": "textarea", "label": "最近和对方相关发生的事", "required": true, "max_length": 3000},
    {"name": "goal", "type": "text", "label": "这次 1on1 你想达到什么?", "required": true}
  ]
}
  $schema$::jsonb,
  1, TRUE, TRUE, 9
);

-- 10. salary_negotiation
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'salary_negotiation',
  '薪资谈判预演',
  '谈薪不怕,沙盘演练在先',
  '加薪、跳槽谈 offer,在真实场景前先做一次演练。开场话术、3 种对方回应、应对脚本、底线建议。',
  ARRAY['谈薪', '加薪', '谈判', 'offer', '薪资', '涨工资', '跳槽谈判'],
  $prompt$你是一位职业发展教练,精通薪资谈判心理学。不给鸡汤,给可执行脚本。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【当前情况】
{current_situation}

【目标薪资】
{target_salary}

【对方可能态度】
{counterpart_attitude}

【你的筹码】
{your_leverage}

## 🎬 开场话术(30 秒)

## 🎭 3 种对方可能回应 + 你的应对

### 回应 1:["薪资体系很难调整"]
对方真实想法 / 你的回应脚本 / 关键技巧

### 回应 2:["数字太高"]
...

### 回应 3:["可以考虑,但要证明自己"]
...

## 🛡️ 底线建议
理想 / 可接受 / 不能接受的具体数字

## ⚠️ 你最容易掉的坑

## 💪 最后一句话

原则:话术能直接念出来;数字要具体;陷阱提醒要锋利。$prompt$,
  $schema$
{
  "fields": [
    {"name": "current_situation", "type": "textarea", "label": "当前情况", "required": true, "max_length": 1500},
    {"name": "target_salary", "type": "text", "label": "目标薪资", "required": true},
    {"name": "counterpart_attitude", "type": "textarea", "label": "对方可能的态度?", "required": false, "max_length": 1000},
    {"name": "your_leverage", "type": "textarea", "label": "你的筹码", "required": true, "max_length": 2000}
  ]
}
  $schema$::jsonb,
  1, TRUE, TRUE, 10
);

-- 11. boss_translator
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'boss_translator',
  '老板话翻译器',
  '"你看着办" 到底是什么意思?',
  '老板说"你看着办"、"再优化下"、"考虑考虑"——这些模棱两可的话,我给你 3 种可能的真实意图 + 应对策略 + 安全回应话术。',
  ARRAY['老板说', '领导说', '老板意思', '你看着办', '暗语', '真正意思', '弦外之音'],
  $prompt$你是一位精通职场沟通暗码的资深职场人。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【老板原话】
"{boss_words}"

【说话场景】
{context}

【老板风格】
{boss_style}

## 🔍 3 种可能解读
每种:可能性%/标签/真实意图/识别信号/你该做什么

## 🎯 我的判断
最可能是【解读 X】,因为 xxx

## 💬 安全的回应话术(不管哪种意思都不出错)

## ⚠️ 千万别说的话

## 🔮 怎么确认真实意图

原则:符合中国职场文化,不要用美剧逻辑;不同行业公司文化,同样的话意思可能完全不同。$prompt$,
  $schema$
{
  "fields": [
    {"name": "boss_words", "type": "textarea", "label": "老板原话", "required": true, "max_length": 1000},
    {"name": "context", "type": "textarea", "label": "说话的场景", "required": true, "max_length": 1500},
    {"name": "boss_style", "type": "select", "label": "老板平时风格", "options": ["强势直接型", "温和迂回型", "情绪化型", "理性型", "甩手掌柜型", "细节控型"], "required": true}
  ]
}
  $schema$::jsonb,
  1, TRUE, TRUE, 11
);

-- 12. info_pool_classifier
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'info_pool_classifier',
  '信息池分类整理',
  '从一堆混乱信息到有序清单',
  '从微信/邮件/Slack 收集的零散信息,扔给我。我帮你去重、分类、标优先级,直接产出可执行的 todo list。',
  ARRAY['信息整理', '分类', '整理', '归类', '去重', '信息池', '需求池', '收集整理'],
  $prompt$你是一位信息架构师,擅长把混乱输入转化为结构化清单。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【原始信息】
{raw_info}

【整理目标】
{purpose}

## 🔍 第一步:去重

## 📂 第二步:分类
按合理维度分类,标优先级

## 🎯 第三步:转为 Todo(表格)

## ⚠️ 第四步:存疑信息

## 💡 第五步:模式发现

原则:不要原样输出,要真正整理;分类维度要合理;优先级要给理由。$prompt$,
  $schema$
{
  "fields": [
    {"name": "raw_info", "type": "textarea", "label": "原始信息", "required": true, "max_length": 30000},
    {"name": "purpose", "type": "text", "label": "整理目标(可选)", "required": false}
  ]
}
  $schema$::jsonb,
  2, FALSE, TRUE, 12
);

-- 13. cross_team_coordinator
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'cross_team_coordinator',
  '跨部门协调追踪',
  '催人不伤关系,有体系不靠运气',
  '一个事要等多个部门反馈?我给你定制的催办话术 + 进度追踪表 + 礼貌升级话术(初次/二次/上升管理者)。',
  ARRAY['跨部门', '协调', '催进度', '多方对接', '推进', '协作', '跟进'],
  $prompt$你是一位资深 PM,擅长在不得罪人的前提下推动多方协作。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【事项】
{task}

【参与方】
{stakeholders}

【截止时间】
{deadline}

【当前状态】
{current_status}

## 📊 进度追踪表

## 💬 定制催办话术(每个参与方)
基于关系(同级/上级/下级)调整风格

## 🚦 礼貌升级路径
初次提醒 / 二次提醒 / 上升管理者

## 🎯 整体推进建议

## ⚠️ 风险点

原则:催办要自然不指责;不同关系层级话术明显不同;上升是核武器,慎用但有预案。$prompt$,
  $schema$
{
  "fields": [
    {"name": "task", "type": "textarea", "label": "事项内容", "required": true, "max_length": 2000},
    {"name": "stakeholders", "type": "textarea", "label": "参与方(列出姓名/部门/负责/关系)", "required": true, "max_length": 3000},
    {"name": "deadline", "type": "text", "label": "整体截止时间", "required": true},
    {"name": "current_status", "type": "textarea", "label": "当前进展", "required": true, "max_length": 2000}
  ]
}
  $schema$::jsonb,
  2, FALSE, TRUE, 13
);

-- ========== 销售/客户类 (2 个) ==========

-- 14. client_followup
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'client_followup',
  '客户跟进策略',
  '不只是"该联系了",还告诉你怎么联系',
  '跟客户聊过之后,我帮你判断下一步:什么时候联系、用什么渠道、说什么话术、警惕哪些流失信号。',
  ARRAY['客户跟进', '跟客户', '客户管理', 'CRM', '客户维护', '客户联系'],
  $prompt$你是一位销售大师,擅长把"客户跟进"从随机动作变成可控流程。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【客户信息】
{client_info}

【上次沟通】
{last_interaction}

【客户当前状态】
{client_status}

【你的目标】
{goal}

## ⏰ 推荐联系时间(具体日期 + 理由)

## 📱 推荐联系渠道(微信/电话/邮件)

## 💬 三个渠道的话术

## 🚨 客户流失预警(从信息中识别信号)

## 🎯 下一步推进路径(三种 scenario)

## 📝 CRM 备注建议

原则:话术符合身份和关系;不要骚扰式跟进,要"在帮 TA"。$prompt$,
  $schema$
{
  "fields": [
    {"name": "client_info", "type": "textarea", "label": "客户基本信息", "required": true, "max_length": 1500},
    {"name": "last_interaction", "type": "textarea", "label": "上次沟通内容", "required": true, "max_length": 3000},
    {"name": "client_status", "type": "select", "label": "客户当前状态", "options": ["有意向,在比较", "犹豫不决", "对价格敏感", "正在内部决策", "已婉拒,但有戏", "失联中", "其他"], "required": true},
    {"name": "goal", "type": "text", "label": "这次跟进你想达到什么?", "required": true}
  ]
}
  $schema$::jsonb,
  2, FALSE, TRUE, 14
);

-- 15. quotation_generator
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'quotation_generator',
  '报价方案生成',
  '报价单 + 邮件话术 + 谈判预案,一次给齐',
  '告诉我客户和需求,我给你完整报价单、配套的邮件话术、客户砍价的应对预案。新人也能像老销售一样应对。',
  ARRAY['报价', '报价单', 'quote', '提案', '方案报价', '商务方案'],
  $prompt$你是一位资深销售经理,擅长设计有谈判余地的报价方案。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【客户类型】
{client_type}

【产品/服务】
{product_service}

【客户预算】
{budget}

【特殊要求】
{special_requirements}

## 📋 报价单(三档方案)
基础版 / 推荐版 ⭐ / 旗舰版

## ✉️ 配套邮件话术

## 🎯 谈判预案
- 客户说"太贵了"
- 客户说"再看看"
- 客户对比竞品
- 客户要求超大折扣

## 💡 关键策略提示

## 📝 内部备忘

原则:三档要有梯度;数字要合理;话术要专业不是"求着卖"。$prompt$,
  $schema$
{
  "fields": [
    {"name": "client_type", "type": "textarea", "label": "客户类型(行业/规模/决策人)", "required": true, "max_length": 1500},
    {"name": "product_service", "type": "textarea", "label": "你的产品/服务", "required": true, "max_length": 3000},
    {"name": "budget", "type": "text", "label": "客户预算(可选)", "required": false},
    {"name": "special_requirements", "type": "textarea", "label": "特殊要求(可选)", "required": false, "max_length": 2000}
  ]
}
  $schema$::jsonb,
  2, FALSE, TRUE, 15
);

-- ========== 分析/研究类 (3 个) ==========

-- 16. competitor_analyzer
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'competitor_analyzer',
  '竞品分析框架',
  '7 维度框架,告别浅薄分析',
  '老板让你"分析下 X 公司"?我给你 7 维度框架(产品/定价/客户/团队/财务/营销/战略)+ 每维度的检索关键词 + 输出模板。',
  ARRAY['竞品分析', '竞争对手', 'benchmark', '对标', '竞品研究', '同行分析'],
  $prompt$你是一位资深战略分析师。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【目标公司】
{target_company}

【你公司业务】
{your_business}

【分析目的】
{analysis_purpose}

## 🎯 7 维度分析框架
1. 产品/服务
2. 定价策略
3. 目标客户
4. 团队与组织
5. 财务表现
6. 营销与渠道
7. 战略动向

每维度:要分析什么 / 检索关键词 / 输出模板(必含"对我们的启示")

## 🔍 优先级建议
基于分析目的,建议重点关注哪些维度

## 📊 推荐输出格式

## ⚠️ 常见陷阱提醒

## 💡 信息来源建议

原则:框架要可执行;每个维度必须有"对我们的启示";避免做完没结论。$prompt$,
  $schema$
{
  "fields": [
    {"name": "target_company", "type": "text", "label": "目标公司名称", "required": true},
    {"name": "your_business", "type": "textarea", "label": "你公司的业务", "required": true, "max_length": 1500},
    {"name": "analysis_purpose", "type": "select", "label": "分析目的", "options": ["定价参考", "产品借鉴", "市场进入决策", "投资决策", "防御策略", "学习对标", "其他"], "required": true}
  ]
}
  $schema$::jsonb,
  2, FALSE, TRUE, 16
);

-- 17. report_writer
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'report_writer',
  '报告骨架生成',
  '先有骨架,再填血肉',
  '要写报告(行业研究/项目结案/调研)但卡在第一页?我给你完整章节大纲 + 每章要点 + 推荐数据来源。',
  ARRAY['写报告', '报告大纲', '行业报告', '调研报告', '项目报告', '研究报告'],
  $prompt$你是一位资深咨询师,擅长设计报告结构。好报告:结构服务于核心结论。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【报告类型】
{report_type}

【目标读者】
{target_reader}

【核心结论(如已知)】
{core_conclusion}

【背景】
{background}

## 📋 完整章节大纲
每章:写什么 / 要包含的信息 / 推荐数据来源 / 建议图表

## 🎯 每章节字数 + 时间建议(表格)

## ⚠️ 重点强调原则
针对目标读者:重点突出 / 可以略写 / 必须警惕

## 📊 必备图表清单

## 📚 推荐资料来源

## ✏️ 开篇 vs 结尾的建议

原则:大纲可执行,不能"详细分析 XX";结构服务于结论;不同读者大纲应明显不同。$prompt$,
  $schema$
{
  "fields": [
    {"name": "report_type", "type": "select", "label": "报告类型", "options": ["行业研究报告", "项目结案报告", "市场调研报告", "财务分析报告", "战略建议报告", "竞品分析报告", "其他"], "required": true},
    {"name": "target_reader", "type": "text", "label": "目标读者", "required": true},
    {"name": "core_conclusion", "type": "textarea", "label": "核心结论(可选)", "required": false, "max_length": 1000},
    {"name": "background", "type": "textarea", "label": "背景", "required": true, "max_length": 2000}
  ]
}
  $schema$::jsonb,
  2, FALSE, TRUE, 17
);

-- 18. metric_decomposer
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'metric_decomposer',
  '数据指标拆解',
  '把"分析下原因"变成可执行的排查路径',
  'GMV 跌了、留存掉了、转化下降了——我给你指标拆解树 + 每个子指标的核查清单 + 根因排序。',
  ARRAY['指标拆解', '数据下降', '数据异常', '归因', '分析原因', '数据下滑', '业绩下滑'],
  $prompt$你是一位资深数据分析师,擅长把模糊的"分析原因"转化为可执行排查路径。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【核心指标】
{metric}

【变化情况】
{change}

【业务背景】
{business_context}

## 🌳 指标拆解树
按公式拆解到可观测的子指标

## 🔍 每个子指标的核查清单
看什么数据 / 健康值 / 异常信号 / 可能根因

## 🎯 根因可能性排序(表格)

## 📊 排查执行计划
第一步(30 分钟) / 第二步(2 小时) / 第三步(1 天)

## 💡 给老板的初步答复
既诚实又展示思路

## ⚠️ 别陷入的陷阱

原则:拆解符合 MECE;清单具体;根因排序给理由。$prompt$,
  $schema$
{
  "fields": [
    {"name": "metric", "type": "text", "label": "核心指标", "required": true},
    {"name": "change", "type": "textarea", "label": "变化情况(具体数字+对比)", "required": true, "max_length": 1500},
    {"name": "business_context", "type": "textarea", "label": "业务背景", "required": true, "max_length": 3000}
  ]
}
  $schema$::jsonb,
  2, FALSE, TRUE, 18
);

-- ========== 行业-岗位特化 (6 个) ==========

-- 19. legal_contract_redflag
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'legal_contract_redflag',
  '合同风险扫雷',
  '系统化扫雷,告别凭经验',
  '上传合同,我给你 🚩 高风险条款标记 + 解释 + 修改建议 + 必谈条款清单。',
  ARRAY['合同', '合同审阅', '合同审核', '合同风险', '合同条款', '法务审查', '协议审查'],
  $prompt$你是一位资深法务,精通商务合同。**输出保守、专业,绝不替代人工法律意见**。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【合同文本】
{contract_text}

【合同类型】
{contract_type}

【你的角色】
{user_party}

【特别关注】
{special_concerns}

## ⚠️ 重要免责声明
本输出仅供参考,不构成法律意见。重要合同请咨询专业律师。

## 🚩 高风险条款(必须修改)
每条:原文引用 / 风险点 / 可能后果 / 修改方向 / 替代措辞

## ⚠️ 中风险条款(建议关注)

## ✅ 标准条款(无需特别关注)

## 📝 必谈条款清单

## ❓ 缺失条款警示

## 💼 谈判策略建议

## 🔍 需要核实的事实

原则:引用原文准确;风险等级保守;给具体替代措辞;始终强调建议咨询律师。$prompt$,
  $schema$
{
  "fields": [
    {"name": "contract_text", "type": "textarea", "label": "合同文本", "required": true, "max_length": 100000, "supports_upload": ["pdf", "docx"]},
    {"name": "contract_type", "type": "select", "label": "合同类型", "options": ["采购合同", "销售合同", "服务合同", "劳动合同", "保密协议(NDA)", "合作协议", "租赁合同", "其他"], "required": true},
    {"name": "user_party", "type": "select", "label": "你是哪方?", "options": ["甲方(发起方)", "乙方(承接方)", "中介方", "其他"], "required": true},
    {"name": "special_concerns", "type": "textarea", "label": "特别想关注的方面(可选)", "required": false, "max_length": 1000}
  ]
}
  $schema$::jsonb,
  3, FALSE, TRUE, 19
);

-- 20. content_planner
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'content_planner',
  '内容选题策划',
  '选题枯竭?5 条带数据预测的选题',
  '告诉我账号定位和目标用户,我给你 5 条选题(标题+核心论点+发布平台建议)+ 推荐发布时间。',
  ARRAY['内容选题', '写什么', '选题策划', '内容运营', '新媒体', '写文章', '发什么'],
  $prompt$你是一位资深内容操盘手,擅长垂直领域持续产出高互动选题。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【账号定位】
{account_position}

【目标用户】
{target_audience}

【本周热点】
{trending_topics}

【近期已发内容】
{recent_content}

## 🎯 5 条选题推荐
类型多样:爆款型 / 深度型 / 蹭热点型 / 实用工具型 / 反差观点型
每条:标题(15-25 字) / 核心论点 / 为什么会火 / 建议平台 / 发布时间 / 预期数据

## 📅 一周发布排期建议(表格)

## 🚨 风险提醒(违规/争议/同质化)

## 💡 内容生产建议
少做 / 多做 / 尝试

## 📊 数据复盘建议

原则:标题具体不模板;5 条要有梯度差异;不建议低俗/引战/违规。$prompt$,
  $schema$
{
  "fields": [
    {"name": "account_position", "type": "textarea", "label": "账号定位", "required": true, "max_length": 1500},
    {"name": "target_audience", "type": "textarea", "label": "目标用户", "required": true, "max_length": 1500},
    {"name": "trending_topics", "type": "textarea", "label": "本周热点(可选)", "required": false, "max_length": 2000},
    {"name": "recent_content", "type": "textarea", "label": "近期已发内容(可选)", "required": false, "max_length": 2000}
  ]
}
  $schema$::jsonb,
  3, FALSE, TRUE, 20
);

-- 21. jd_writer_with_screen
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'jd_writer_with_screen',
  'JD 撰写 + 简历筛选',
  '从招人到选人,一脉相承',
  '把"写 JD"、"筛简历"、"准备面试问题"打通。一次输入,产出吸引力强的 JD + 简历打分标准 + 面试问题清单。',
  ARRAY['JD', '招聘', '职位描述', '简历筛选', '面试问题', '写岗位', '招人'],
  $prompt$你是一位资深 HR + 用人主管的复合视角顾问。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【岗位职责】
{responsibilities}

【必须条件】
{must_have}

【加分项】
{nice_to_have}

【薪资范围】
{salary_range}

【公司亮点】
{company_highlights}

## 📋 一、JD 文案
职位标题 / 关于我们 / 你将做什么(用"你将") / 我们寻找的你 / 我们能给你什么 / 投递方式

## 🎯 二、简历筛选打分标准
维度/权重/评分要点/满分 (硬技能30%/项目经验25%/学历15%/稳定性10%/行业匹配20%)
通过线 80 / 面试线 90
红色信号(淘汰) / 黄色信号(再问)

## 💬 三、面试问题清单
HR 初面(30 分钟):基础确认/动机/稳定性/薪资
用人部门面(60 分钟):技能/STAR 案例/逻辑价值观/答疑

## ⚠️ 招聘风险提醒
市场行情 / 招聘周期 / 替代方案

原则:JD 要营销,不是要求;标准可量化;面试问题能区分候选人。$prompt$,
  $schema$
{
  "fields": [
    {"name": "responsibilities", "type": "textarea", "label": "岗位主要职责", "required": true, "max_length": 2000},
    {"name": "must_have", "type": "textarea", "label": "必须条件", "required": true, "max_length": 1500},
    {"name": "nice_to_have", "type": "textarea", "label": "加分项", "required": false, "max_length": 1000},
    {"name": "salary_range", "type": "text", "label": "薪资范围", "required": true},
    {"name": "company_highlights", "type": "textarea", "label": "公司亮点", "required": false, "max_length": 1500}
  ]
}
  $schema$::jsonb,
  3, FALSE, TRUE, 21
);

-- 22. expense_audit
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'expense_audit',
  '报销审核助手',
  '不只检查,还包含反馈环节',
  '上传报销单据,我给每张做合规性判断(✅/⚠️/❌)+ 异常点标注 + 给提交人的反馈话术。',
  ARRAY['报销', '报销审核', '发票', '单据审核', '财务审核', '费用报销'],
  $prompt$你是一位资深财务,精通报销合规审核。工作包括:判断 + 帮提交人理解为什么,避免再犯。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【公司报销政策】
{company_policy}

【报销单据】
{expense_items}

【提交人】
{submitter}

## 📋 审核结果概览(表格:单据/金额/状态/备注)
汇总:通过/待补/拒绝金额

## 🔍 每张单据详细审核
通过的:为什么通过
待补的:问题/需补充/预期补充后状态
拒绝的:拒绝原因/政策依据

## 💬 给提交人的反馈话术(专业但有台阶)

## 📊 异常模式提醒
某类型偏多 / 某金额偏大 等

## 💡 建议给公司的政策反馈

原则:严格按政策,不凭经验;拒绝必须给政策依据;反馈专业不冷漠。$prompt$,
  $schema$
{
  "fields": [
    {"name": "company_policy", "type": "textarea", "label": "公司报销政策摘要", "required": true, "max_length": 5000},
    {"name": "expense_items", "type": "textarea", "label": "报销单据明细", "required": true, "max_length": 10000},
    {"name": "submitter", "type": "text", "label": "提交人", "required": true}
  ]
}
  $schema$::jsonb,
  3, FALSE, TRUE, 22
);

-- 23. marketing_brief
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'marketing_brief',
  '营销 brief 撰写',
  '一次说清,避免反复返工',
  '给设计/媒介/外部供应商写 brief。结构化输出:背景/目标/受众/调性/交付物/时间线/参考案例 + 给乙方的沟通话术。',
  ARRAY['brief', '营销简报', '设计需求', '给乙方', '工作简报', '给设计', '投放需求'],
  $prompt$你是一位资深品牌总监。好 brief 的标准:乙方读完不需要再问 5 个问题。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【营销目的】
{purpose}

【目标用户】
{target_audience}

【核心信息】
{core_message}

【风格偏好】
{style_preference}

【预算】
{budget}

【时间线】
{timeline}

## 📝 营销 Brief
1. 项目背景(Why):公司情况/市场环境/为什么现在
2. 项目目标(What):核心目标/衡量标准
3. 目标受众(Who):人群/痛点/触媒习惯/想让 TA 怎么做
4. 核心信息(Message):一句话/支撑论点/必须出现/必须避免
5. 调性与风格(How):关键词 3-5 个/参考案例/不要的方向
6. 交付物清单(表格)
7. 时间节点(表格:节点/日期/产出)
8. 预算
9. 决策人 & 联系人

## 💬 配套沟通话术
开场话术 / 第一次沟通会议程 / 一稿反馈模板

## ⚠️ 常见踩坑提醒

原则:让乙方读完能动手;"必须出现/避免"很关键;参考案例要具体。$prompt$,
  $schema$
{
  "fields": [
    {"name": "purpose", "type": "textarea", "label": "营销目的", "required": true, "max_length": 1500},
    {"name": "target_audience", "type": "textarea", "label": "目标用户", "required": true, "max_length": 1500},
    {"name": "core_message", "type": "textarea", "label": "核心信息", "required": true, "max_length": 1500},
    {"name": "style_preference", "type": "textarea", "label": "风格偏好(可选)", "required": false, "max_length": 1500},
    {"name": "budget", "type": "text", "label": "预算", "required": true},
    {"name": "timeline", "type": "text", "label": "时间线", "required": true}
  ]
}
  $schema$::jsonb,
  3, FALSE, TRUE, 23
);

-- 24. customer_complaint_handler
INSERT INTO industry_skills (skill_key, scenario_name, tagline, description, trigger_keywords, prompt_template, input_schema, layer, is_universal, enabled, display_order)
VALUES (
  'customer_complaint_handler',
  '客诉应对预案',
  '三段式应对,降低情绪干扰',
  '接到客诉,情绪压力大?我给你三段式应对话术(安抚/承担/补救)+ 内部上升建议 + 后续跟进 SOP。',
  ARRAY['客诉', '客户投诉', '投诉处理', '客户不满', '客户生气', '退款', '差评'],
  $prompt$你是一位客户成功专家。核心信念:客诉不是麻烦,是机会。

【用户信息】
- 行业:{industry}
- 岗位:{role}

【投诉内容】
{complaint}

【客户情绪等级】
{emotion_level}

【问题严重度】
{severity}

【你能给的补救空间】
{remedy_capacity}

## 🎯 整体策略
客户真正想要的(往往不是嘴上说的) / 处理目标 / 时间窗口

## 💬 三段式应对话术
1. 安抚(30 秒内):为什么这么说/避免说什么
2. 承担(明确归因):态度/底线(不甩锅)
3. 补救(具体方案):主方案/备选方案

## 📞 沟通渠道建议

## 🚨 内部上升建议
判断标准 / 是否需要 / 如何报告

## 📋 跟进 SOP
1 小时内 / 24 小时内 / 1 周内

## ⚠️ 关键风险提醒

## 💡 一句话原则

原则:话术自然不模板;安抚不等于认错;补救要具体到金额/动作/时间。$prompt$,
  $schema$
{
  "fields": [
    {"name": "complaint", "type": "textarea", "label": "投诉内容(尽量原话)", "required": true, "max_length": 3000},
    {"name": "emotion_level", "type": "select", "label": "客户情绪等级", "options": ["平静(只是反馈)", "不满(语气重)", "愤怒(要求处理)", "暴怒(威胁/激烈)"], "required": true},
    {"name": "severity", "type": "select", "label": "问题严重度", "options": ["小问题(体验瑕疵)", "中等(影响使用)", "严重(造成损失)", "极严重(法律/公关风险)"], "required": true},
    {"name": "remedy_capacity", "type": "textarea", "label": "你能给的补救空间", "required": true, "max_length": 1500}
  ]
}
  $schema$::jsonb,
  3, FALSE, TRUE, 24
);


-- ============================================================
-- Part 2: 行业-角色-Skill 映射
-- 
-- 用一个临时表来组织数据,然后用 JOIN 写入 skill_role_mapping
-- ============================================================

CREATE TEMP TABLE _mapping_data (
  industry VARCHAR(50),
  role VARCHAR(50),
  skill_key VARCHAR(100),
  priority VARCHAR(20),
  display_order INT
);

-- 互联网/科技公司
INSERT INTO _mapping_data VALUES
  -- 研发助理
  ('互联网', '研发助理', 'meeting_notes_pro', 'essential', 1),
  ('互联网', '研发助理', 'weekly_report', 'essential', 2),
  ('互联网', '研发助理', 'cross_team_coordinator', 'essential', 3),
  ('互联网', '研发助理', 'info_pool_classifier', 'essential', 4),
  ('互联网', '研发助理', 'email_drafter', 'recommended', 5),
  ('互联网', '研发助理', 'doc_summarizer', 'recommended', 6),
  ('互联网', '研发助理', 'one_on_one_prep', 'recommended', 7),
  ('互联网', '研发助理', 'presentation_outliner', 'optional', 8),
  ('互联网', '研发助理', 'boss_translator', 'optional', 9),
  ('互联网', '研发助理', 'monthly_review', 'optional', 10),
  
  -- 产品经理
  ('互联网', '产品经理', 'meeting_notes_pro', 'essential', 1),
  ('互联网', '产品经理', 'weekly_report', 'essential', 2),
  ('互联网', '产品经理', 'competitor_analyzer', 'essential', 3),
  ('互联网', '产品经理', 'metric_decomposer', 'essential', 4),
  ('互联网', '产品经理', 'presentation_outliner', 'recommended', 5),
  ('互联网', '产品经理', 'doc_summarizer', 'recommended', 6),
  ('互联网', '产品经理', 'info_pool_classifier', 'recommended', 7),
  ('互联网', '产品经理', 'email_drafter', 'optional', 8),
  ('互联网', '产品经理', 'cross_team_coordinator', 'optional', 9),
  ('互联网', '产品经理', 'content_planner', 'optional', 10),
  
  -- 运营
  ('互联网', '运营', 'content_planner', 'essential', 1),
  ('互联网', '运营', 'metric_decomposer', 'essential', 2),
  ('互联网', '运营', 'weekly_report', 'essential', 3),
  ('互联网', '运营', 'data_explainer', 'recommended', 4),
  ('互联网', '运营', 'customer_complaint_handler', 'recommended', 5),
  ('互联网', '运营', 'marketing_brief', 'recommended', 6),
  ('互联网', '运营', 'competitor_analyzer', 'optional', 7),
  ('互联网', '运营', 'email_drafter', 'optional', 8),
  
  -- 市场/品牌
  ('互联网', '市场', 'marketing_brief', 'essential', 1),
  ('互联网', '市场', 'content_planner', 'essential', 2),
  ('互联网', '市场', 'presentation_outliner', 'essential', 3),
  ('互联网', '市场', 'competitor_analyzer', 'recommended', 4),
  ('互联网', '市场', 'data_explainer', 'recommended', 5),
  ('互联网', '市场', 'weekly_report', 'recommended', 6),
  ('互联网', '市场', 'email_drafter', 'optional', 7),
  ('互联网', '市场', 'monthly_review', 'optional', 8),
  
  -- 商务/BD/销售
  ('互联网', '销售', 'client_followup', 'essential', 1),
  ('互联网', '销售', 'quotation_generator', 'essential', 2),
  ('互联网', '销售', 'email_drafter', 'essential', 3),
  ('互联网', '销售', 'meeting_notes_pro', 'recommended', 4),
  ('互联网', '销售', 'weekly_report', 'recommended', 5),
  ('互联网', '销售', 'customer_complaint_handler', 'recommended', 6),
  ('互联网', '销售', 'competitor_analyzer', 'optional', 7),
  ('互联网', '销售', 'salary_negotiation', 'optional', 8),
  
  -- HR
  ('互联网', 'HR', 'jd_writer_with_screen', 'essential', 1),
  ('互联网', 'HR', 'email_drafter', 'essential', 2),
  ('互联网', 'HR', 'one_on_one_prep', 'essential', 3),
  ('互联网', 'HR', 'meeting_notes_pro', 'recommended', 4),
  ('互联网', 'HR', 'weekly_report', 'recommended', 5),
  ('互联网', 'HR', 'monthly_review', 'recommended', 6),
  ('互联网', 'HR', 'doc_summarizer', 'optional', 7),
  ('互联网', 'HR', 'salary_negotiation', 'optional', 8);

-- 律所
INSERT INTO _mapping_data VALUES
  ('律所', '律师', 'legal_contract_redflag', 'essential', 1),
  ('律所', '律师', 'email_drafter', 'essential', 2),
  ('律所', '律师', 'doc_summarizer', 'essential', 3),
  ('律所', '律师', 'meeting_notes_pro', 'recommended', 4),
  ('律所', '律师', 'weekly_report', 'recommended', 5),
  ('律所', '律师', 'translate_with_context', 'recommended', 6),
  ('律所', '律师', 'presentation_outliner', 'optional', 7),
  ('律所', '律师', 'report_writer', 'optional', 8),
  
  ('律所', '律师助理', 'legal_contract_redflag', 'essential', 1),
  ('律所', '律师助理', 'email_drafter', 'essential', 2),
  ('律所', '律师助理', 'doc_summarizer', 'essential', 3),
  ('律所', '律师助理', 'info_pool_classifier', 'recommended', 4),
  ('律所', '律师助理', 'meeting_notes_pro', 'recommended', 5),
  ('律所', '律师助理', 'cross_team_coordinator', 'recommended', 6),
  ('律所', '律师助理', 'weekly_report', 'optional', 7),
  ('律所', '律师助理', 'translate_with_context', 'optional', 8);

-- 会计师事务所/财务
INSERT INTO _mapping_data VALUES
  ('财务', '会计', 'expense_audit', 'essential', 1),
  ('财务', '会计', 'data_explainer', 'essential', 2),
  ('财务', '会计', 'doc_summarizer', 'essential', 3),
  ('财务', '会计', 'email_drafter', 'recommended', 4),
  ('财务', '会计', 'weekly_report', 'recommended', 5),
  ('财务', '会计', 'report_writer', 'recommended', 6),
  ('财务', '会计', 'meeting_notes_pro', 'optional', 7),
  ('财务', '会计', 'presentation_outliner', 'optional', 8),
  
  ('财务', '审计', 'expense_audit', 'essential', 1),
  ('财务', '审计', 'doc_summarizer', 'essential', 2),
  ('财务', '审计', 'data_explainer', 'essential', 3),
  ('财务', '审计', 'report_writer', 'recommended', 4),
  ('财务', '审计', 'email_drafter', 'recommended', 5),
  ('财务', '审计', 'weekly_report', 'recommended', 6);

-- 金融/投资
INSERT INTO _mapping_data VALUES
  ('金融', '投资分析师', 'competitor_analyzer', 'essential', 1),
  ('金融', '投资分析师', 'report_writer', 'essential', 2),
  ('金融', '投资分析师', 'doc_summarizer', 'essential', 3),
  ('金融', '投资分析师', 'data_explainer', 'recommended', 4),
  ('金融', '投资分析师', 'metric_decomposer', 'recommended', 5),
  ('金融', '投资分析师', 'presentation_outliner', 'recommended', 6),
  ('金融', '投资分析师', 'meeting_notes_pro', 'optional', 7),
  ('金融', '投资分析师', 'email_drafter', 'optional', 8),
  
  ('金融', '客户经理', 'client_followup', 'essential', 1),
  ('金融', '客户经理', 'quotation_generator', 'essential', 2),
  ('金融', '客户经理', 'email_drafter', 'essential', 3),
  ('金融', '客户经理', 'meeting_notes_pro', 'recommended', 4),
  ('金融', '客户经理', 'customer_complaint_handler', 'recommended', 5),
  ('金融', '客户经理', 'weekly_report', 'recommended', 6),
  ('金融', '客户经理', 'presentation_outliner', 'optional', 7),
  ('金融', '客户经理', 'data_explainer', 'optional', 8);

-- 咨询
INSERT INTO _mapping_data VALUES
  ('咨询', '顾问', 'report_writer', 'essential', 1),
  ('咨询', '顾问', 'presentation_outliner', 'essential', 2),
  ('咨询', '顾问', 'competitor_analyzer', 'essential', 3),
  ('咨询', '顾问', 'meeting_notes_pro', 'recommended', 4),
  ('咨询', '顾问', 'data_explainer', 'recommended', 5),
  ('咨询', '顾问', 'doc_summarizer', 'recommended', 6),
  ('咨询', '顾问', 'metric_decomposer', 'optional', 7),
  ('咨询', '顾问', 'weekly_report', 'optional', 8);

-- 教育/培训
INSERT INTO _mapping_data VALUES
  ('教育', '老师', 'presentation_outliner', 'essential', 1),
  ('教育', '老师', 'content_planner', 'essential', 2),
  ('教育', '老师', 'monthly_review', 'essential', 3),
  ('教育', '老师', 'email_drafter', 'recommended', 4),
  ('教育', '老师', 'doc_summarizer', 'recommended', 5),
  ('教育', '老师', 'one_on_one_prep', 'recommended', 6),
  ('教育', '老师', 'meeting_notes_pro', 'optional', 7),
  ('教育', '老师', 'marketing_brief', 'optional', 8),
  
  ('教育', '培训师', 'presentation_outliner', 'essential', 1),
  ('教育', '培训师', 'content_planner', 'essential', 2),
  ('教育', '培训师', 'monthly_review', 'essential', 3),
  ('教育', '培训师', 'doc_summarizer', 'recommended', 4),
  ('教育', '培训师', 'email_drafter', 'recommended', 5),
  ('教育', '培训师', 'marketing_brief', 'recommended', 6);

-- 医疗
INSERT INTO _mapping_data VALUES
  ('医疗', '科室秘书', 'meeting_notes_pro', 'essential', 1),
  ('医疗', '科室秘书', 'email_drafter', 'essential', 2),
  ('医疗', '科室秘书', 'info_pool_classifier', 'essential', 3),
  ('医疗', '科室秘书', 'weekly_report', 'recommended', 4),
  ('医疗', '科室秘书', 'doc_summarizer', 'recommended', 5),
  ('医疗', '科室秘书', 'cross_team_coordinator', 'recommended', 6),
  ('医疗', '科室秘书', 'presentation_outliner', 'optional', 7),
  
  ('医疗', '医药代表', 'client_followup', 'essential', 1),
  ('医疗', '医药代表', 'weekly_report', 'essential', 2),
  ('医疗', '医药代表', 'meeting_notes_pro', 'essential', 3),
  ('医疗', '医药代表', 'email_drafter', 'recommended', 4),
  ('医疗', '医药代表', 'quotation_generator', 'recommended', 5),
  ('医疗', '医药代表', 'presentation_outliner', 'recommended', 6),
  ('医疗', '医药代表', 'customer_complaint_handler', 'optional', 7);

-- 房产/贸易/餐饮/物业(传统行业通用)
INSERT INTO _mapping_data VALUES
  ('传统行业', '门店店员', 'client_followup', 'essential', 1),
  ('传统行业', '门店店员', 'customer_complaint_handler', 'essential', 2),
  ('传统行业', '门店店员', 'weekly_report', 'essential', 3),
  ('传统行业', '门店店员', 'email_drafter', 'recommended', 4),
  ('传统行业', '门店店员', 'expense_audit', 'recommended', 5),
  ('传统行业', '门店店员', 'info_pool_classifier', 'optional', 6),
  
  ('传统行业', '店长', 'weekly_report', 'essential', 1),
  ('传统行业', '店长', 'customer_complaint_handler', 'essential', 2),
  ('传统行业', '店长', 'expense_audit', 'essential', 3),
  ('传统行业', '店长', 'monthly_review', 'recommended', 4),
  ('传统行业', '店长', 'client_followup', 'recommended', 5),
  ('传统行业', '店长', 'marketing_brief', 'recommended', 6),
  ('传统行业', '店长', 'email_drafter', 'optional', 7),
  ('传统行业', '店长', 'meeting_notes_pro', 'optional', 8),
  
  ('外贸', '业务员', 'client_followup', 'essential', 1),
  ('外贸', '业务员', 'email_drafter', 'essential', 2),
  ('外贸', '业务员', 'quotation_generator', 'essential', 3),
  ('外贸', '业务员', 'translate_with_context', 'essential', 4),
  ('外贸', '业务员', 'weekly_report', 'recommended', 5),
  ('外贸', '业务员', 'customer_complaint_handler', 'recommended', 6),
  ('外贸', '业务员', 'competitor_analyzer', 'optional', 7);


-- 把临时表数据合并到正式表
INSERT INTO skill_role_mapping (skill_id, industry, role, priority, display_order)
SELECT s.id, m.industry, m.role, m.priority, m.display_order
FROM _mapping_data m
JOIN industry_skills s ON s.skill_key = m.skill_key
ON CONFLICT (skill_id, industry, role) DO NOTHING;

DROP TABLE _mapping_data;

COMMIT;

-- ============================================================
-- 验证查询
-- ============================================================

-- SELECT '✅ Skills 总数' AS metric, COUNT(*)::TEXT AS value FROM industry_skills WHERE enabled = TRUE
-- UNION ALL
-- SELECT '✅ 映射条目' AS metric, COUNT(*)::TEXT FROM skill_role_mapping
-- UNION ALL
-- SELECT '✅ 通用 Skill 数' AS metric, COUNT(*)::TEXT FROM industry_skills WHERE is_universal = TRUE
-- UNION ALL
-- SELECT '✅ 覆盖的行业数' AS metric, COUNT(DISTINCT industry)::TEXT FROM skill_role_mapping
-- UNION ALL
-- SELECT '✅ 覆盖的角色数' AS metric, COUNT(DISTINCT (industry, role))::TEXT FROM skill_role_mapping;

-- 看某个角色看到的 Skill:
-- SELECT s.scenario_name, m.priority, m.display_order
-- FROM skill_role_mapping m
-- JOIN industry_skills s ON s.id = m.skill_id
-- WHERE m.industry = '互联网' AND m.role = '研发助理'
-- ORDER BY 
--   CASE m.priority WHEN 'essential' THEN 1 WHEN 'recommended' THEN 2 ELSE 3 END,
--   m.display_order;
