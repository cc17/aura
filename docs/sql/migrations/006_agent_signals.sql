-- Migration 006: support agent events in skill_signals
-- Makes skill_id nullable and adds agent_key so agent click/impression events
-- can be stored in the same table alongside skill events.

BEGIN;

-- Allow skill_id to be NULL (agent rows won't have one)
ALTER TABLE skill_signals
  ALTER COLUMN skill_id DROP NOT NULL;

-- New column to store the agent key for agent-type events
ALTER TABLE skill_signals
  ADD COLUMN IF NOT EXISTS agent_key VARCHAR(100) NULL;

-- Index for agent event queries
CREATE INDEX IF NOT EXISTS idx_skill_signals_agent_key
  ON skill_signals (agent_key, signal_type, created_at)
  WHERE agent_key IS NOT NULL;

COMMIT;
