-- ================================================================
-- SAMA/PDPL Compliance Engine — Remediation Script
-- Dialect  : POSTGRES
-- Generated: 2026-04-15T09:03:58.315060+00:00
-- Findings : 36
-- Blocks   : 23
--
-- ⚠  REVIEW BEFORE EXECUTING. Test on a non-production database.
-- ================================================================


-- ── Schema Prerequisites ────────────────────────────────────────

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [PDPL-CON-001] Create consent_records table
-- │ PDPL Article 10 — consent must be recorded with purpose, date, and basis
-- └──────────────────────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS consent_records (
    id               BIGSERIAL     PRIMARY KEY,
    data_subject_id  BIGINT        NOT NULL,
    purpose          VARCHAR(500)  NOT NULL,
    processing_basis VARCHAR(100)  NOT NULL
                     DEFAULT 'CONSENT'
                     CHECK (processing_basis IN (
                         'CONSENT', 'CONTRACT', 'LEGAL_OBLIGATION',
                         'VITAL_INTERESTS', 'PUBLIC_TASK', 'LEGITIMATE_INTERESTS'
                     )),
    consent_given    BOOLEAN       NOT NULL DEFAULT FALSE,
    consent_date     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    withdrawal_date  TIMESTAMPTZ   NULL,
    consent_version  VARCHAR(50)   NULL,
    ip_address       INET          NULL,
    is_deleted       BOOLEAN       NOT NULL DEFAULT FALSE,
    deleted_at       TIMESTAMPTZ   NULL,
    deleted_by       VARCHAR(255)  NULL,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_by       VARCHAR(255)  NOT NULL DEFAULT 'SYSTEM',
    updated_at       TIMESTAMPTZ   NULL,
    updated_by       VARCHAR(255)  NULL
);

CREATE INDEX IF NOT EXISTS idx_consent_data_subject
    ON consent_records (data_subject_id);
CREATE INDEX IF NOT EXISTS idx_consent_given
    ON consent_records (consent_given, consent_date DESC);

COMMENT ON TABLE consent_records
    IS 'PDPL Art.10 — records of data subject consent for each processing purpose.';

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [PDPL-DSR-001] Create data_subject_requests table
-- │ PDPL Articles 14–18 — access, rectification, erasure, portability rights
-- └──────────────────────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS data_subject_requests (
    id                BIGSERIAL     PRIMARY KEY,
    data_subject_id   BIGINT        NOT NULL,
    request_type      VARCHAR(50)   NOT NULL
                      CHECK (request_type IN (
                          'ACCESS', 'RECTIFICATION', 'ERASURE',
                          'PORTABILITY', 'RESTRICTION', 'OBJECTION'
                      )),
    status            VARCHAR(50)   NOT NULL DEFAULT 'PENDING'
                      CHECK (status IN (
                          'PENDING', 'IN_REVIEW', 'COMPLETED',
                          'REJECTED', 'WITHDRAWN'
                      )),
    requested_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    response_due_date DATE          NULL
                      GENERATED ALWAYS AS (
                          (requested_at + INTERVAL '30 days')::DATE
                      ) STORED,
    completed_at      TIMESTAMPTZ   NULL,
    rejection_reason  TEXT          NULL,
    handler_id        VARCHAR(255)  NULL,
    notes             TEXT          NULL,
    is_deleted        BOOLEAN       NOT NULL DEFAULT FALSE,
    deleted_at        TIMESTAMPTZ   NULL,
    deleted_by        VARCHAR(255)  NULL,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_by        VARCHAR(255)  NOT NULL DEFAULT 'SYSTEM',
    updated_at        TIMESTAMPTZ   NULL,
    updated_by        VARCHAR(255)  NULL
);

CREATE INDEX IF NOT EXISTS idx_dsr_data_subject
    ON data_subject_requests (data_subject_id);
CREATE INDEX IF NOT EXISTS idx_dsr_status
    ON data_subject_requests (status, requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_dsr_due
    ON data_subject_requests (response_due_date)
    WHERE status NOT IN ('COMPLETED', 'REJECTED', 'WITHDRAWN');

COMMENT ON TABLE data_subject_requests
    IS 'PDPL Arts.14-18 — tracks data subject rights requests and their resolution.';
COMMENT ON COLUMN data_subject_requests.response_due_date
    IS 'Auto-computed: 30 days from requested_at per PDPL response deadline.';


-- ── Structural Integrity ────────────────────────────────────────

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-INT-001] Add primary key → country_codes
-- │ Every table must have a PK for record uniqueness and audit referencing
-- └──────────────────────────────────────────────────────────────────────────┘
-- Step 1: Add surrogate PK column
ALTER TABLE country_codes
    ADD COLUMN IF NOT EXISTS id BIGSERIAL;

-- Step 2: Populate id for existing rows (idempotent)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM country_codes WHERE id IS NULL LIMIT 1
    ) THEN
        -- Assign sequential IDs to existing rows
        WITH numbered AS (
            SELECT ctid, ROW_NUMBER() OVER () AS rn FROM country_codes WHERE id IS NULL
        )
        UPDATE country_codes t
           SET id = n.rn
          FROM numbered n
         WHERE t.ctid = n.ctid;
    END IF;
END
$$;

-- Step 3: Add NOT NULL + PK constraint
ALTER TABLE country_codes
    ALTER COLUMN id SET NOT NULL;

