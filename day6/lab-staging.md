# Lab 1 — Building the Staging Layer
## Al-Noor Bank | Mixed Feed Practice Lab
### SNB Data Management Capability Programme

---

> **What this lab is.**
>
> You are the data engineer responsible for the nightly integration
> pipeline at Al-Noor Bank. At midnight, the Core Banking System
> runs its end-of-day batch. Transaction records, customer updates,
> and Nafath KYC events land in your staging database.
>
> Your job: build the staging schema, load a realistic mixed feed,
> run quality checks, and prepare the data for ODS transformation.
>
> By the end of this lab you will have a working staging layer
> with real data quality issues to diagnose — the same issues
> that cause SAMA regulatory findings in production systems.

---

## Before You Start

**If you completed Day 3 labs:** Your `al_noor_bank` database
already exists with the retail schema. Skip to Step 2.

**If you are starting fresh:** Run Step 1 to create the database.

**Check your existing database:**
```sql
-- Run this in psql or pgAdmin
\l
-- Look for al_noor_bank in the list
```

---

## Step 1 — Database Setup (Skip if Day 3 database exists)

```sql
-- Create the database
CREATE DATABASE al_noor_bank ENCODING 'UTF8';

-- Connect to it
\c al_noor_bank

-- Create the retail schema (minimum needed for FK references)
CREATE SCHEMA retail;

CREATE TABLE retail.customer (
    customer_id         CHAR(10)     NOT NULL,
    customer_type       CHAR(1)      NOT NULL CHECK (customer_type IN ('I','C')),
    customer_segment    VARCHAR(30)  NOT NULL,
    kyc_status          VARCHAR(20)  NOT NULL DEFAULT 'PENDING',
    risk_rating         CHAR(1)      NOT NULL DEFAULT 'L',
    onboarding_channel  VARCHAR(20)  NOT NULL,
    onboarding_date     DATE         NOT NULL DEFAULT CURRENT_DATE,
    is_pep              BOOLEAN      NOT NULL DEFAULT FALSE,
    is_sanctioned       BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_customer PRIMARY KEY (customer_id)
);

CREATE TABLE retail.account (
    account_id      CHAR(16)      NOT NULL,
    account_number  VARCHAR(24)   NOT NULL,
    account_type    VARCHAR(20)   NOT NULL,
    balance         NUMERIC(18,2) NOT NULL DEFAULT 0,
    currency        CHAR(3)       NOT NULL DEFAULT 'SAR',
    status          VARCHAR(15)   NOT NULL DEFAULT 'ACTIVE',
    opened_date     DATE          NOT NULL,
    CONSTRAINT pk_account        PRIMARY KEY (account_id),
    CONSTRAINT uq_account_number UNIQUE (account_number)
);

-- Insert minimum reference data
INSERT INTO retail.customer
    (customer_id, customer_type, customer_segment, kyc_status,
     risk_rating, onboarding_channel, onboarding_date)
VALUES
    ('C000000001', 'I', 'PREMIUM',  'VERIFIED', 'L', 'DIGITAL', '2024-01-15'),
    ('C000000002', 'I', 'STANDARD', 'VERIFIED', 'M', 'BRANCH',  '2024-03-22'),
    ('C000000003', 'I', 'PREMIUM',  'VERIFIED', 'L', 'DIGITAL', '2024-06-01'),
    ('C000000004', 'C', 'CORPORATE','VERIFIED', 'L', 'BRANCH',  '2023-11-10'),
    ('C000000005', 'I', 'STANDARD', 'EXPIRED',  'H', 'DIGITAL', '2024-02-28');

INSERT INTO retail.account
    (account_id, account_number, account_type, balance, opened_date)
VALUES
    ('ACC0000000000001', 'SA1234567890123456780001', 'TAWARRUQ',   125000.00, '2024-01-15'),
    ('ACC0000000000002', 'SA1234567890123456780002', 'SAVINGS',     48500.00, '2024-03-22'),
    ('ACC0000000000003', 'SA1234567890123456780003', 'CURRENT',    320000.00, '2024-06-01'),
    ('ACC0000000000004', 'SA1234567890123456780004', 'CURRENT',   1850000.00, '2023-11-10'),
    ('ACC0000000000005', 'SA1234567890123456780005', 'TAWARRUQ',    12000.00, '2024-02-28');
```

---

## Step 2 — Create the Staging Schema

```sql
-- Connect to al_noor_bank if not already connected
\c al_noor_bank

CREATE SCHEMA IF NOT EXISTS staging;
```

### 2A — Transaction Staging Table

