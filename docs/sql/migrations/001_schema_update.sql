-- ============================================================
-- 001_schema_update.sql
-- 
-- 目的:基于 24 个 Skill 的实际需求,升级数据库结构
-- 
-- 关键升级:
-- 1. industry_skills 改为支持"多行业-多角色"的多对多映射
-- 2. 增加 Skill 召回信号埋点表(为未来召回算法做数据准备)
-- 3. 增加 Skill 在线 A/B 实验字段
-- 
-- 执行前提:基础 schema(users, user_memories, industry_skills,
--           user_suggestions, skill_executions)已存在
-- ============================================================

BEGIN;

-- ========== Part 1: industry_skills 表结构调整 ==========

-- 备份现有表(如果有数据)
-- CREATE TABLE industry_skills_backup AS SELECT * FROM industry_skills;

-- 添加新字段
ALTER TABLE industry_skills
  ADD COLUMN IF NOT EXISTS tagline VARCHAR(200),
  ADD COLUMN IF NOT EXISTS example_output TEXT,
  ADD COLUMN IF NOT EXISTS display_metadata JSONB DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS is_universal BOOLEAN DEFAULT FALSE,
  -- is_universal=TRUE 表示所有角色都能看到(如 email_drafter)
  
  ADD COLUMN IF NOT EXISTS layer SMALLINT DEFAULT 1 CHECK (layer IN (1, 2, 3)),
  -- 1=通用白领 Skill, 2=岗位类型横向, 3=行业-岗位特化
  -- 仅用于内部组织,不展示给用户
  
  ADD COLUMN IF NOT EXISTS version VARCHAR(20) DEFAULT '1.0.0',
  ADD COLUMN IF NOT EXISTS experiment_group VARCHAR(50);
  -- 用于 A/B 实验,如 'control' / 'variant_a'

-- 把原来的 industry/role 字段标记为废弃(保留兼容)
COMMENT ON COLUMN industry_skills.industry IS 'DEPRECATED: 用 skill_role_mapping 表代替';
COMMENT ON COLUMN industry_skills.role IS 'DEPRECATED: 用 skill_role_mapping 表代替';

-- ========== Part 2: 新增多对多映射表 ==========

-- 一个 Skill 可以服务多个 [行业 + 角色] 组合
-- 而且每个组合下,Skill 有不同的优先级(必备/推荐/可选)
CREATE TABLE IF NOT EXISTS skill_role_mapping (
  id BIGSERIAL PRIMARY KEY,
  skill_id BIGINT NOT NULL REFERENCES industry_skills(id) ON DELETE CASCADE,
  industry VARCHAR(50) NOT NULL,
  role VARCHAR(50) NOT NULL,
  
  priority VARCHAR(20) NOT NULL CHECK (priority IN ('essential', 'recommended', 'optional')),
  -- essential   = 必备(默认显示在首页)
  -- recommended = 推荐(首页可能显示)
  -- optional    = 可选(在"更多 Skills"里)
  
  display_order INT DEFAULT 0,
  -- 同优先级下的展示顺序
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(skill_id, industry, role)
);

CREATE INDEX idx_skill_role_mapping_lookup 
  ON skill_role_mapping(industry, role, priority, display_order);

CREATE INDEX idx_skill_role_mapping_skill 
  ON skill_role_mapping(skill_id);

-- ========== Part 3: Skill 召回信号埋点表 ==========
-- 这是为未来召回算法准备的数据基础
-- 设计参考:抖音 feed 流的多目标信号系统

CREATE TABLE IF NOT EXISTS skill_signals (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  skill_id BIGINT NOT NULL REFERENCES industry_skills(id),
  
  signal_type VARCHAR(30) NOT NULL,
  -- 'recommended'    Skill 被推荐展示给用户
  -- 'impressioned'   Skill 卡片真的渲染到屏幕(曝光)
  -- 'clicked'        用户点击 Skill 卡片
  -- 'opened'         用户打开 Skill 输入面板
  -- 'started'        用户开始填写
  -- 'submitted'      用户提交完成填写
  -- 'completed'      Skill 执行成功
  -- 'output_copied'  用户复制了输出
  -- 'output_liked'   用户点赞输出
  -- 'output_disliked' 用户点踩输出
  -- 'output_edited'  用户编辑了输出后才用
  -- 'shared'         用户分享了输出
  -- 'abandoned'      用户中途放弃
  
  context JSONB DEFAULT '{}'::jsonb,
  -- 上下文信息,如:
  -- - 来源(首页/推荐/搜索/对话)
  -- - 用户当时的对话 topic
  -- - 实验组
  -- - 显示位置 position
  
  session_id VARCHAR(100),
  -- 用于关联同一次完整使用流程(从 recommended 到 completed)
  
  created_at TIMESTAMP DEFAULT NOW()
);

-- 高频查询索引
CREATE INDEX idx_skill_signals_user_time 
  ON skill_signals(user_id, created_at DESC);

CREATE INDEX idx_skill_signals_skill_type 
  ON skill_signals(skill_id, signal_type, created_at DESC);