ALTER TABLE country_codes
    ADD CONSTRAINT pk_country_codes PRIMARY KEY (id);


-- ── Audit Infrastructure ────────────────────────────────────────

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-AUD-003] Create audit log table → customers_audit_log
-- │ SAMA CSF §3.3.5 — immutable before/after record for all DML operations
-- └──────────────────────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS customers_audit_log (
    audit_id       BIGSERIAL     PRIMARY KEY,
    record_id      BIGINT        NOT NULL,
    operation      VARCHAR(10)   NOT NULL
                   CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    performed_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    performed_by   VARCHAR(255)  NOT NULL
                   DEFAULT current_setting('app.current_user', TRUE),
    source_ip      INET          NULL,
    correlation_id UUID          NULL DEFAULT gen_random_uuid(),
    old_values     JSONB         NULL,
    new_values     JSONB         NULL
);

-- Indexes for efficient audit queries
CREATE INDEX IF NOT EXISTS idx_customers_audit_record
    ON customers_audit_log (record_id);
CREATE INDEX IF NOT EXISTS idx_customers_audit_performed
    ON customers_audit_log (performed_at DESC);
CREATE INDEX IF NOT EXISTS idx_customers_audit_operation
    ON customers_audit_log (operation);

-- Trigger function
CREATE OR REPLACE FUNCTION fn_customers_audit()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO customers_audit_log
            (record_id, operation, performed_by, source_ip, correlation_id, new_values)
        VALUES (
            NEW.id,
            'INSERT',
            current_setting('app.current_user', TRUE),
            inet_client_addr(),
            gen_random_uuid(),
            to_jsonb(NEW)
        );
        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO customers_audit_log
            (record_id, operation, performed_by, source_ip, correlation_id, old_values, new_values)
        VALUES (
            NEW.id,
            'UPDATE',
            current_setting('app.current_user', TRUE),
            inet_client_addr(),
            gen_random_uuid(),
            to_jsonb(OLD),
            to_jsonb(NEW)
        );
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO customers_audit_log
            (record_id, operation, performed_by, source_ip, correlation_id, old_values)
        VALUES (
            OLD.id,
            'DELETE',
            current_setting('app.current_user', TRUE),
            inet_client_addr(),
            gen_random_uuid(),
            to_jsonb(OLD)
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_customers_audit ON customers;
CREATE TRIGGER trg_customers_audit
    AFTER INSERT OR UPDATE OR DELETE ON customers
    FOR EACH ROW EXECUTE FUNCTION fn_customers_audit();

-- Make audit log append-only via RLS (optional but recommended)
-- ALTER TABLE customers_audit_log ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY audit_insert_only ON customers_audit_log FOR INSERT WITH CHECK (TRUE);

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-AUD-003] Create audit log table → accounts_audit_log
-- │ SAMA CSF §3.3.5 — immutable before/after record for all DML operations
-- └──────────────────────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS accounts_audit_log (
    audit_id       BIGSERIAL     PRIMARY KEY,
    record_id      BIGINT        NOT NULL,
    operation      VARCHAR(10)   NOT NULL
                   CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    performed_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    performed_by   VARCHAR(255)  NOT NULL
                   DEFAULT current_setting('app.current_user', TRUE),
    source_ip      INET          NULL,
    correlation_id UUID          NULL DEFAULT gen_random_uuid(),
    old_values     JSONB         NULL,
    new_values     JSONB         NULL
);

-- Indexes for efficient audit queries
CREATE INDEX IF NOT EXISTS idx_accounts_audit_record
    ON accounts_audit_log (record_id);
CREATE INDEX IF NOT EXISTS idx_accounts_audit_performed
    ON accounts_audit_log (performed_at DESC);
CREATE INDEX IF NOT EXISTS idx_accounts_audit_operation
    ON accounts_audit_log (operation);

-- Trigger function
CREATE OR REPLACE FUNCTION fn_accounts_audit()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO accounts_audit_log
            (record_id, operation, performed_by, source_ip, correlation_id, new_values)
        VALUES (
            NEW.id,
            'INSERT',
            current_setting('app.current_user', TRUE),
            inet_client_addr(),
            gen_random_uuid(),
            to_jsonb(NEW)
        );
        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO accounts_audit_log
            (record_id, operation, performed_by, source_ip, correlation_id, old_values, new_values)
        VALUES (
            NEW.id,
            'UPDATE',
            current_setting('app.current_user', TRUE),
            inet_client_addr(),
            gen_random_uuid(),
            to_jsonb(OLD),
            to_jsonb(NEW)
        );
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO accounts_audit_log
            (record_id, operation, performed_by, source_ip, correlation_id, old_values)
        VALUES (
            OLD.id,
            'DELETE',
            current_setting('app.current_user', TRUE),
            inet_client_addr(),
            gen_random_uuid(),
            to_jsonb(OLD)
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_accounts_audit ON accounts;
CREATE TRIGGER trg_accounts_audit
    AFTER INSERT OR UPDATE OR DELETE ON accounts
    FOR EACH ROW EXECUTE FUNCTION fn_accounts_audit();

-- Make audit log append-only via RLS (optional but recommended)
-- ALTER TABLE accounts_audit_log ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY audit_insert_only ON accounts_audit_log FOR INSERT WITH CHECK (TRUE);

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-AUD-003] Create audit log table → patient_health_records_audit_log
-- │ SAMA CSF §3.3.5 — immutable before/after record for all DML operations
-- └──────────────────────────────────────────────────────────────────────────┘
CREATE TABLE IF NOT EXISTS patient_health_records_audit_log (
    audit_id       BIGSERIAL     PRIMARY KEY,
    record_id      BIGINT        NOT NULL,
    operation      VARCHAR(10)   NOT NULL
                   CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    performed_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    performed_by   VARCHAR(255)  NOT NULL
                   DEFAULT current_setting('app.current_user', TRUE),
    source_ip      INET          NULL,
    correlation_id UUID          NULL DEFAULT gen_random_uuid(),
    old_values     JSONB         NULL,
    new_values     JSONB         NULL
);