```sql
-- ============================================================
-- STG_TRANSACTION
-- Raw landing zone for CBS transaction feed.
-- Every column is VARCHAR — we preserve exactly what arrived.
-- Type conversion happens in the ODS, not here.
-- ============================================================
CREATE TABLE staging.stg_transaction (
    stg_id          BIGSERIAL     NOT NULL,

    -- Source system identifiers
    source_system   VARCHAR(50)   NOT NULL,  -- 'FLEXCUBE', 'T24'
    source_txn_id   VARCHAR(100)  NOT NULL,  -- CBS-assigned ID
    batch_id        VARCHAR(30)   NOT NULL,  -- which load run

    -- Raw payload — exactly as received from CBS
    -- Every field is VARCHAR to preserve source fidelity
    raw_account_id  VARCHAR(100),
    raw_amount      VARCHAR(50),   -- may arrive as '50000' or '50,000.00'
    raw_currency    VARCHAR(10),
    raw_txn_type    VARCHAR(50),   -- CBS codes: 'SI','SO','MP','DP' etc
    raw_txn_date    VARCHAR(30),   -- may arrive in any date format
    raw_channel     VARCHAR(50),
    raw_reference   VARCHAR(100),
    raw_description VARCHAR(500),

    -- Staging metadata
    received_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    load_status     VARCHAR(20)   NOT NULL DEFAULT 'LOADED'
        CHECK (load_status IN ('LOADED','FAILED','DUPLICATE','EXCLUDED')),
    load_notes      TEXT,         -- reason for FAILED or EXCLUDED

    CONSTRAINT pk_stg_transaction PRIMARY KEY (stg_id)
);

CREATE INDEX idx_stg_txn_batch
    ON staging.stg_transaction (batch_id, load_status);
CREATE INDEX idx_stg_txn_source
    ON staging.stg_transaction (source_system, source_txn_id);
```

### 2B — Customer Update Staging Table

```sql
-- ============================================================
-- STG_CUSTOMER_UPDATE
-- Raw landing zone for CBS customer record updates.
-- Customer address changes, segment changes, risk rating updates.
-- ============================================================
CREATE TABLE staging.stg_customer_update (
    stg_id          BIGSERIAL     NOT NULL,
    source_system   VARCHAR(50)   NOT NULL,
    source_cust_id  VARCHAR(100)  NOT NULL,
    batch_id        VARCHAR(30)   NOT NULL,

    -- Raw update payload
    raw_customer_id VARCHAR(100),
    update_type     VARCHAR(50),   -- 'SEGMENT_CHANGE','RISK_RATING','KYC_STATUS'
    raw_old_value   VARCHAR(200),
    raw_new_value   VARCHAR(200),
    raw_updated_by  VARCHAR(100),
    raw_updated_at  VARCHAR(30),
    raw_reason      VARCHAR(500),

    -- Staging metadata
    received_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    load_status     VARCHAR(20)   NOT NULL DEFAULT 'LOADED'
        CHECK (load_status IN ('LOADED','FAILED','DUPLICATE','EXCLUDED')),
    load_notes      TEXT,

    CONSTRAINT pk_stg_customer_update PRIMARY KEY (stg_id)
);

CREATE INDEX idx_stg_cust_batch
    ON staging.stg_customer_update (batch_id, load_status);
```

### 2C — KYC Event Staging Table

```sql
-- ============================================================
-- STG_KYC_EVENT
-- Raw landing zone for Nafath eKYC verification callbacks.
-- These arrive as API responses — JSON payload preserved raw.
-- ============================================================
CREATE TABLE staging.stg_kyc_event (
    stg_id              BIGSERIAL     NOT NULL,
    source_system       VARCHAR(50)   NOT NULL DEFAULT 'NAFATH',
    batch_id            VARCHAR(30)   NOT NULL,

    -- Raw API response fields
    raw_application_id  VARCHAR(100),
    raw_customer_id     VARCHAR(100),
    raw_national_id     VARCHAR(50),   -- hashed before landing — never plain text
    raw_verification_status VARCHAR(50),
    raw_verified_at     VARCHAR(30),
    raw_response_code   VARCHAR(20),
    raw_response_msg    VARCHAR(500),
    raw_nafath_ref      VARCHAR(100),  -- Nafath's own reference number
    full_payload        JSONB,         -- complete API response preserved

    -- Staging metadata
    received_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    load_status         VARCHAR(20)   NOT NULL DEFAULT 'LOADED'
        CHECK (load_status IN ('LOADED','FAILED','DUPLICATE','EXCLUDED')),
    load_notes          TEXT,

    CONSTRAINT pk_stg_kyc_event PRIMARY KEY (stg_id)
);

CREATE INDEX idx_stg_kyc_batch
    ON staging.stg_kyc_event (batch_id, load_status);
```

### 2D — Staging Batch Registry

```sql
-- ============================================================
-- STG_BATCH_REGISTRY
-- One row per batch run. Tracks every load that ever happened.
-- If SAMA asks "what ran on the night of 14 April 2025?" —
-- this table has the answer.
-- ============================================================
CREATE TABLE staging.stg_batch_registry (
    batch_id          VARCHAR(30)   NOT NULL,
    source_system     VARCHAR(50)   NOT NULL,
    feed_type         VARCHAR(50)   NOT NULL,  -- 'TRANSACTION','CUSTOMER','KYC'
    batch_start       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    batch_end         TIMESTAMPTZ,
    records_received  INTEGER       NOT NULL DEFAULT 0,
    records_loaded    INTEGER       NOT NULL DEFAULT 0,
    records_failed    INTEGER       NOT NULL DEFAULT 0,
    records_duplicate INTEGER       NOT NULL DEFAULT 0,
    batch_status      VARCHAR(20)   NOT NULL DEFAULT 'RUNNING'
        CHECK (batch_status IN ('RUNNING','COMPLETED','FAILED','PARTIAL')),
    error_message     TEXT,

    CONSTRAINT pk_batch_registry PRIMARY KEY (batch_id)
);
```

