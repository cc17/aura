-- Migration 004: user_skills table
-- Tracks skills each user has added to their library and which are pinned to Chatbox.

CREATE TABLE IF NOT EXISTS user_skills (
    id           BIGSERIAL PRIMARY KEY,
    user_id      INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id     INT NOT NULL REFERENCES industry_skills(id) ON DELETE CASCADE,
    is_pinned    BOOLEAN NOT NULL DEFAULT FALSE,
    use_count    INT NOT NULL DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    added_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_user_skills_user ON user_skills(user_id);
CREATE INDEX IF NOT EXISTS idx_user_skills_pinned ON user_skills(user_id, is_pinned) WHERE is_pinned = TRUE;