-- Indexes for efficient audit queries
CREATE INDEX IF NOT EXISTS idx_patient_health_records_audit_record
    ON patient_health_records_audit_log (record_id);
CREATE INDEX IF NOT EXISTS idx_patient_health_records_audit_performed
    ON patient_health_records_audit_log (performed_at DESC);
CREATE INDEX IF NOT EXISTS idx_patient_health_records_audit_operation
    ON patient_health_records_audit_log (operation);

-- Trigger function
CREATE OR REPLACE FUNCTION fn_patient_health_records_audit()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO patient_health_records_audit_log
            (record_id, operation, performed_by, source_ip, correlation_id, new_values)
        VALUES (
            NEW.id,
            'INSERT',
            current_setting('app.current_user', TRUE),
            inet_client_addr(),
            gen_random_uuid(),
            to_jsonb(NEW)
        );
        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO patient_health_records_audit_log
            (record_id, operation, performed_by, source_ip, correlation_id, old_values, new_values)
        VALUES (
            NEW.id,
            'UPDATE',
            current_setting('app.current_user', TRUE),
            inet_client_addr(),
            gen_random_uuid(),
            to_jsonb(OLD),
            to_jsonb(NEW)
        );
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO patient_health_records_audit_log
            (record_id, operation, performed_by, source_ip, correlation_id, old_values)
        VALUES (
            OLD.id,
            'DELETE',
            current_setting('app.current_user', TRUE),
            inet_client_addr(),
            gen_random_uuid(),
            to_jsonb(OLD)
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_patient_health_records_audit ON patient_health_records;
CREATE TRIGGER trg_patient_health_records_audit
    AFTER INSERT OR UPDATE OR DELETE ON patient_health_records
    FOR EACH ROW EXECUTE FUNCTION fn_patient_health_records_audit();

-- Make audit log append-only via RLS (optional but recommended)
-- ALTER TABLE patient_health_records_audit_log ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY audit_insert_only ON patient_health_records_audit_log FOR INSERT WITH CHECK (TRUE);


-- ── Audit Trail Columns ─────────────────────────────────────────

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-AUD-001] Add missing audit trail columns → customers
-- │ SAMA Cyber Security Framework §3.3.5 — full create/update audit trail
-- └──────────────────────────────────────────────────────────────────────────┘
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ  NULL;
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS updated_by VARCHAR(255) NULL;

-- ⚠  After backfilling real user IDs, drop the migration defaults:

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-AUD-001] Add missing audit trail columns → country_codes
-- │ SAMA Cyber Security Framework §3.3.5 — full create/update audit trail
-- └──────────────────────────────────────────────────────────────────────────┘
ALTER TABLE country_codes
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW();
ALTER TABLE country_codes
    ADD COLUMN IF NOT EXISTS created_by VARCHAR(255) NOT NULL DEFAULT 'MIGRATION';
ALTER TABLE country_codes
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ  NULL;
ALTER TABLE country_codes
    ADD COLUMN IF NOT EXISTS updated_by VARCHAR(255) NULL;

-- ⚠  After backfilling real user IDs, drop the migration defaults:
-- ALTER TABLE country_codes ALTER COLUMN created_by DROP DEFAULT;


-- ── Soft Delete Columns ─────────────────────────────────────────

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-AUD-002] Add soft-delete columns → customers
-- │ SAMA CSF §3.3.7 — logical deletion preserves audit trail
-- └──────────────────────────────────────────────────────────────────────────┘
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS is_deleted  BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS deleted_at  TIMESTAMPTZ  NULL,
    ADD COLUMN IF NOT EXISTS deleted_by  VARCHAR(255) NULL;

CREATE INDEX IF NOT EXISTS idx_customers_is_deleted ON customers (is_deleted)
    WHERE is_deleted = FALSE;

-- Usage: instead of DELETE, use:
-- UPDATE customers
--   SET is_deleted = TRUE, deleted_at = NOW(), deleted_by = current_setting('app.current_user', TRUE)
--   WHERE id = $1;

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-AUD-002] Add soft-delete columns → accounts
-- │ SAMA CSF §3.3.7 — logical deletion preserves audit trail
-- └──────────────────────────────────────────────────────────────────────────┘
ALTER TABLE accounts
    ADD COLUMN IF NOT EXISTS is_deleted  BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS deleted_at  TIMESTAMPTZ  NULL,
    ADD COLUMN IF NOT EXISTS deleted_by  VARCHAR(255) NULL;

CREATE INDEX IF NOT EXISTS idx_accounts_is_deleted ON accounts (is_deleted)
    WHERE is_deleted = FALSE;