**Verify your staging schema:**
```sql
SELECT schemaname, tablename
FROM   pg_tables
WHERE  schemaname = 'staging'
ORDER BY tablename;

-- Expected output:
-- staging | stg_batch_registry
-- staging | stg_customer_update
-- staging | stg_kyc_event
-- staging | stg_transaction
```

---

## Step 3 — Register the Batch Run

```sql
-- ============================================================
-- Every batch starts by registering itself.
-- This is the first thing the pipeline does — before any data loads.
-- If the batch crashes, the registry row is still there.
-- The operations team can see a RUNNING batch that never completed.
-- ============================================================

INSERT INTO staging.stg_batch_registry
    (batch_id, source_system, feed_type, records_received, batch_status)
VALUES
    ('BATCH-2025-0415-TXN',  'FLEXCUBE', 'TRANSACTION', 0, 'RUNNING'),
    ('BATCH-2025-0415-CUST', 'FLEXCUBE', 'CUSTOMER',    0, 'RUNNING'),
    ('BATCH-2025-0415-KYC',  'NAFATH',   'KYC',         0, 'RUNNING');
```

---

## Step 4 — Load the Mixed Feed

This is the midnight batch arriving from the CBS and Nafath.
Read every INSERT carefully — some records are clean,
some have issues you will diagnose in Step 5.

### 4A — Transaction Feed (15 records)

```sql
INSERT INTO staging.stg_transaction
    (source_system, source_txn_id, batch_id,
     raw_account_id, raw_amount, raw_currency,
     raw_txn_type, raw_txn_date, raw_channel,
     raw_reference, raw_description, load_status)
VALUES

-- ── CLEAN RECORDS ──────────────────────────────────────────
-- Standard SARIE inbound transfer
('FLEXCUBE', 'FX-TXN-20250414-000001', 'BATCH-2025-0415-TXN',
 'ACC0000000000001', '15000.00', 'SAR',
 'SI', '2025-04-14 23:01:14', 'SARIE',
 'UETR-f47ac10b-58cc', 'Inbound SARIE transfer from Riyad Bank',
 'LOADED'),

-- Murabaha instalment payment
('FLEXCUBE', 'FX-TXN-20250414-000002', 'BATCH-2025-0415-TXN',
 'ACC0000000000001', '2437.50', 'SAR',
 'MP', '2025-04-14 09:15:33', 'MOBILE',
 'MRB-2024-0042-PMT-003', 'Murabaha instalment payment - contract MRB-2024-0042',
 'LOADED'),

-- SADAD bill payment
('FLEXCUBE', 'FX-TXN-20250414-000003', 'BATCH-2025-0415-TXN',
 'ACC0000000000002', '850.00', 'SAR',
 'BP', '2025-04-14 11:22:07', 'MOBILE',
 'SADAD-REF-9087234561', 'Electricity bill payment - Saudi Electricity Company',
 'LOADED'),

-- ATM cash withdrawal
('FLEXCUBE', 'FX-TXN-20250414-000004', 'BATCH-2025-0415-TXN',
 'ACC0000000000003', '2000.00', 'SAR',
 'WD', '2025-04-14 14:45:19', 'ATM',
 'ATM-AL-OLAYA-00421', 'Cash withdrawal - Al Olaya branch ATM',
 'LOADED'),

-- Corporate SARIE outbound - large amount (AML threshold: SAR 60,000)
('FLEXCUBE', 'FX-TXN-20250414-000005', 'BATCH-2025-0415-TXN',
 'ACC0000000000004', '85000.00', 'SAR',
 'SO', '2025-04-14 16:33:55', 'INTERNET',
 'UETR-a891bc23-44dd', 'Outbound SARIE - supplier payment to Al-Marai Co',
 'LOADED'),

-- Internal transfer between Al-Noor accounts
('FLEXCUBE', 'FX-TXN-20250414-000006', 'BATCH-2025-0415-TXN',
 'ACC0000000000002', '5000.00', 'SAR',
 'IT', '2025-04-14 19:08:44', 'MOBILE',
 'INT-TRF-20250414-0061', 'Internal transfer to own savings account',
 'LOADED'),

-- SWIFT international transfer
('FLEXCUBE', 'FX-TXN-20250414-000007', 'BATCH-2025-0415-TXN',
 'ACC0000000000003', '12500.00', 'USD',
 'SW', '2025-04-14 10:17:22', 'INTERNET',
 'SWIFT-UETR-c334de12', 'International wire transfer to HSBC UK',
 'LOADED'),

-- ── RECORDS WITH DATA QUALITY ISSUES ───────────────────────
-- Issue 1: Amount arrives as formatted string with comma
-- CBS sent '50,000.00' — cannot cast directly to NUMERIC
('FLEXCUBE', 'FX-TXN-20250414-000008', 'BATCH-2025-0415-TXN',
 'ACC0000000000001', '50,000.00', 'SAR',
 'SI', '2025-04-14 08:44:12', 'SARIE',
 'UETR-b221cc45-77ee', 'Inbound SARIE - salary credit from Al-Noor HR',
 'LOADED'),

-- Issue 2: Unknown transaction type code from CBS
-- 'XF' is not in the canonical mapping table
('FLEXCUBE', 'FX-TXN-20250414-000009', 'BATCH-2025-0415-TXN',
 'ACC0000000000002', '750.00', 'SAR',
 'XF', '2025-04-14 13:22:01', 'BRANCH',
 'FEE-REF-20250414-0019', 'Fee charge - account maintenance',
 'LOADED'),

-- Issue 3: Date in wrong format — DD/MM/YYYY instead of ISO
('FLEXCUBE', 'FX-TXN-20250414-000010', 'BATCH-2025-0415-TXN',
 'ACC0000000000003', '3200.00', 'SAR',
 'DP', '14/04/2025', 'BRANCH',
 'DEP-BRANCH-0054', 'Cash deposit at Al Malaz branch',
 'LOADED'),

-- Issue 4: Account ID does not exist in retail.account
-- This is an orphaned transaction — references a closed account
('FLEXCUBE', 'FX-TXN-20250414-000011', 'BATCH-2025-0415-TXN',
 'ACC0000000000099', '1500.00', 'SAR',
 'WD', '2025-04-14 17:55:33', 'ATM',
 'ATM-MALAZ-00187', 'Cash withdrawal - unknown account',
 'LOADED'),

-- Issue 5: Exact duplicate of record 000001 — CBS resent it
-- Same source_txn_id, same amount, same everything
('FLEXCUBE', 'FX-TXN-20250414-000001', 'BATCH-2025-0415-TXN',
 'ACC0000000000001', '15000.00', 'SAR',
 'SI', '2025-04-14 23:01:14', 'SARIE',
 'UETR-f47ac10b-58cc', 'Inbound SARIE transfer from Riyad Bank',
 'LOADED'),

-- Issue 6: Amount is NULL — CBS failed to send the field
('FLEXCUBE', 'FX-TXN-20250414-000012', 'BATCH-2025-0415-TXN',
 'ACC0000000000005', NULL, 'SAR',
 'MP', '2025-04-14 20:11:49', 'MOBILE',
 'MRB-2024-0088-PMT-001', 'Murabaha instalment payment - contract MRB-2024-0088',
 'LOADED'),

-- Issue 7: Structuring detection candidate
-- Three transactions from same account, same day, all just below SAR 60,000
('FLEXCUBE', 'FX-TXN-20250414-000013', 'BATCH-2025-0415-TXN',
 'ACC0000000000004', '59500.00', 'SAR',
 'SO', '2025-04-14 09:05:11', 'INTERNET',
 'UETR-d556ff89-11aa', 'Transfer to Al-Rajhi Bank',
 'LOADED'),

('FLEXCUBE', 'FX-TXN-20250414-000014', 'BATCH-2025-0415-TXN',
 'ACC0000000000004', '58900.00', 'SAR',
 'SO', '2025-04-14 11:44:22', 'INTERNET',
 'UETR-e667aa90-22bb', 'Transfer to NCB Bank',
 'LOADED'),

('FLEXCUBE', 'FX-TXN-20250414-000015', 'BATCH-2025-0415-TXN',
 'ACC0000000000004', '57800.00', 'SAR',
 'SO', '2025-04-14 14:23:07', 'INTERNET',
 'UETR-f778bb01-33cc', 'Transfer to Banque Saudi Fransi',
 'LOADED');
```

