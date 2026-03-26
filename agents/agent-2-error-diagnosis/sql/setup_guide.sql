-- ============================================================
-- HUONG DAN: Chay file nay thu cong trong PostgreSQL
-- Muc dich: Tao schema + bang log cho Agent 2
-- Nguoi thuc hien: DE Team
-- ============================================================

-- Buoc 1: Tao schema agent_log (neu chua co)
CREATE SCHEMA IF NOT EXISTS agent_log;

-- Buoc 2: Tao bang diagnosis_log
CREATE TABLE IF NOT EXISTS agent_log.diagnosis_log (
    diagnosis_id            BIGSERIAL PRIMARY KEY,
    source                  VARCHAR(20)  NOT NULL,   -- 'pg_log' | 'nifi_bulletin'
    source_log_id           VARCHAR(100),             -- log_id goc hoac bulletin id
    correlation_id          VARCHAR(36)  NOT NULL,
    tenant_code             VARCHAR(20),
    job_id                  INTEGER,
    job_name                VARCHAR(200),
    batch_id                VARCHAR(50),
    layer                   VARCHAR(50),
    environment             VARCHAR(10)  NOT NULL,
    error_message_raw       TEXT,
    error_category          VARCHAR(30)  NOT NULL,    -- TRANSIENT | DATA_QUALITY | CONFIGURATION | SOURCE_UNAVAILABLE | RESOURCE | UNKNOWN
    matched_keyword         VARCHAR(200),
    classification_method   VARCHAR(20)  NOT NULL,    -- 'rule_based'
    llm_root_cause          TEXT,
    llm_suggested_steps     JSONB,
    llm_severity            VARCHAR(10),              -- LOW | MEDIUM | HIGH | CRITICAL
    llm_escalate            BOOLEAN      DEFAULT FALSE,
    teams_alert_sent        BOOLEAN      DEFAULT FALSE,
    teams_alert_ts          TIMESTAMPTZ,
    processed_at            TIMESTAMPTZ  DEFAULT NOW(),
    processing_duration_ms  INTEGER
);

-- Buoc 3: Tao index
CREATE INDEX IF NOT EXISTS idx_diag_job       ON agent_log.diagnosis_log(job_name, processed_at DESC);
CREATE INDEX IF NOT EXISTS idx_diag_category  ON agent_log.diagnosis_log(error_category, processed_at DESC);
CREATE INDEX IF NOT EXISTS idx_diag_source    ON agent_log.diagnosis_log(source, source_log_id);

-- Buoc 4: Kiem tra bang da tao thanh cong
SELECT table_schema, table_name, obj_description(pgc.oid) AS comment
FROM information_schema.tables t
JOIN pg_class pgc ON pgc.relname = t.table_name
WHERE table_schema = 'agent_log';