-- Usage: instead of DELETE, use:
-- UPDATE accounts
--   SET is_deleted = TRUE, deleted_at = NOW(), deleted_by = current_setting('app.current_user', TRUE)
--   WHERE id = $1;

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-AUD-002] Add soft-delete columns → patient_health_records
-- │ SAMA CSF §3.3.7 — logical deletion preserves audit trail
-- └──────────────────────────────────────────────────────────────────────────┘
ALTER TABLE patient_health_records
    ADD COLUMN IF NOT EXISTS is_deleted  BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS deleted_at  TIMESTAMPTZ  NULL,
    ADD COLUMN IF NOT EXISTS deleted_by  VARCHAR(255) NULL;

CREATE INDEX IF NOT EXISTS idx_patient_health_records_is_deleted ON patient_health_records (is_deleted)
    WHERE is_deleted = FALSE;

-- Usage: instead of DELETE, use:
-- UPDATE patient_health_records
--   SET is_deleted = TRUE, deleted_at = NOW(), deleted_by = current_setting('app.current_user', TRUE)
--   WHERE id = $1;


-- ── Data Retention ──────────────────────────────────────────────

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-RET-001] Add data retention metadata → customers
-- │ SAMA mandates minimum 5-year (60-month) retention for financial records
-- └──────────────────────────────────────────────────────────────────────────┘
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS retention_period   SMALLINT     NULL
        CHECK (retention_period > 0)
        DEFAULT 60,   -- 60 months = 5 years (SAMA minimum)
    ADD COLUMN IF NOT EXISTS data_category      VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS retention_expires_at TIMESTAMPTZ NULL
        GENERATED ALWAYS AS (
            created_at + (retention_period * INTERVAL '1 month')
        ) STORED;

COMMENT ON COLUMN customers.retention_period
    IS 'Retention period in months. SAMA minimum for financial records = 60.';
COMMENT ON COLUMN customers.data_category
    IS 'Data category for retention policy (e.g. FINANCIAL, PERSONAL, OPERATIONAL).';
COMMENT ON COLUMN customers.retention_expires_at
    IS 'Computed expiry timestamp: created_at + retention_period months.';

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-RET-001] Add data retention metadata → accounts
-- │ SAMA mandates minimum 5-year (60-month) retention for financial records
-- └──────────────────────────────────────────────────────────────────────────┘
ALTER TABLE accounts
    ADD COLUMN IF NOT EXISTS retention_period   SMALLINT     NULL
        CHECK (retention_period > 0)
        DEFAULT 60,   -- 60 months = 5 years (SAMA minimum)
    ADD COLUMN IF NOT EXISTS data_category      VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS retention_expires_at TIMESTAMPTZ NULL
        GENERATED ALWAYS AS (
            created_at + (retention_period * INTERVAL '1 month')
        ) STORED;

COMMENT ON COLUMN accounts.retention_period
    IS 'Retention period in months. SAMA minimum for financial records = 60.';
COMMENT ON COLUMN accounts.data_category
    IS 'Data category for retention policy (e.g. FINANCIAL, PERSONAL, OPERATIONAL).';
COMMENT ON COLUMN accounts.retention_expires_at
    IS 'Computed expiry timestamp: created_at + retention_period months.';


-- ── Referential Integrity ───────────────────────────────────────

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-REF-001] Replace CASCADE DELETE with RESTRICT → accounts
-- │ FK on column(s) customer_id → customers
-- │ CASCADE DELETE on PII/financial tables risks bulk erasure of regulated data
-- └──────────────────────────────────────────────────────────────────────────┘

-- Step 1: Identify and drop the offending FK constraint
DO $$
DECLARE
    v_constraint_name TEXT;
BEGIN
    SELECT tc.constraint_name
      INTO v_constraint_name
      FROM information_schema.table_constraints tc
      JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
       AND tc.table_name      = kcu.table_name
      JOIN information_schema.referential_constraints rc
        ON tc.constraint_name = rc.constraint_name
     WHERE tc.table_name       = 'accounts'
       AND tc.constraint_type  = 'FOREIGN KEY'
       AND kcu.column_name     IN ("customer_id")
     LIMIT 1;

    IF v_constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE accounts DROP CONSTRAINT %I', v_constraint_name);
        RAISE NOTICE 'Dropped FK constraint: %', v_constraint_name;
    ELSE
        RAISE NOTICE 'No matching FK constraint found on accounts(customer_id) — may already be fixed.';
    END IF;
END
$$;

-- Step 2: Recreate with ON DELETE RESTRICT
ALTER TABLE accounts
    ADD CONSTRAINT fk_accounts_customer_id
    FOREIGN KEY (customer_id)
    REFERENCES customers (id)
    ON DELETE RESTRICT
    ON UPDATE NO ACTION;


-- ── Transaction Traceability ────────────────────────────────────

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [SAMA-TRX-001] Add transaction traceability columns → transactions
-- │ SAMA Open Banking Framework — end-to-end traceability for all transactions
-- └──────────────────────────────────────────────────────────────────────────┘
ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS reference_id   VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS correlation_id UUID         NULL DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS status         VARCHAR(50)  NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','PROCESSING','COMPLETED','FAILED','REVERSED','CANCELLED')),
    -- placeholder to avoid trailing comma — remove above line if last real column has no comma
    updated_at = updated_at;  -- no-op anchor; remove this line and fix trailing commas above