### 4B — Customer Update Feed (5 records)

```sql
INSERT INTO staging.stg_customer_update
    (source_system, source_cust_id, batch_id,
     raw_customer_id, update_type, raw_old_value, raw_new_value,
     raw_updated_by, raw_updated_at, raw_reason, load_status)
VALUES

-- Clean: risk rating upgrade after AML review
('FLEXCUBE', 'C000000002', 'BATCH-2025-0415-CUST',
 'C000000002', 'RISK_RATING', 'L', 'M',
 'AML_SYSTEM_v3', '2025-04-14 08:00:00',
 'Periodic AML review — elevated transaction pattern detected',
 'LOADED'),

-- Clean: KYC status renewal
('FLEXCUBE', 'C000000005', 'BATCH-2025-0415-CUST',
 'C000000005', 'KYC_STATUS', 'EXPIRED', 'PENDING',
 'KYC_OFFICER_A42', '2025-04-14 10:30:00',
 'KYC renewal initiated — customer contacted for documentation',
 'LOADED'),

-- Clean: segment upgrade
('FLEXCUBE', 'C000000003', 'BATCH-2025-0415-CUST',
 'C000000003', 'SEGMENT_CHANGE', 'STANDARD', 'PREMIUM',
 'RM_OFFICER_B17', '2025-04-14 14:15:00',
 'Balance threshold crossed — auto-upgrade to PREMIUM segment',
 'LOADED'),

-- Issue: customer_id does not exist in retail.customer
('FLEXCUBE', 'C000000099', 'BATCH-2025-0415-CUST',
 'C000000099', 'RISK_RATING', 'L', 'H',
 'AML_SYSTEM_v3', '2025-04-14 09:45:00',
 'High-risk flag from OFAC watchlist match',
 'LOADED'),

-- Issue: new_value is not a valid risk_rating value
('FLEXCUBE', 'C000000001', 'BATCH-2025-0415-CUST',
 'C000000001', 'RISK_RATING', 'L', 'VERY_HIGH',
 'AML_SYSTEM_v3', '2025-04-14 11:00:00',
 'System error — invalid rating code sent by AML system',
 'LOADED');
```

