-- ============================================================
-- PostgreSQL Sample DDL — intentionally non-compliant
-- for SAMA/PDPL compliance engine testing
-- ============================================================

-- Customers table: missing audit columns, PII not encrypted
CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,          -- Tier 1: directly identifying
    email VARCHAR(255) UNIQUE NOT NULL,        -- Tier 1
    phone_number VARCHAR(20),                  -- Tier 1
    national_id VARCHAR(20),                   -- Tier 1
    date_of_birth DATE,                        -- Tier 1
    address TEXT,                              -- Tier 1
    credit_score INTEGER,                      -- Tier 3: financial
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL
    -- MISSING: updated_at, updated_by
    -- MISSING: is_deleted, deleted_at, deleted_by
    -- VIOLATION: Tier 1 columns stored as VARCHAR, not BYTEA
);

-- Accounts table: missing soft delete, CASCADE DELETE violation
CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE CASCADE, -- VIOLATION: CASCADE on Tier 1 table
    account_number VARCHAR(30) UNIQUE NOT NULL,  -- Tier 3
    iban VARCHAR(34),                             -- Tier 3
    balance NUMERIC(18, 2) NOT NULL DEFAULT 0,   -- Tier 3
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP,
    updated_by VARCHAR(255)
    -- MISSING: is_deleted, deleted_at, deleted_by
    -- MISSING: retention_period, data_category
);

-- Transactions table: missing trace ID columns
CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    amount NUMERIC(18, 2) NOT NULL,              -- Tier 3
    transaction_date TIMESTAMP NOT NULL DEFAULT NOW(),
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP,
    updated_by VARCHAR(255)
    -- MISSING: reference_id / transaction_id / correlation_id
    -- MISSING: status column
    -- MISSING: retention_period, data_category
);

-- Health data table: Tier 4, no encryption
CREATE TABLE patient_health_records (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    diagnosis TEXT,                              -- Tier 4: health data
    medical_record TEXT,                         -- Tier 4
    prescription TEXT,                           -- Tier 4
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP,
    updated_by VARCHAR(255)
    -- VIOLATION: Tier 4 columns not stored as BYTEA
    -- MISSING: is_deleted, deleted_at, deleted_by
);

-- Lookup table without PK (violation)
CREATE TABLE country_codes (
    code CHAR(2) NOT NULL,
    name VARCHAR(100) NOT NULL
    -- MISSING: primary key
);

-- NOTE: consent_records and data_subject_requests are intentionally
-- omitted to trigger PDPL-CON-001 and PDPL-DSR-001 findings