-- Unique index on reference_id for idempotent transaction submission
CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_reference_id
    ON transactions (reference_id)
    WHERE reference_id IS NOT NULL;


-- ── Column Encryption ───────────────────────────────────────────

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [PDPL-ENC-001] Encrypt Tier 1 column → customers.full_name
-- │ PDPL Art.8 — Tier 1 (Directly Identifying) data must be encrypted at rest
-- │ Requires: CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- └──────────────────────────────────────────────────────────────────────────┘

-- PREREQUISITES:
-- 1. Set your encryption key in postgresql.conf or at session level:
--    SET app.encryption_key = 'your-256-bit-key-here';
-- 2. Ensure pgcrypto is installed:
--    CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- 3. TEST THIS MIGRATION ON A NON-PRODUCTION DATABASE FIRST.

BEGIN;

-- Step 1: Add encrypted column alongside the plaintext column
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS full_name_encrypted BYTEA;

-- Step 2: Encrypt existing data
--   pgp_sym_encrypt stores AES-256 encrypted ciphertext as BYTEA
UPDATE customers
   SET full_name_encrypted = pgp_sym_encrypt(
           full_name::TEXT,
           current_setting('app.encryption_key')
       )
 WHERE full_name IS NOT NULL
   AND full_name_encrypted IS NULL;

-- Step 3: Verify row counts match (abort if not)
DO $$
DECLARE
    total_rows       BIGINT;
    encrypted_rows   BIGINT;
BEGIN
    SELECT COUNT(*) INTO total_rows      FROM customers WHERE full_name IS NOT NULL;
    SELECT COUNT(*) INTO encrypted_rows  FROM customers WHERE full_name_encrypted IS NOT NULL;
    IF total_rows <> encrypted_rows THEN
        RAISE EXCEPTION 'Encryption verification failed: % rows have plaintext but only % encrypted.',
            total_rows, encrypted_rows;
    END IF;
    RAISE NOTICE 'Encryption OK: % rows encrypted for customers.full_name.', encrypted_rows;
END
$$;

-- Step 4: Rename plaintext column for rollback safety (do NOT drop yet)
ALTER TABLE customers
    RENAME COLUMN full_name TO full_name_plaintext_backup;

-- Step 5: Rename encrypted column to canonical name
ALTER TABLE customers
    RENAME COLUMN full_name_encrypted TO full_name;

COMMIT;

-- Step 6 (AFTER VALIDATION): Drop the plaintext backup column
-- Run this only after confirming the application works with decryption:
--   ALTER TABLE customers DROP COLUMN full_name_plaintext_backup;

-- Decryption query for application use:
--   SELECT pgp_sym_decrypt(full_name, current_setting('app.encryption_key'))::VARCHAR(255)
--     FROM customers WHERE id = $1;

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [PDPL-ENC-001] Encrypt Tier 1 column → customers.email
-- │ PDPL Art.8 — Tier 1 (Directly Identifying) data must be encrypted at rest
-- │ Requires: CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- └──────────────────────────────────────────────────────────────────────────┘

-- PREREQUISITES:
-- 1. Set your encryption key in postgresql.conf or at session level:
--    SET app.encryption_key = 'your-256-bit-key-here';
-- 2. Ensure pgcrypto is installed:
--    CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- 3. TEST THIS MIGRATION ON A NON-PRODUCTION DATABASE FIRST.

BEGIN;

-- Step 1: Add encrypted column alongside the plaintext column
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS email_encrypted BYTEA;

-- Step 2: Encrypt existing data
--   pgp_sym_encrypt stores AES-256 encrypted ciphertext as BYTEA
UPDATE customers
   SET email_encrypted = pgp_sym_encrypt(
           email::TEXT,
           current_setting('app.encryption_key')
       )
 WHERE email IS NOT NULL
   AND email_encrypted IS NULL;

-- Step 3: Verify row counts match (abort if not)
DO $$
DECLARE
    total_rows       BIGINT;
    encrypted_rows   BIGINT;
BEGIN
    SELECT COUNT(*) INTO total_rows      FROM customers WHERE email IS NOT NULL;
    SELECT COUNT(*) INTO encrypted_rows  FROM customers WHERE email_encrypted IS NOT NULL;
    IF total_rows <> encrypted_rows THEN
        RAISE EXCEPTION 'Encryption verification failed: % rows have plaintext but only % encrypted.',
            total_rows, encrypted_rows;
    END IF;
    RAISE NOTICE 'Encryption OK: % rows encrypted for customers.email.', encrypted_rows;
END
$$;

-- Step 4: Rename plaintext column for rollback safety (do NOT drop yet)
ALTER TABLE customers
    RENAME COLUMN email TO email_plaintext_backup;

-- Step 5: Rename encrypted column to canonical name
ALTER TABLE customers
    RENAME COLUMN email_encrypted TO email;

COMMIT;

-- Step 6 (AFTER VALIDATION): Drop the plaintext backup column
-- Run this only after confirming the application works with decryption:
--   ALTER TABLE customers DROP COLUMN email_plaintext_backup;

-- Decryption query for application use:
--   SELECT pgp_sym_decrypt(email, current_setting('app.encryption_key'))::VARCHAR(255)
--     FROM customers WHERE id = $1;

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [PDPL-ENC-001] Encrypt Tier 1 column → customers.phone_number
-- │ PDPL Art.8 — Tier 1 (Directly Identifying) data must be encrypted at rest
-- │ Requires: CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- └──────────────────────────────────────────────────────────────────────────┘