### 4C — KYC Event Feed (4 records)

```sql
INSERT INTO staging.stg_kyc_event
    (source_system, batch_id,
     raw_application_id, raw_customer_id, raw_national_id,
     raw_verification_status, raw_verified_at,
     raw_response_code, raw_response_msg, raw_nafath_ref,
     full_payload, load_status)
VALUES

-- Clean: successful Nafath verification
('NAFATH', 'BATCH-2025-0415-KYC',
 'APP-2025-0389', 'C000000001',
 'sha256:a3f8b2c1d4e5f67890abcdef1234567890abcdef1234567890abcdef12345678',
 'VERIFIED', '2025-04-14 09:14:22',
 'NAF-200', 'Identity verified successfully', 'NAF-REF-20250414-0389',
 '{"status":"VERIFIED","nafath_ref":"NAF-REF-20250414-0389",
   "verification_method":"ABSHER_OTP","response_time_ms":1240}',
 'LOADED'),

-- Clean: verification failed — NID mismatch
('NAFATH', 'BATCH-2025-0415-KYC',
 'APP-2025-0391', 'C000000002',
 'sha256:b4g9c3d2e5f68901bcdefg2345678901bcdefg2345678901bcdefg23456789',
 'FAILED', '2025-04-14 10:05:41',
 'NAF-422', 'Name does not match NID record', 'NAF-REF-20250414-0391',
 '{"status":"FAILED","error_code":"NAF-422",
   "error_detail":"NAME_MISMATCH","response_time_ms":987}',
 'LOADED'),

-- Issue: response arrived with no application_id — cannot trace back
('NAFATH', 'BATCH-2025-0415-KYC',
 NULL, 'C000000003',
 'sha256:c5h0d4e3f69012cdefgh3456789012cdefgh3456789012cdefgh34567890',
 'VERIFIED', '2025-04-14 11:33:09',
 'NAF-200', 'Identity verified successfully', 'NAF-REF-20250414-0394',
 '{"status":"VERIFIED","nafath_ref":"NAF-REF-20250414-0394",
   "response_time_ms":1105}',
 'LOADED'),

-- Issue: timeout — Nafath did not respond within SLA
('NAFATH', 'BATCH-2025-0415-KYC',
 'APP-2025-0402', 'C000000005',
 NULL,
 'TIMEOUT', '2025-04-14 14:22:55',
 'NAF-504', 'Nafath service timeout after 30000ms', NULL,
 '{"status":"TIMEOUT","error_code":"NAF-504",
   "response_time_ms":30000,"retry_attempted":true}',
 'LOADED');
```

---

## Step 5 — Data Quality Checks

Run every query below. Study the results before moving on.
Each query surfaces a different class of data quality problem.

### Check 1 — Overall load summary by batch

```sql
SELECT
    batch_id,
    COUNT(*)                                          AS total_records,
    COUNT(*) FILTER (WHERE load_status = 'LOADED')   AS loaded,
    COUNT(*) FILTER (WHERE load_status = 'FAILED')   AS failed,
    COUNT(*) FILTER (WHERE load_status = 'DUPLICATE') AS duplicates
FROM staging.stg_transaction
GROUP BY batch_id

UNION ALL

SELECT
    batch_id,
    COUNT(*),
    COUNT(*) FILTER (WHERE load_status = 'LOADED'),
    COUNT(*) FILTER (WHERE load_status = 'FAILED'),
    COUNT(*) FILTER (WHERE load_status = 'DUPLICATE')
FROM staging.stg_customer_update
GROUP BY batch_id

UNION ALL

SELECT
    batch_id,
    COUNT(*),
    COUNT(*) FILTER (WHERE load_status = 'LOADED'),
    COUNT(*) FILTER (WHERE load_status = 'FAILED'),
    COUNT(*) FILTER (WHERE load_status = 'DUPLICATE')
FROM staging.stg_kyc_event
GROUP BY batch_id

ORDER BY batch_id;
```

---

### Check 2 — Find duplicate transactions

```sql
-- Same source_txn_id appearing more than once = CBS sent it twice
SELECT
    source_txn_id,
    COUNT(*)        AS occurrence_count,
    MIN(stg_id)     AS first_stg_id,
    MAX(stg_id)     AS duplicate_stg_id
FROM staging.stg_transaction
WHERE batch_id = 'BATCH-2025-0415-TXN'
GROUP BY source_txn_id
HAVING COUNT(*) > 1;

-- Expected: FX-TXN-20250414-000001 appears twice
```

