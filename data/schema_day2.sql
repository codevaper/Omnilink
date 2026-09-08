-- ============================================
-- OMNILINK DAY 2 SCHEMA
-- Auth + RBAC tables
-- ============================================

-- ── ADD PASSWORD HASH TO OFFICERS ────────────
ALTER TABLE officers 
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- ── ADD PASSWORD HASH TO CITIZENS ────────────
ALTER TABLE omnilink_core.citizens 
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- ── UPDATE OFFICERS WITH DEFAULT PASSWORD ────
-- Default password for prototype: omnilink123
UPDATE officers 
SET password_hash = '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'
WHERE password_hash IS NULL;

-- ── UPDATE CITIZENS WITH DEFAULT PASSWORD ────
UPDATE omnilink_core.citizens 
SET password_hash = '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'
WHERE password_hash IS NULL;

-- ── CREATE SESSIONS TABLE ────────────────────
CREATE TABLE IF NOT EXISTS auth_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    revoked_at TIMESTAMP
);

-- ── INDEX ────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_sessions_user ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON auth_sessions(token_hash);