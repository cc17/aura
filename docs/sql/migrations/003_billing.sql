-- ============================================================
-- 003_billing.sql
-- 创建 user_quotas 表（计费额度）
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS user_quotas (
  id              BIGSERIAL PRIMARY KEY,
  user_id         INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  plan            VARCHAR(20) NOT NULL DEFAULT 'free',
  -- 'free' | 'pro' | 'max'

  usage_count     INT NOT NULL DEFAULT 0,
  -- 当前计费周期内已消耗的次数

  period_start    TIMESTAMP WITH TIME ZONE NOT NULL,
  -- 本周期开始时刻（CST）

  period_end      TIMESTAMP WITH TIME ZONE NOT NULL,
  -- 本周期结束时刻（exclusive，到达此时刻需重置）
  -- Free:  明日 00:00 CST
  -- Pro/Max: 下月 1 日 00:00 CST

  plan_expires_at TIMESTAMP WITH TIME ZONE,
  -- 付费套餐到期时间，NULL = 永久免费

  created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_quotas_user ON user_quotas(user_id);

COMMIT;
