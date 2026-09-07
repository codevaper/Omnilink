-- ============================================
-- OMNILINK DAY 1 SEED DATA
-- Run after schema_day1.sql
-- ============================================

-- ── OFFICERS ────────────────────────────────
INSERT INTO officers (officer_id, name, department, role, email) VALUES
('OFF-EDU-001', 'Rajesh Kumar', 'Education', 'officer', 'rajesh.kumar@gov.in'),
('OFF-HEA-001', 'Priya Sharma', 'Health', 'officer', 'priya.sharma@gov.in'),
('OFF-WEL-001', 'Anita Desai', 'Social Welfare', 'officer', 'anita.desai@gov.in'),
('OFF-REV-001', 'Suresh Patel', 'Revenue', 'officer', 'suresh.patel@gov.in'),
('OFF-ADM-001', 'Vikram Singh', 'Administration', 'admin', 'vikram.singh@gov.in')
ON CONFLICT (officer_id) DO NOTHING;

-- ── QUALITY SCORES: Category A (Excellent) ──
INSERT INTO citizen_quality_scores (citizen_id, quality_score, quality_category, missing_fields, invalid_fields)
SELECT 
    citizen_id, 
    95 + (random()*5)::int, 
    'Excellent',
    '[]'::jsonb,
    '[]'::jsonb
FROM citizens 
WHERE citizen_id BETWEEN 'CIT-000001' AND 'CIT-000030'
ON CONFLICT (citizen_id) DO NOTHING;

-- ── QUALITY SCORES: Category B (Good) ───────
INSERT INTO citizen_quality_scores (citizen_id, quality_score, quality_category, missing_fields, invalid_fields)
SELECT 
    citizen_id,
    80 + (random()*14)::int,
    'Good',
    '["alternate_mobile_number"]'::jsonb,
    '{"mobile_number": "old 9-digit format"}'::jsonb
FROM citizens 
WHERE citizen_id BETWEEN 'CIT-000031' AND 'CIT-000060'
ON CONFLICT (citizen_id) DO NOTHING;

-- ── QUALITY SCORES: Category C (Fair) ───────
INSERT INTO citizen_quality_scores (citizen_id, quality_score, quality_category, missing_fields, invalid_fields)
SELECT 
    citizen_id,
    60 + (random()*19)::int,
    'Fair',
    '["email", "alternate_mobile_number"]'::jsonb,
    '{"bank_ifsc": "old IFSC format"}'::jsonb
FROM citizens 
WHERE citizen_id BETWEEN 'CIT-000061' AND 'CIT-000090'
ON CONFLICT (citizen_id) DO NOTHING;

-- ── QUALITY SCORES: Category D (Poor) ───────
INSERT INTO citizen_quality_scores (citizen_id, quality_score, quality_category, missing_fields, invalid_fields)
SELECT 
    citizen_id,
    40 + (random()*19)::int,
    'Poor',
    '["pan_number", "email", "bank_ifsc"]'::jsonb,
    '{"mobile_number": "invalid", "bank_account": "too short"}'::jsonb
FROM citizens 
WHERE citizen_id BETWEEN 'CIT-000091' AND 'CIT-000120'
ON CONFLICT (citizen_id) DO NOTHING;

-- ── QUALITY SCORES: Category E (Critical) ───
INSERT INTO citizen_quality_scores (citizen_id, quality_score, quality_category, missing_fields, invalid_fields)
SELECT 
    citizen_id,
    20 + (random()*19)::int,
    'Critical',
    '["date_of_birth", "pan_number", "bank_account", "bank_ifsc"]'::jsonb,
    '{"first_name": "conflicting", "mobile_number": "invalid"}'::jsonb
FROM citizens 
WHERE citizen_id BETWEEN 'CIT-000121' AND 'CIT-000150'
ON CONFLICT (citizen_id) DO NOTHING;

-- ── AUDIT LOGS ──────────────────────────────
INSERT INTO audit_logs (timestamp, actor_type, actor_id, action, citizen_id, target_form, fields_affected, purpose, correlation_id, status) VALUES
('2026-08-15 10:23:45', 'citizen', 'CIT-000001', 'consent_requested', 'CIT-000001', 'scholarship', '{"fields":12}', 'Citizen application prefill', 'CON-001', 'success'),
('2026-08-15 10:24:12', 'citizen', 'CIT-000001', 'consent_approved', 'CIT-000001', 'scholarship', '{"fields":12}', 'Citizen application prefill', 'CON-001', 'success'),
('2026-08-15 10:25:30', 'system', 'prefill_engine', 'prefill_generated', 'CIT-000001', 'scholarship', '{"mapped":12}', 'Schema translation', 'CON-001', 'success'),
('2026-08-15 10:27:05', 'citizen', 'CIT-000001', 'submission_created', 'CIT-000001', 'scholarship', '{"complete":true}', 'Scholarship application', 'SUB-001', 'success'),
('2026-08-15 14:30:00', 'officer', 'OFF-EDU-001', 'status_changed', 'CIT-000001', 'scholarship', '{"status":"APPROVED"}', 'Officer review', 'SUB-001', 'success'),
('2026-08-16 09:15:00', 'citizen', 'CIT-000003', 'consent_revoked', 'CIT-000003', 'scholarship', '{"reason":"privacy concern"}', 'Privacy', 'CON-003', 'success'),
('2026-08-16 09:20:00', 'system', 'prefill_engine', 'prefill_blocked', 'CIT-000003', 'scholarship', '{"reason":"consent_revoked"}', 'Validation', 'CON-003', 'failure'),
('2026-08-18 12:05:00', 'system', 'data_quality', 'submission_blocked', 'CIT-000091', 'scholarship', '{"pan_number":"missing","bank_ifsc":"invalid"}', 'Validation', 'CON-091', 'failure');