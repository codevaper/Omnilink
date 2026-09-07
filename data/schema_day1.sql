-- ============================================
-- OMNILINK DAY 1 SCHEMA
-- Run on PostgreSQL database
-- ============================================

-- ── OFFICERS TABLE ──────────────────────────
CREATE TABLE IF NOT EXISTS officers (
    officer_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'officer',
    email VARCHAR(100),
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── AUDIT LOGS TABLE ────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actor_type VARCHAR(20) NOT NULL,
    actor_id VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    citizen_id VARCHAR(20),
    target_form VARCHAR(50),
    fields_affected JSONB,
    purpose TEXT,
    correlation_id VARCHAR(50),
    ip_address VARCHAR(50),
    metadata JSONB,
    status VARCHAR(20) DEFAULT 'success'
);

-- ── CITIZEN QUALITY SCORES TABLE ────────────
CREATE TABLE IF NOT EXISTS citizen_quality_scores (
    citizen_id VARCHAR(20) PRIMARY KEY,
    quality_score INTEGER NOT NULL,
    quality_category VARCHAR(20) NOT NULL,
    missing_fields JSONB,
    invalid_fields JSONB,
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── INDEXES ─────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_audit_citizen ON audit_logs(citizen_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_quality_category ON citizen_quality_scores(quality_category);

-- ── MONITORING VIEWS ────────────────────────
CREATE OR REPLACE VIEW v_audit_summary AS
SELECT 
    action,
    COUNT(*) as total_events,
    COUNT(DISTINCT citizen_id) as unique_citizens,
    MAX(timestamp) as last_event
FROM audit_logs
GROUP BY action;