**Action — mark duplicates so they do not enter the ODS:**
```sql
UPDATE staging.stg_transaction
SET    load_status = 'DUPLICATE',
       load_notes  = 'Duplicate source_txn_id — first occurrence retained'
WHERE  source_txn_id = 'FX-TXN-20250414-000001'
AND    stg_id = (
    SELECT MAX(stg_id)
    FROM   staging.stg_transaction
    WHERE  source_txn_id = 'FX-TXN-20250414-000001'
);

-- Verify: only one row remains LOADED for this txn_id
SELECT stg_id, source_txn_id, load_status, load_notes
FROM   staging.stg_transaction
WHERE  source_txn_id = 'FX-TXN-20250414-000001'
ORDER BY stg_id;
```

---

### Check 3 — Find NULL amounts (mandatory field)

```sql
SELECT
    stg_id,
    source_txn_id,
    raw_account_id,
    raw_amount,
    raw_txn_type,
    raw_txn_date
FROM staging.stg_transaction
WHERE raw_amount IS NULL
AND   batch_id = 'BATCH-2025-0415-TXN';

-- Expected: FX-TXN-20250414-000012 — Murabaha payment with no amount
```

**Action — mark as FAILED, reason recorded:**
```sql
UPDATE staging.stg_transaction
SET    load_status = 'FAILED',
       load_notes  = 'Mandatory field raw_amount is NULL — cannot transform to ODS'
WHERE  raw_amount IS NULL
AND    batch_id = 'BATCH-2025-0415-TXN';
```

---

### Check 4 — Find amounts that cannot be cast to NUMERIC

```sql
-- Amounts with commas or non-numeric characters
SELECT
    stg_id,
    source_txn_id,
    raw_amount
FROM staging.stg_transaction
WHERE batch_id = 'BATCH-2025-0415-TXN'
AND   load_status = 'LOADED'
AND   raw_amount !~ '^[0-9]+(\.[0-9]+)?$';

-- Expected: FX-TXN-20250414-000008 — '50,000.00' has a comma
```

**The ODS transformation will handle this — but staging flags it:**
```sql
UPDATE staging.stg_transaction
SET    load_notes = 'Amount contains formatting characters — '
                  || 'ODS transformation will strip commas before cast'
WHERE  raw_amount !~ '^[0-9]+(\.[0-9]+)?$'
AND    batch_id = 'BATCH-2025-0415-TXN';

-- This record stays LOADED — it CAN be transformed.
-- The note documents what transformation is needed.
```

---

### Check 5 — Find unknown transaction type codes

```sql
-- The canonical mapping: SI, SO, MP, BP, WD, IT, SW, DP, FE
-- Anything outside this list is unknown
SELECT
    stg_id,
    source_txn_id,
    raw_txn_type,
    raw_description
FROM staging.stg_transaction
WHERE batch_id = 'BATCH-2025-0415-TXN'
AND   load_status = 'LOADED'
AND   raw_txn_type NOT IN ('SI','SO','MP','BP','WD','IT','SW','DP','FE');

-- Expected: FX-TXN-20250414-000009 — 'XF' has no canonical mapping
```

**Action:**
```sql
UPDATE staging.stg_transaction
SET    load_status = 'FAILED',
       load_notes  = 'Unknown txn_type code XF — no canonical mapping exists. '
                  || 'Referred to CBS team for code definition.'
WHERE  raw_txn_type = 'XF'
AND    batch_id = 'BATCH-2025-0415-TXN';
```

---

### Check 6 — Find date format issues

```sql
-- Dates that are NOT in ISO format YYYY-MM-DD HH:MI:SS
SELECT
    stg_id,
    source_txn_id,
    raw_txn_date
FROM staging.stg_transaction
WHERE batch_id = 'BATCH-2025-0415-TXN'
AND   load_status = 'LOADED'
AND   raw_txn_date !~ '^\d{4}-\d{2}-\d{2}';

-- Expected: FX-TXN-20250414-000010 — '14/04/2025' is DD/MM/YYYY
```

**Action — note the format, ODS transformation converts it:**
```sql
UPDATE staging.stg_transaction
SET    load_notes = 'Date format DD/MM/YYYY detected — '
                  || 'ODS transformation will convert to ISO using TO_DATE'
WHERE  raw_txn_date !~ '^\d{4}-\d{2}-\d{2}'
AND    batch_id = 'BATCH-2025-0415-TXN';
```

---

### Check 7 — Find orphaned transactions (account not in system)

```sql
SELECT
    st.stg_id,
    st.source_txn_id,
    st.raw_account_id,
    st.raw_amount
FROM staging.stg_transaction st
LEFT JOIN retail.account ra
    ON st.raw_account_id = ra.account_id
WHERE ra.account_id IS NULL
AND   st.batch_id = 'BATCH-2025-0415-TXN'
AND   st.load_status = 'LOADED';

-- Expected: FX-TXN-20250414-000011 — ACC0000000000099 does not exist
```

**Action:**
```sql
UPDATE staging.stg_transaction
SET    load_status = 'FAILED',
       load_notes  = 'Account ACC0000000000099 not found in retail.account. '
                  || 'Possible closed account or CBS data error. '
                  || 'Referred to Operations team for investigation.'
WHERE  raw_account_id = 'ACC0000000000099'
AND    batch_id = 'BATCH-2025-0415-TXN';
```

