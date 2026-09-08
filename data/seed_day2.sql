-- ============================================
-- OMNILINK DAY 2 SEED DATA
-- Officers with passwords
-- ============================================

-- Password for all: omnilink123
-- SHA-256 hash: 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9

INSERT INTO officers (officer_id, name, department, role, email, password_hash) VALUES
('OFF-EDU-001', 'Rajesh Kumar', 'Education', 'officer', 'rajesh.kumar@gov.in', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'),
('OFF-HEA-001', 'Priya Sharma', 'Health', 'officer', 'priya.sharma@gov.in', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'),
('OFF-WEL-001', 'Anita Desai', 'Social Welfare', 'officer', 'anita.desai@gov.in', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'),
('OFF-REV-001', 'Suresh Patel', 'Revenue', 'officer', 'suresh.patel@gov.in', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'),
('OFF-ADM-001', 'Vikram Singh', 'Administration', 'admin', 'vikram.singh@gov.in', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9')
ON CONFLICT (officer_id) DO UPDATE SET password_hash = EXCLUDED.password_hash;