-- PREREQUISITES:
-- 1. Set your encryption key in postgresql.conf or at session level:
--    SET app.encryption_key = 'your-256-bit-key-here';
-- 2. Ensure pgcrypto is installed:
--    CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- 3. TEST THIS MIGRATION ON A NON-PRODUCTION DATABASE FIRST.

BEGIN;

-- Step 1: Add encrypted column alongside the plaintext column
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS phone_number_encrypted BYTEA;

-- Step 2: Encrypt existing data
--   pgp_sym_encrypt stores AES-256 encrypted ciphertext as BYTEA
UPDATE customers
   SET phone_number_encrypted = pgp_sym_encrypt(
           phone_number::TEXT,
           current_setting('app.encryption_key')
       )
 WHERE phone_number IS NOT NULL
   AND phone_number_encrypted IS NULL;

-- Step 3: Verify row counts match (abort if not)
DO $$
DECLARE
    total_rows       BIGINT;
    encrypted_rows   BIGINT;
BEGIN
    SELECT COUNT(*) INTO total_rows      FROM customers WHERE phone_number IS NOT NULL;
    SELECT COUNT(*) INTO encrypted_rows  FROM customers WHERE phone_number_encrypted IS NOT NULL;
    IF total_rows <> encrypted_rows THEN
        RAISE EXCEPTION 'Encryption verification failed: % rows have plaintext but only % encrypted.',
            total_rows, encrypted_rows;
    END IF;
    RAISE NOTICE 'Encryption OK: % rows encrypted for customers.phone_number.', encrypted_rows;
END
$$;

-- Step 4: Rename plaintext column for rollback safety (do NOT drop yet)
ALTER TABLE customers
    RENAME COLUMN phone_number TO phone_number_plaintext_backup;

-- Step 5: Rename encrypted column to canonical name
ALTER TABLE customers
    RENAME COLUMN phone_number_encrypted TO phone_number;

COMMIT;

-- Step 6 (AFTER VALIDATION): Drop the plaintext backup column
-- Run this only after confirming the application works with decryption:
--   ALTER TABLE customers DROP COLUMN phone_number_plaintext_backup;

-- Decryption query for application use:
--   SELECT pgp_sym_decrypt(phone_number, current_setting('app.encryption_key'))::VARCHAR(20)
--     FROM customers WHERE id = $1;

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [PDPL-ENC-001] Encrypt Tier 1 column → customers.national_id
-- │ PDPL Art.8 — Tier 1 (Directly Identifying) data must be encrypted at rest
-- │ Requires: CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- └──────────────────────────────────────────────────────────────────────────┘

-- PREREQUISITES:
-- 1. Set your encryption key in postgresql.conf or at session level:
--    SET app.encryption_key = 'your-256-bit-key-here';
-- 2. Ensure pgcrypto is installed:
--    CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- 3. TEST THIS MIGRATION ON A NON-PRODUCTION DATABASE FIRST.

BEGIN;

-- Step 1: Add encrypted column alongside the plaintext column
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS national_id_encrypted BYTEA;

-- Step 2: Encrypt existing data
--   pgp_sym_encrypt stores AES-256 encrypted ciphertext as BYTEA
UPDATE customers
   SET national_id_encrypted = pgp_sym_encrypt(
           national_id::TEXT,
           current_setting('app.encryption_key')
       )
 WHERE national_id IS NOT NULL
   AND national_id_encrypted IS NULL;

-- Step 3: Verify row counts match (abort if not)
DO $$
DECLARE
    total_rows       BIGINT;
    encrypted_rows   BIGINT;
BEGIN
    SELECT COUNT(*) INTO total_rows      FROM customers WHERE national_id IS NOT NULL;
    SELECT COUNT(*) INTO encrypted_rows  FROM customers WHERE national_id_encrypted IS NOT NULL;
    IF total_rows <> encrypted_rows THEN
        RAISE EXCEPTION 'Encryption verification failed: % rows have plaintext but only % encrypted.',
            total_rows, encrypted_rows;
    END IF;
    RAISE NOTICE 'Encryption OK: % rows encrypted for customers.national_id.', encrypted_rows;
END
$$;

-- Step 4: Rename plaintext column for rollback safety (do NOT drop yet)
ALTER TABLE customers
    RENAME COLUMN national_id TO national_id_plaintext_backup;

-- Step 5: Rename encrypted column to canonical name
ALTER TABLE customers
    RENAME COLUMN national_id_encrypted TO national_id;

COMMIT;

-- Step 6 (AFTER VALIDATION): Drop the plaintext backup column
-- Run this only after confirming the application works with decryption:
--   ALTER TABLE customers DROP COLUMN national_id_plaintext_backup;

-- Decryption query for application use:
--   SELECT pgp_sym_decrypt(national_id, current_setting('app.encryption_key'))::VARCHAR(20)
--     FROM customers WHERE id = $1;

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [PDPL-ENC-001] Encrypt Tier 1 column → customers.date_of_birth
-- │ PDPL Art.8 — Tier 1 (Directly Identifying) data must be encrypted at rest
-- │ Requires: CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- └──────────────────────────────────────────────────────────────────────────┘

