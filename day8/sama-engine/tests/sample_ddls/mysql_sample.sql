-- ============================================================
-- MySQL Sample DDL — intentionally non-compliant
-- for SAMA/PDPL compliance engine testing
-- ============================================================

CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,          -- Tier 1
    email VARCHAR(255) UNIQUE NOT NULL,        -- Tier 1
    mobile_number VARCHAR(20),                 -- Tier 1
    national_number VARCHAR(20),               -- Tier 1
    date_of_birth DATE,                        -- Tier 1
    ip_address VARCHAR(45),                    -- Tier 2
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL
    -- MISSING: updated_at, updated_by
    -- VIOLATION: Tier 1 fields not stored as VARBINARY
);

CREATE TABLE bank_accounts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    account_number VARCHAR(30) UNIQUE NOT NULL,  -- Tier 3
    salary DECIMAL(18, 2),                        -- Tier 3
    balance DECIMAL(18, 2) NOT NULL DEFAULT 0.00,  -- Tier 3
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at DATETIME,
    updated_by VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE  -- VIOLATION
);

CREATE TABLE payments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id BIGINT NOT NULL,
    transaction_amount DECIMAL(18, 2) NOT NULL,  -- Tier 3
    payment_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at DATETIME,
    updated_by VARCHAR(255),
    FOREIGN KEY (account_id) REFERENCES bank_accounts(id)
    -- MISSING: reference_id, status
    -- MISSING: retention_period, data_category
);

-- Sensitive categories table: Tier 4
CREATE TABLE employee_profiles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    religion VARCHAR(100),                    -- Tier 4
    racial_origin VARCHAR(100),               -- Tier 4
    disability VARCHAR(255),                  -- Tier 4
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at DATETIME,
    updated_by VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE  -- VIOLATION
    -- VIOLATION: Tier 4 columns not VARBINARY
);