---

### Check 8 — Structuring detection (AML threshold alert)

```sql
-- Three or more outbound transactions from the same account
-- on the same day, each below SAR 60,000 (SAMA reporting threshold)
-- This is a structuring pattern indicator
SELECT
    raw_account_id,
    COUNT(*)                     AS transaction_count,
    SUM(raw_amount::NUMERIC)     AS total_amount_sar,
    MIN(raw_amount::NUMERIC)     AS min_single_amount,
    MAX(raw_amount::NUMERIC)     AS max_single_amount
FROM staging.stg_transaction
WHERE batch_id = 'BATCH-2025-0415-TXN'
AND   load_status = 'LOADED'
AND   raw_txn_type IN ('SO', 'SW')   -- outbound only
AND   raw_amount::NUMERIC < 60000    -- each below reporting threshold
GROUP BY raw_account_id
HAVING COUNT(*) >= 3
ORDER BY total_amount_sar DESC;

-- Expected: ACC0000000000004 — 3 outbound transfers totalling ~SAR 176,200
-- All just below SAR 60,000 each. Classic structuring pattern.
```

```sql
-- Flag these for AML team review
UPDATE staging.stg_transaction
SET    load_notes = COALESCE(load_notes, '') ||
                   ' | AML FLAG: Structuring pattern detected — '
                   || '3+ outbound transfers below SAR 60,000 threshold on same day'
WHERE  raw_account_id = 'ACC0000000000004'
AND    raw_txn_type IN ('SO', 'SW')
AND    raw_amount::NUMERIC < 60000
AND    batch_id = 'BATCH-2025-0415-TXN';
```

---

### Check 9 — Customer updates for non-existent customers

```sql
SELECT
    su.stg_id,
    su.raw_customer_id,
    su.update_type,
    su.raw_new_value
FROM staging.stg_customer_update su
LEFT JOIN retail.customer rc
    ON su.raw_customer_id = rc.customer_id
WHERE rc.customer_id IS NULL
AND   su.batch_id = 'BATCH-2025-0415-CUST';

-- Expected: C000000099 — does not exist in retail.customer
```

```sql
UPDATE staging.stg_customer_update
SET    load_status = 'FAILED',
       load_notes  = 'Customer C000000099 not found in retail.customer'
WHERE  raw_customer_id = 'C000000099'
AND    batch_id = 'BATCH-2025-0415-CUST';
```

---

### Check 10 — KYC events with no application reference

```sql
SELECT
    stg_id,
    raw_customer_id,
    raw_verification_status,
    raw_response_code,
    load_notes
FROM staging.stg_kyc_event
WHERE raw_application_id IS NULL
AND   batch_id = 'BATCH-2025-0415-KYC';

-- Expected: one record — Nafath sent a response with no application_id
-- Cannot be traced back to a specific application
-- This is an UNRESOLVABLE quality issue at the staging level
```

```sql
UPDATE staging.stg_kyc_event
SET    load_status = 'FAILED',
       load_notes  = 'No application_id in Nafath response — cannot trace '
                  || 'to a product_application record. '
                  || 'Nafath reference NAF-REF-20250414-0394 sent to '
                  || 'integration team for manual matching.'
WHERE  raw_application_id IS NULL
AND    batch_id = 'BATCH-2025-0415-KYC';
```

---

## Step 6 — Final Status Summary

```sql
-- ============================================================
-- THE STAGING HEALTH REPORT
-- Run this before the ODS transformation begins.
-- Every LOADED record is ready for transformation.
-- Every FAILED record is documented with a reason.
-- Every DUPLICATE record is marked — only the first is used.
-- ============================================================

SELECT
    'TRANSACTION'           AS feed_type,
    load_status,
    COUNT(*)                AS record_count
FROM staging.stg_transaction
WHERE batch_id = 'BATCH-2025-0415-TXN'
GROUP BY load_status

UNION ALL

SELECT
    'CUSTOMER_UPDATE',
    load_status,
    COUNT(*)
FROM staging.stg_customer_update
WHERE batch_id = 'BATCH-2025-0415-CUST'
GROUP BY load_status

UNION ALL

SELECT
    'KYC_EVENT',
    load_status,
    COUNT(*)
FROM staging.stg_kyc_event
WHERE batch_id = 'BATCH-2025-0415-KYC'
GROUP BY load_status

ORDER BY feed_type, load_status;
```

**Expected result:**

```
feed_type        | load_status | record_count
─────────────────┼─────────────┼─────────────
CUSTOMER_UPDATE  | FAILED      | 1
CUSTOMER_UPDATE  | LOADED      | 4
KYC_EVENT        | FAILED      | 1
KYC_EVENT        | LOADED      | 3
TRANSACTION      | DUPLICATE   | 1
TRANSACTION      | FAILED      | 3
TRANSACTION      | LOADED      | 11
```

---

## Step 7 — Update the Batch Registry

