-- ============================================================
-- Microsoft SQL Server Sample DDL — intentionally non-compliant
-- for SAMA/PDPL compliance engine testing
-- ============================================================

CREATE TABLE customers (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    full_name NVARCHAR(255) NOT NULL,         -- Tier 1
    email NVARCHAR(255) NOT NULL,             -- Tier 1
    phone_number NVARCHAR(20),                -- Tier 1
    passport_number NVARCHAR(20),             -- Tier 1
    date_of_birth DATE,                       -- Tier 1
    home_address NVARCHAR(500),               -- Tier 1
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    created_by NVARCHAR(255) NOT NULL
    -- MISSING: updated_at, updated_by
    -- VIOLATION: Tier 1 columns stored as NVARCHAR, not VARBINARY
);

CREATE TABLE financial_accounts (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    account_number NVARCHAR(30) NOT NULL,     -- Tier 3
    iban NVARCHAR(34),                        -- Tier 3
    credit_card NVARCHAR(20),                 -- Tier 3
    balance DECIMAL(18, 2) NOT NULL DEFAULT 0,  -- Tier 3
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    created_by NVARCHAR(255) NOT NULL,
    updated_at DATETIME2,
    updated_by NVARCHAR(255),
    CONSTRAINT fk_fa_customer FOREIGN KEY (customer_id)
        REFERENCES customers(id) ON DELETE CASCADE  -- VIOLATION
    -- MISSING: is_deleted, deleted_at, deleted_by
    -- MISSING: retention_period, data_category
);

CREATE TABLE wire_transfers (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    account_id BIGINT NOT NULL,
    loan_amount DECIMAL(18, 2),               -- Tier 3
    transfer_date DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    created_by NVARCHAR(255) NOT NULL,
    updated_at DATETIME2,
    updated_by NVARCHAR(255),
    CONSTRAINT fk_wt_account FOREIGN KEY (account_id)
        REFERENCES financial_accounts(id)
    -- MISSING: reference_id, status, retention_period
);

-- Table with no PK
CREATE TABLE audit_settings (
    setting_name NVARCHAR(100) NOT NULL,
    setting_value NVARCHAR(500)
    -- MISSING: PRIMARY KEY
);

-- Well-formed consent table (partial — missing some columns)
CREATE TABLE consent_records (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    data_subject_id BIGINT NOT NULL,
    purpose NVARCHAR(500) NOT NULL,
    consent_given BIT NOT NULL DEFAULT 0,
    consent_date DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    -- MISSING: withdrawal_date, consent_version (LOW severity)
);