-- PREREQUISITES:
-- 1. Set your encryption key in postgresql.conf or at session level:
--    SET app.encryption_key = 'your-256-bit-key-here';
-- 2. Ensure pgcrypto is installed:
--    CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- 3. TEST THIS MIGRATION ON A NON-PRODUCTION DATABASE FIRST.

BEGIN;

-- Step 1: Add encrypted column alongside the plaintext column
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS date_of_birth_encrypted BYTEA;

-- Step 2: Encrypt existing data
--   pgp_sym_encrypt stores AES-256 encrypted ciphertext as BYTEA
UPDATE customers
   SET date_of_birth_encrypted = pgp_sym_encrypt(
           date_of_birth::TEXT,
           current_setting('app.encryption_key')
       )
 WHERE date_of_birth IS NOT NULL
   AND date_of_birth_encrypted IS NULL;

-- Step 3: Verify row counts match (abort if not)
DO $$
DECLARE
    total_rows       BIGINT;
    encrypted_rows   BIGINT;
BEGIN
    SELECT COUNT(*) INTO total_rows      FROM customers WHERE date_of_birth IS NOT NULL;
    SELECT COUNT(*) INTO encrypted_rows  FROM customers WHERE date_of_birth_encrypted IS NOT NULL;
    IF total_rows <> encrypted_rows THEN
        RAISE EXCEPTION 'Encryption verification failed: % rows have plaintext but only % encrypted.',
            total_rows, encrypted_rows;
    END IF;
    RAISE NOTICE 'Encryption OK: % rows encrypted for customers.date_of_birth.', encrypted_rows;
END
$$;

-- Step 4: Rename plaintext column for rollback safety (do NOT drop yet)
ALTER TABLE customers
    RENAME COLUMN date_of_birth TO date_of_birth_plaintext_backup;

-- Step 5: Rename encrypted column to canonical name
ALTER TABLE customers
    RENAME COLUMN date_of_birth_encrypted TO date_of_birth;

COMMIT;

-- Step 6 (AFTER VALIDATION): Drop the plaintext backup column
-- Run this only after confirming the application works with decryption:
--   ALTER TABLE customers DROP COLUMN date_of_birth_plaintext_backup;

-- Decryption query for application use:
--   SELECT pgp_sym_decrypt(date_of_birth, current_setting('app.encryption_key'))::DATE
--     FROM customers WHERE id = $1;

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [PDPL-ENC-001] Encrypt Tier 4 column → patient_health_records.diagnosis
-- │ PDPL Art.8 — Tier 4 (PDPL Art.3 Sensitive) data must be encrypted at rest
-- │ Requires: CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- └──────────────────────────────────────────────────────────────────────────┘

-- PREREQUISITES:
-- 1. Set your encryption key in postgresql.conf or at session level:
--    SET app.encryption_key = 'your-256-bit-key-here';
-- 2. Ensure pgcrypto is installed:
--    CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- 3. TEST THIS MIGRATION ON A NON-PRODUCTION DATABASE FIRST.

BEGIN;

-- Step 1: Add encrypted column alongside the plaintext column
ALTER TABLE patient_health_records
    ADD COLUMN IF NOT EXISTS diagnosis_encrypted BYTEA;

-- Step 2: Encrypt existing data
--   pgp_sym_encrypt stores AES-256 encrypted ciphertext as BYTEA
UPDATE patient_health_records
   SET diagnosis_encrypted = pgp_sym_encrypt(
           diagnosis::TEXT,
           current_setting('app.encryption_key')
       )
 WHERE diagnosis IS NOT NULL
   AND diagnosis_encrypted IS NULL;

-- Step 3: Verify row counts match (abort if not)
DO $$
DECLARE
    total_rows       BIGINT;
    encrypted_rows   BIGINT;
BEGIN
    SELECT COUNT(*) INTO total_rows      FROM patient_health_records WHERE diagnosis IS NOT NULL;
    SELECT COUNT(*) INTO encrypted_rows  FROM patient_health_records WHERE diagnosis_encrypted IS NOT NULL;
    IF total_rows <> encrypted_rows THEN
        RAISE EXCEPTION 'Encryption verification failed: % rows have plaintext but only % encrypted.',
            total_rows, encrypted_rows;
    END IF;
    RAISE NOTICE 'Encryption OK: % rows encrypted for patient_health_records.diagnosis.', encrypted_rows;
END
$$;

-- Step 4: Rename plaintext column for rollback safety (do NOT drop yet)
ALTER TABLE patient_health_records
    RENAME COLUMN diagnosis TO diagnosis_plaintext_backup;

-- Step 5: Rename encrypted column to canonical name
ALTER TABLE patient_health_records
    RENAME COLUMN diagnosis_encrypted TO diagnosis;

COMMIT;

-- Step 6 (AFTER VALIDATION): Drop the plaintext backup column
-- Run this only after confirming the application works with decryption:
--   ALTER TABLE patient_health_records DROP COLUMN diagnosis_plaintext_backup;

-- Decryption query for application use:
--   SELECT pgp_sym_decrypt(diagnosis, current_setting('app.encryption_key'))::TEXT
--     FROM patient_health_records WHERE id = $1;

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [PDPL-ENC-001] Encrypt Tier 4 column → patient_health_records.medical_record
-- │ PDPL Art.8 — Tier 4 (PDPL Art.3 Sensitive) data must be encrypted at rest
-- │ Requires: CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- └──────────────────────────────────────────────────────────────────────────┘