```sql
-- ============================================================
-- Close out the batch runs with final counts.
-- This is what the operations team dashboard reads at 6:00 AM.
-- ============================================================

UPDATE staging.stg_batch_registry
SET
    batch_end        = NOW(),
    records_received = 15,
    records_loaded   = (SELECT COUNT(*) FROM staging.stg_transaction
                        WHERE batch_id = 'BATCH-2025-0415-TXN'
                        AND load_status = 'LOADED'),
    records_failed   = (SELECT COUNT(*) FROM staging.stg_transaction
                        WHERE batch_id = 'BATCH-2025-0415-TXN'
                        AND load_status = 'FAILED'),
    records_duplicate = (SELECT COUNT(*) FROM staging.stg_transaction
                         WHERE batch_id = 'BATCH-2025-0415-TXN'
                         AND load_status = 'DUPLICATE'),
    batch_status     = 'COMPLETED'
WHERE batch_id = 'BATCH-2025-0415-TXN';

UPDATE staging.stg_batch_registry
SET
    batch_end        = NOW(),
    records_received = 5,
    records_loaded   = (SELECT COUNT(*) FROM staging.stg_customer_update
                        WHERE batch_id = 'BATCH-2025-0415-CUST'
                        AND load_status = 'LOADED'),
    records_failed   = (SELECT COUNT(*) FROM staging.stg_customer_update
                        WHERE batch_id = 'BATCH-2025-0415-CUST'
                        AND load_status = 'FAILED'),
    batch_status     = 'COMPLETED'
WHERE batch_id = 'BATCH-2025-0415-CUST';

UPDATE staging.stg_batch_registry
SET
    batch_end        = NOW(),
    records_received = 4,
    records_loaded   = (SELECT COUNT(*) FROM staging.stg_kyc_event
                        WHERE batch_id = 'BATCH-2025-0415-KYC'
                        AND load_status = 'LOADED'),
    records_failed   = (SELECT COUNT(*) FROM staging.stg_kyc_event
                        WHERE batch_id = 'BATCH-2025-0415-KYC'
                        AND load_status = 'FAILED'),
    batch_status     = 'COMPLETED'
WHERE batch_id = 'BATCH-2025-0415-KYC';

-- Verify the registry
SELECT
    batch_id, feed_type, batch_start, batch_end,
    records_received, records_loaded, records_failed,
    records_duplicate, batch_status
FROM staging.stg_batch_registry
ORDER BY batch_id;
```

---

## Step 8 — Bonus: Preview the ODS Transformation

This is what the LOADED records look like after transformation.
You are not building the ODS table here — just seeing
what the transformation logic produces.

```sql
-- ============================================================
-- PREVIEW: What LOADED transactions become in the ODS
-- The transformation:
--   1. Strips commas from amounts → casts to NUMERIC
--   2. Converts CBS codes to canonical txn_type values
--   3. Standardises date formats to TIMESTAMPTZ
--   4. Carries stg_id for lineage traceability
-- ============================================================

SELECT
    stg_id                                         AS stg_source_id,
    source_txn_id                                  AS source_txn_id,
    raw_account_id                                 AS account_id,

    -- Amount transformation: strip comma, cast to NUMERIC
    REPLACE(raw_amount, ',', '')::NUMERIC(18,2)    AS amount_sar,

    raw_currency                                   AS currency,

    -- Canonical txn_type mapping
    CASE raw_txn_type
        WHEN 'SI' THEN 'SARIE_IN'
        WHEN 'SO' THEN 'SARIE_OUT'
        WHEN 'MP' THEN 'MRB_PMT'
        WHEN 'BP' THEN 'SADAD_PMT'
        WHEN 'WD' THEN 'DEBIT'
        WHEN 'IT' THEN 'INTERNAL'
        WHEN 'SW' THEN 'SWIFT_OUT'
        WHEN 'DP' THEN 'CREDIT'
        WHEN 'FE' THEN 'FEE'
        ELSE 'UNKNOWN_' || raw_txn_type
    END                                            AS txn_type,

    -- Date normalisation
    CASE
        WHEN raw_txn_date ~ '^\d{4}-\d{2}-\d{2}'
        THEN raw_txn_date::TIMESTAMPTZ
        WHEN raw_txn_date ~ '^\d{2}/\d{2}/\d{4}'
        THEN TO_TIMESTAMP(raw_txn_date, 'DD/MM/YYYY')
        ELSE NULL
    END                                            AS txn_timestamp,

    raw_channel                                    AS channel,
    raw_reference                                  AS external_reference,
    batch_id                                       AS stg_batch_id

FROM staging.stg_transaction
WHERE batch_id   = 'BATCH-2025-0415-TXN'
AND   load_status = 'LOADED'
ORDER BY stg_id;
```

---

## Lab Complete — What You Built

```
✓ Three staging tables with appropriate metadata columns
✓ A batch registry tracking every load run
✓ 24 realistic source records across three feed types
✓ 8 data quality checks surfacing 7 distinct issue types:
    → Duplicate source records
    → NULL mandatory fields
    → Non-castable amount formats
    → Unknown source codes
    → Invalid date formats
    → Orphaned account references
    → AML structuring detection pattern
✓ Status classification: LOADED / FAILED / DUPLICATE
✓ Audit trail: every issue documented with load_notes
✓ Batch registry closed with final counts
✓ ODS transformation preview showing canonicalisation logic
```

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*