CREATE INDEX idx_skill_signals_session 
  ON skill_signals(session_id) WHERE session_id IS NOT NULL;

-- ========== Part 4: Skill 聚合指标表(物化视图,定时刷新) ==========
-- 用于快速查询每个 Skill 的整体表现

CREATE TABLE IF NOT EXISTS skill_metrics_daily (
  id BIGSERIAL PRIMARY KEY,
  skill_id BIGINT NOT NULL REFERENCES industry_skills(id),
  date DATE NOT NULL,
  
  -- 基础漏斗
  recommended_count INT DEFAULT 0,
  impressioned_count INT DEFAULT 0,
  clicked_count INT DEFAULT 0,
  started_count INT DEFAULT 0,
  completed_count INT DEFAULT 0,
  
  -- 质量信号
  liked_count INT DEFAULT 0,
  disliked_count INT DEFAULT 0,
  copied_count INT DEFAULT 0,
  edited_count INT DEFAULT 0,
  abandoned_count INT DEFAULT 0,
  
  -- 衍生指标(由后台任务每天计算)
  ctr NUMERIC(5,4),                    -- clicked / impressioned
  start_rate NUMERIC(5,4),             -- started / clicked
  completion_rate NUMERIC(5,4),        -- completed / started
  satisfaction_rate NUMERIC(5,4),      -- liked / (liked + disliked)
  
  unique_users INT DEFAULT 0,
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(skill_id, date)
);

CREATE INDEX idx_skill_metrics_skill_date 
  ON skill_metrics_daily(skill_id, date DESC);

-- ========== Part 5: 用户对 Skill 的偏好(个性化召回用) ==========
-- 给每个用户对每个 Skill 维护一个动态分数
-- 这是召回算法的核心:已知用户偏好向量

CREATE TABLE IF NOT EXISTS user_skill_affinity (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  skill_id BIGINT NOT NULL REFERENCES industry_skills(id),
  
  affinity_score NUMERIC(6,4) DEFAULT 0.5,
  -- 0-1 范围,反映用户对这个 Skill 的偏好程度
  -- 由后台任务基于 skill_signals 计算
  -- 信号权重:completed > liked > clicked > impressioned > disliked
  
  total_uses INT DEFAULT 0,
  last_used_at TIMESTAMP,
  
  -- 用于召回算法的辅助字段
  last_recommended_at TIMESTAMP,
  recommendation_cool_down_until TIMESTAMP,
  -- 防止短时间内重复推荐同一个 Skill
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(user_id, skill_id)
);

CREATE INDEX idx_user_skill_affinity_user_score 
  ON user_skill_affinity(user_id, affinity_score DESC);

CREATE INDEX idx_user_skill_affinity_last_used 
  ON user_skill_affinity(user_id, last_used_at DESC) 
  WHERE last_used_at IS NOT NULL;

-- ========== Part 6: 触发器:从 skill_executions 自动产生 signals ==========
-- 兼容现有的 skill_executions 表

CREATE OR REPLACE FUNCTION fn_create_skill_signal_from_execution()
RETURNS TRIGGER AS $$
BEGIN
  -- 当一次 skill_execution 完成时,自动写入对应的 signal
  IF NEW.status = 'success' THEN
    INSERT INTO skill_signals (user_id, skill_id, signal_type, session_id, created_at)
    VALUES (NEW.user_id, NEW.skill_id, 'completed', NEW.id::TEXT, NEW.created_at);
  ELSIF NEW.status = 'failed' THEN
    INSERT INTO skill_signals (user_id, skill_id, signal_type, session_id, created_at)
    VALUES (NEW.user_id, NEW.skill_id, 'abandoned', NEW.id::TEXT, NEW.created_at);
  END IF;
  
  -- 更新 user_skill_affinity 的 total_uses 和 last_used_at
  IF NEW.status = 'success' THEN
    INSERT INTO user_skill_affinity (user_id, skill_id, total_uses, last_used_at)
    VALUES (NEW.user_id, NEW.skill_id, 1, NEW.created_at)
    ON CONFLICT (user_id, skill_id) DO UPDATE
    SET total_uses = user_skill_affinity.total_uses + 1,
        last_used_at = NEW.created_at,
        updated_at = NOW();
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_skill_execution_signal ON skill_executions;
CREATE TRIGGER trg_skill_execution_signal
  AFTER INSERT OR UPDATE OF status ON skill_executions
  FOR EACH ROW
  EXECUTE FUNCTION fn_create_skill_signal_from_execution();

-- ========== 完成 ==========

COMMIT;

-- 验证查询(执行后跑一下)
-- SELECT 'industry_skills' AS table_name, COUNT(*) FROM industry_skills
-- UNION ALL SELECT 'skill_role_mapping', COUNT(*) FROM skill_role_mapping
-- UNION ALL SELECT 'skill_signals', COUNT(*) FROM skill_signals
-- UNION ALL SELECT 'skill_metrics_daily', COUNT(*) FROM skill_metrics_daily
-- UNION ALL SELECT 'user_skill_affinity', COUNT(*) FROM user_skill_affinity;