-- PREREQUISITES:
-- 1. Set your encryption key in postgresql.conf or at session level:
--    SET app.encryption_key = 'your-256-bit-key-here';
-- 2. Ensure pgcrypto is installed:
--    CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- 3. TEST THIS MIGRATION ON A NON-PRODUCTION DATABASE FIRST.

BEGIN;

-- Step 1: Add encrypted column alongside the plaintext column
ALTER TABLE patient_health_records
    ADD COLUMN IF NOT EXISTS medical_record_encrypted BYTEA;

-- Step 2: Encrypt existing data
--   pgp_sym_encrypt stores AES-256 encrypted ciphertext as BYTEA
UPDATE patient_health_records
   SET medical_record_encrypted = pgp_sym_encrypt(
           medical_record::TEXT,
           current_setting('app.encryption_key')
       )
 WHERE medical_record IS NOT NULL
   AND medical_record_encrypted IS NULL;

-- Step 3: Verify row counts match (abort if not)
DO $$
DECLARE
    total_rows       BIGINT;
    encrypted_rows   BIGINT;
BEGIN
    SELECT COUNT(*) INTO total_rows      FROM patient_health_records WHERE medical_record IS NOT NULL;
    SELECT COUNT(*) INTO encrypted_rows  FROM patient_health_records WHERE medical_record_encrypted IS NOT NULL;
    IF total_rows <> encrypted_rows THEN
        RAISE EXCEPTION 'Encryption verification failed: % rows have plaintext but only % encrypted.',
            total_rows, encrypted_rows;
    END IF;
    RAISE NOTICE 'Encryption OK: % rows encrypted for patient_health_records.medical_record.', encrypted_rows;
END
$$;

-- Step 4: Rename plaintext column for rollback safety (do NOT drop yet)
ALTER TABLE patient_health_records
    RENAME COLUMN medical_record TO medical_record_plaintext_backup;

-- Step 5: Rename encrypted column to canonical name
ALTER TABLE patient_health_records
    RENAME COLUMN medical_record_encrypted TO medical_record;

COMMIT;

-- Step 6 (AFTER VALIDATION): Drop the plaintext backup column
-- Run this only after confirming the application works with decryption:
--   ALTER TABLE patient_health_records DROP COLUMN medical_record_plaintext_backup;

-- Decryption query for application use:
--   SELECT pgp_sym_decrypt(medical_record, current_setting('app.encryption_key'))::TEXT
--     FROM patient_health_records WHERE id = $1;

-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ [PDPL-ENC-001] Encrypt Tier 4 column → patient_health_records.prescription
-- │ PDPL Art.8 — Tier 4 (PDPL Art.3 Sensitive) data must be encrypted at rest
-- │ Requires: CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- └──────────────────────────────────────────────────────────────────────────┘

-- PREREQUISITES:
-- 1. Set your encryption key in postgresql.conf or at session level:
--    SET app.encryption_key = 'your-256-bit-key-here';
-- 2. Ensure pgcrypto is installed:
--    CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- 3. TEST THIS MIGRATION ON A NON-PRODUCTION DATABASE FIRST.

BEGIN;

-- Step 1: Add encrypted column alongside the plaintext column
ALTER TABLE patient_health_records
    ADD COLUMN IF NOT EXISTS prescription_encrypted BYTEA;

-- Step 2: Encrypt existing data
--   pgp_sym_encrypt stores AES-256 encrypted ciphertext as BYTEA
UPDATE patient_health_records
   SET prescription_encrypted = pgp_sym_encrypt(
           prescription::TEXT,
           current_setting('app.encryption_key')
       )
 WHERE prescription IS NOT NULL
   AND prescription_encrypted IS NULL;

-- Step 3: Verify row counts match (abort if not)
DO $$
DECLARE
    total_rows       BIGINT;
    encrypted_rows   BIGINT;
BEGIN
    SELECT COUNT(*) INTO total_rows      FROM patient_health_records WHERE prescription IS NOT NULL;
    SELECT COUNT(*) INTO encrypted_rows  FROM patient_health_records WHERE prescription_encrypted IS NOT NULL;
    IF total_rows <> encrypted_rows THEN
        RAISE EXCEPTION 'Encryption verification failed: % rows have plaintext but only % encrypted.',
            total_rows, encrypted_rows;
    END IF;
    RAISE NOTICE 'Encryption OK: % rows encrypted for patient_health_records.prescription.', encrypted_rows;
END
$$;

-- Step 4: Rename plaintext column for rollback safety (do NOT drop yet)
ALTER TABLE patient_health_records
    RENAME COLUMN prescription TO prescription_plaintext_backup;

-- Step 5: Rename encrypted column to canonical name
ALTER TABLE patient_health_records
    RENAME COLUMN prescription_encrypted TO prescription;

COMMIT;

-- Step 6 (AFTER VALIDATION): Drop the plaintext backup column
-- Run this only after confirming the application works with decryption:
--   ALTER TABLE patient_health_records DROP COLUMN prescription_plaintext_backup;

-- Decryption query for application use:
--   SELECT pgp_sym_decrypt(prescription, current_setting('app.encryption_key'))::TEXT
--     FROM patient_health_records WHERE id = $1;
