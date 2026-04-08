# SNB Data Engineering Programme
## Guided Lab 3A — Create and Populate the Al-Noor Bank Database
---

> **Welcome to Lab 3A.**
>
> In this lab you will build the complete Al-Noor Bank database
> from scratch — every schema, every table, every row of data.
> By the end of this lab you will have a fully working banking
> database that you can query, explore, and build on.
>
> Every step is explained fully. Read the comments before
> running each block — the comments are where the learning is.
>
> Take your time. There is no rush.

---

## What You Will Build

```
al_noor_bank DATABASE
│
├── retail SCHEMA
│   ├── branch           (4 branches across Saudi Arabia)
│   ├── customer         (4 customers with Arabic names)
│   ├── account          (4 accounts, one per customer)
│   ├── customer_account (5 relationships incl. one joint)
│   └── transaction      (6 transactions, partitioned by year)
│
├── finance SCHEMA
│   ├── murabaha_contract  (1 active Islamic finance contract)
│   └── murabaha_schedule  (3 instalments: 2 paid, 1 pending)
│
└── compliance SCHEMA
    ├── kyc_record  (1 expired KYC review)
    └── aml_alert   (1 open structuring alert)
```

---

## Before You Begin

Open **pgAdmin** and connect to your PostgreSQL server.
Open the **Query Tool**.
You are ready to start.

---

## Step 1 — Create the Database

```sql
-- ============================================================
-- WHY UTF8?
--
-- Al-Noor Bank stores customer names in Arabic.
-- UTF8 is the encoding that supports Arabic characters.
-- Without it, Arabic text either fails on insert or
-- appears as garbled characters (??????).
--
-- This cannot be changed after the database is created.
-- Always specify UTF8 from the start.
-- ============================================================

CREATE DATABASE al_noor_bank
    ENCODING    'UTF8'
    LC_COLLATE  'en_US.UTF-8'
    LC_CTYPE    'en_US.UTF-8';
```

**After running this:**
In pgAdmin, right-click **al_noor_bank** in the left panel
and click **Query Tool**. All remaining steps must run
inside al_noor_bank — not on the default postgres database.

---

## Step 2 — Create the Schemas

```sql
-- ============================================================
-- WHY MULTIPLE SCHEMAS?
--
-- Think of schemas as separate filing cabinets in the same office.
-- All in the same building (database) — but each cabinet
-- has its own lock and its own set of authorised users.
--
-- retail     → customer-facing data (accounts, transactions)
-- finance    → Islamic finance products (Murabaha contracts)
-- compliance → regulatory data (KYC records, AML alerts)
-- analytics  → reporting views and dashboards
-- staging    → raw data landing zone for ETL pipelines
--
-- The compliance schema is the most sensitive — it contains
-- PDPL-restricted data. Schema separation means we can grant
-- access to retail data without exposing compliance data.
-- This is data protection by design.
-- ============================================================

CREATE SCHEMA retail;
CREATE SCHEMA finance;
CREATE SCHEMA compliance;
CREATE SCHEMA analytics;
CREATE SCHEMA staging;

-- Tell PostgreSQL which schemas to search first when
-- a table name is used without specifying the schema
SET search_path TO retail, finance, compliance;
```

**Expected result:** No error. Five schemas created.

---

## Step 3 — Create the Branch Table

```sql
-- ============================================================
-- BRANCH TABLE
-- Stores Al-Noor Bank's physical and digital branches.
--
-- is_digital separates physical branches from the digital
-- banking channel. SAMA tracks digital vs branch-originated
-- transactions separately in regulatory reporting.
--
-- CHAR(10) for branch_id — fixed length, always exactly
-- 10 characters. Use CHAR for codes that never vary in length.
-- Use VARCHAR for values that vary (names, addresses).
--
-- TIMESTAMPTZ — timezone-aware timestamp. Always use this
-- for event timestamps. Saudi Arabia is UTC+3.
-- ============================================================

CREATE TABLE retail.branch (
    branch_id   CHAR(10)     NOT NULL,
    branch_name VARCHAR(100) NOT NULL,
    city        VARCHAR(50)  NOT NULL,
    region      VARCHAR(50)  NOT NULL,
    is_digital  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_branch PRIMARY KEY (branch_id)
);
```

---

## Step 4 — Create the Customer Table

```sql
-- ============================================================
-- CUSTOMER TABLE
-- The most important and most protected table in the system.
-- Contains PDPL-sensitive personal data.
--
-- KEY DESIGN DECISIONS:
--
-- national_id: VARCHAR(15) not INTEGER
--   Saudi NIDs can have leading zeros. Storing as INTEGER
--   silently drops the leading zero. The record then cannot
--   be matched against source systems. Always use VARCHAR.
--
-- CHECK constraints on kyc_status and risk_rating
--   Only specific values are valid. The database enforces this.
--   Application code can have bugs. CHECK constraints cannot
--   be bypassed by any means.
--
-- is_deleted: BOOLEAN DEFAULT FALSE
--   Soft delete pattern. We never hard DELETE customer rows.
--   SAMA requires 10 years of data retention. A deleted row
--   cannot satisfy a SAMA audit request.
-- ============================================================

CREATE TABLE retail.customer (
    customer_id       CHAR(10)      NOT NULL,
    national_id       VARCHAR(15)   NOT NULL,  -- PDPL: Restricted
    full_name_ar      VARCHAR(200)  NOT NULL,  -- PDPL: Confidential
    full_name_en      VARCHAR(200)  NOT NULL,  -- PDPL: Confidential
    date_of_birth     DATE          NOT NULL,  -- PDPL: Restricted
    mobile_number     VARCHAR(15)   NOT NULL,  -- PDPL: Restricted
    customer_segment  VARCHAR(30)   NOT NULL,
    kyc_status        VARCHAR(20)   NOT NULL
        CHECK (kyc_status IN
            ('VERIFIED', 'EXPIRED', 'PENDING', 'REJECTED')),
    kyc_last_reviewed DATE          NOT NULL,
    risk_rating       CHAR(1)       NOT NULL
        CHECK (risk_rating IN ('H', 'M', 'L')),
    branch_id         CHAR(10)      NOT NULL,
    is_deleted        BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_customer    PRIMARY KEY (customer_id),
    CONSTRAINT uq_nid         UNIQUE (national_id),
    CONSTRAINT fk_cust_branch
        FOREIGN KEY (branch_id) REFERENCES retail.branch(branch_id)
);
```

**What to notice:**
- `UNIQUE (national_id)` — no two customers can share the same NID
- `FOREIGN KEY (branch_id)` — a customer cannot be assigned to
  a branch that does not exist. The database enforces this automatically.
- `H`, `M`, `L` for risk_rating — High, Medium, Low.
  These map directly to SAMA AML risk categories and determine
  KYC renewal frequency: 1 year, 2 years, 3 years respectively.

---

## Step 5 — Create the Account Table

```sql
-- ============================================================
-- ACCOUNT TABLE
-- One row per account. A customer can have many accounts.
--
-- THE MOST IMPORTANT CONSTRAINT: balance >= 0
-- Islamic accounts cannot go negative — no overdrafts allowed
-- under Sharia principles. This CHECK constraint enforces that
-- rule at the database layer. No application bug, no developer
-- running direct SQL, nothing can bypass it.
--
-- NUMERIC(18,2) for balance — NEVER use FLOAT for money.
-- FLOAT uses binary approximations that cause rounding errors.
-- 0.1 + 0.2 in FLOAT = 0.30000000000000004, not 0.30.
-- Across millions of transactions these errors compound and
-- fail SAMA reconciliation. NUMERIC stores exact decimals.
--
-- closed_date has no NOT NULL — it is NULL for open accounts
-- and only populated when the account is closed.
-- ============================================================

CREATE TABLE retail.account (
    account_id     CHAR(16)      NOT NULL,
    account_number VARCHAR(24)   NOT NULL,
    account_type   VARCHAR(20)   NOT NULL
        CHECK (account_type IN
            ('CURRENT', 'SAVINGS', 'TAWARRUQ', 'INVESTMENT')),
    balance        NUMERIC(18,2) NOT NULL DEFAULT 0.00
        CHECK (balance >= 0),
    currency       CHAR(3)       NOT NULL DEFAULT 'SAR',
    status         VARCHAR(15)   NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN
            ('ACTIVE', 'DORMANT', 'CLOSED', 'FROZEN')),
    opened_date    DATE          NOT NULL,
    branch_id      CHAR(10)      NOT NULL,
    is_deleted     BOOLEAN       NOT NULL DEFAULT FALSE,
    closed_date    DATE,
    CONSTRAINT pk_account        PRIMARY KEY (account_id),
    CONSTRAINT uq_account_number UNIQUE (account_number),
    CONSTRAINT fk_acct_branch
        FOREIGN KEY (branch_id) REFERENCES retail.branch(branch_id)
);
```

---

## Step 6 — Create the Customer-Account Bridge Table

```sql
-- ============================================================
-- CUSTOMER_ACCOUNT BRIDGE TABLE
-- Resolves the many-to-many relationship between customers
-- and accounts.
--
-- WHY IS THIS NEEDED?
-- A customer can have multiple accounts (current + savings).
-- An account can have multiple customers (joint account).
-- A simple foreign key on either side cannot express this.
-- The bridge table holds one row per customer-account link.
--
-- Example: Ahmed and Fatima share a savings account.
--   Row 1: Ahmed's customer_id + the shared account_id
--   Row 2: Fatima's customer_id + the same account_id
-- The relationship column tells us who is PRIMARY and
-- who is JOINT on that account.
--
-- The composite PRIMARY KEY (customer_id, account_id)
-- prevents the same customer-account pair from appearing twice.
-- ============================================================

CREATE TABLE retail.customer_account (
    customer_id  CHAR(10)    NOT NULL,
    account_id   CHAR(16)    NOT NULL,
    relationship VARCHAR(30) NOT NULL
        CHECK (relationship IN
            ('PRIMARY', 'JOINT', 'AUTHORISED_SIGNATORY', 'GUARDIAN')),
    linked_at    DATE        NOT NULL DEFAULT CURRENT_DATE,
    is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_ca PRIMARY KEY (customer_id, account_id),
    CONSTRAINT fk_ca_cust
        FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id),
    CONSTRAINT fk_ca_acct
        FOREIGN KEY (account_id)
        REFERENCES retail.account(account_id)
);
```

---

## Step 7 — Create the Transaction Table (Partitioned)

```sql
-- ============================================================
-- TRANSACTION TABLE — PARTITIONED BY YEAR
--
-- WHY PARTITIONED?
-- SAMA mandates 10-year transaction data retention.
-- A Saudi retail bank with 500,000 transactions per day
-- accumulates hundreds of millions of rows per year.
-- Over 10 years: potentially billions of rows.
--
-- Without partitioning: a query for "last month's transactions"
-- is planned against 10 years of data — very slow.
--
-- With partitioning: PostgreSQL reads only the relevant
-- year partition. The other 9 years are completely ignored.
-- This is called partition pruning.
--
-- MRB_PMT  = Murabaha Payment (Islamic finance instalment)
-- SARIE_IN = Inbound SARIE transfer (Saudi interbank network)
-- SADAD_PMT = SADAD bill payment (utility, government fees)
--
-- direction: D = Debit (money leaving), C = Credit (arriving)
-- balance_after: running balance snapshot — avoids recalculating
-- from transaction history on every balance enquiry
-- ============================================================

CREATE TABLE retail.transaction (
    txn_id        BIGSERIAL     NOT NULL,
    account_id    CHAR(16)      NOT NULL,
    txn_date      DATE          NOT NULL,
    txn_type      VARCHAR(30)   NOT NULL
        CHECK (txn_type IN (
            'DEBIT',     'CREDIT',    'MRB_PMT',   'MRB_DISB',
            'SADAD_PMT', 'SARIE_OUT', 'SARIE_IN',
            'SWIFT_OUT', 'SWIFT_IN',  'FEE', 'PROFIT', 'REVERSAL'
        )),
    amount_sar    NUMERIC(18,2) NOT NULL CHECK (amount_sar > 0),
    direction     CHAR(1)       NOT NULL CHECK (direction IN ('D','C')),
    balance_after NUMERIC(18,2) NOT NULL,
    channel       VARCHAR(20)   NOT NULL
        CHECK (channel IN
            ('BRANCH','ATM','MOBILE','INTERNET','API','BATCH')),
    reference_no  VARCHAR(50),
    narrative     VARCHAR(200),
    status        VARCHAR(15)   NOT NULL DEFAULT 'POSTED'
        CHECK (status IN ('POSTED','PENDING','REVERSED','FAILED')),
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_transaction PRIMARY KEY (txn_id, txn_date),
    CONSTRAINT fk_txn_account
        FOREIGN KEY (account_id) REFERENCES retail.account(account_id)
) PARTITION BY RANGE (txn_date);

-- One partition per year
-- PostgreSQL automatically routes each INSERT to the right partition
CREATE TABLE retail.transaction_2024
    PARTITION OF retail.transaction
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE retail.transaction_2025
    PARTITION OF retail.transaction
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

-- Indexes defined once on the parent — apply to all partitions
CREATE INDEX idx_txn_account_date
    ON retail.transaction (account_id, txn_date DESC);

CREATE INDEX idx_txn_type_date
    ON retail.transaction (txn_type, txn_date DESC);

-- Partial index: only non-POSTED transactions
-- 99.9% of rows are POSTED — AML team only needs PENDING/FAILED
-- This index is tiny and extremely fast
CREATE INDEX idx_txn_non_posted
    ON retail.transaction (status, txn_date DESC)
    WHERE status != 'POSTED';
```

---

## Step 8 — Create the Compliance Tables

```sql
-- ============================================================
-- KYC_RECORD TABLE
-- Records each Know-Your-Customer review for each customer.
-- One customer has MANY KYC records over their lifetime.
-- We never overwrite the old review — each is a new row.
-- This preserves the full history for SAMA audits.
--
-- SAMA renewal schedule:
--   H (High risk)   → review every 1 year
--   M (Medium risk) → review every 2 years
--   L (Low risk)    → review every 3 years
-- ============================================================

CREATE TABLE compliance.kyc_record (
    kyc_id        SERIAL      NOT NULL,
    customer_id   CHAR(10)    NOT NULL,
    reviewed_date DATE        NOT NULL,
    outcome       VARCHAR(20) NOT NULL
        CHECK (outcome IN ('PASS', 'FAIL', 'PENDING', 'ESCALATED')),
    expiry_date   DATE        NOT NULL,
    reviewer_id   VARCHAR(50) NOT NULL,
    CONSTRAINT pk_kyc PRIMARY KEY (kyc_id),
    CONSTRAINT fk_kyc_cust
        FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id)
);


-- ============================================================
-- AML_ALERT TABLE
-- Records Anti-Money Laundering alerts raised against accounts.
--
-- STRUCTURING is the most common alert type in Saudi banking.
-- It means splitting a large transaction into smaller ones
-- to stay below the SAR 60,000 SAMA mandatory reporting threshold.
--
-- risk_score: 0 to 100 — enforced by CHECK constraint.
-- A score of 78.5 is considered high risk and requires
-- officer investigation before the account can proceed normally.
-- ============================================================

CREATE TABLE compliance.aml_alert (
    alert_id   SERIAL        NOT NULL,
    account_id CHAR(16)      NOT NULL,
    alert_date TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    alert_type VARCHAR(30)   NOT NULL
        CHECK (alert_type IN (
            'STRUCTURING', 'UNUSUAL_PATTERN',
            'WATCHLIST_MATCH', 'LARGE_CASH'
        )),
    risk_score NUMERIC(5,2)  NOT NULL
        CHECK (risk_score BETWEEN 0 AND 100),
    status     VARCHAR(15)   NOT NULL DEFAULT 'OPEN'
        CHECK (status IN
            ('OPEN', 'INVESTIGATING', 'CLOSED', 'ESCALATED')),
    CONSTRAINT pk_aml_alert PRIMARY KEY (alert_id),
    CONSTRAINT fk_alert_acct
        FOREIGN KEY (account_id)
        REFERENCES retail.account(account_id)
);
```

---

## Step 9 — Create the Finance Tables

```sql
-- ============================================================
-- MURABAHA_CONTRACT TABLE
-- The most common Islamic financing product in Saudi banking.
--
-- HOW MURABAHA WORKS:
-- The bank buys an asset (e.g. a car for SAR 75,000)
-- and sells it to the customer at a marked-up price
-- (SAR 90,000 = SAR 75,000 cost + SAR 15,000 profit).
-- The customer pays in monthly instalments.
-- The profit is fixed at contract inception — it cannot
-- change, compound, or increase. This is what makes it
-- Sharia-compliant vs a conventional interest-bearing loan.
--
-- KEY CONSTRAINT: chk_total_price
-- total_sale_price MUST equal asset_cost + profit_amount.
-- This enforces the Islamic finance principle at the database
-- level. Any insert that does not satisfy this equation fails.
--
-- ssb_approval_ref: every Islamic product must have a
-- Sharia Supervisory Board reference. Without it, the
-- product is not Sharia-compliant and the contract is invalid.
-- ============================================================

CREATE TABLE finance.murabaha_contract (
    contract_id       CHAR(15)      NOT NULL,
    customer_id       CHAR(10)      NOT NULL,
    account_id        CHAR(16)      NOT NULL,
    asset_cost_sar    NUMERIC(18,2) NOT NULL,
    profit_amount_sar NUMERIC(18,2) NOT NULL,
    total_sale_price  NUMERIC(18,2) NOT NULL,
    ssb_approval_ref  VARCHAR(50)   NOT NULL,
    disbursement_date DATE          NOT NULL,
    maturity_date     DATE          NOT NULL,
    status            VARCHAR(15)   NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN
            ('ACTIVE', 'SETTLED', 'DEFAULTED', 'SETTLED_EARLY')),
    CONSTRAINT pk_murabaha PRIMARY KEY (contract_id),
    CONSTRAINT fk_mrb_cust
        FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id),
    CONSTRAINT fk_mrb_acct
        FOREIGN KEY (account_id)
        REFERENCES retail.account(account_id),
    CONSTRAINT chk_total_price
        CHECK (total_sale_price = asset_cost_sar + profit_amount_sar)
);


-- ============================================================
-- MURABAHA_SCHEDULE TABLE
-- One row per monthly instalment.
-- A 24-month contract = 24 rows in this table.
--
-- Each instalment is split between:
--   principal_portion → paying back the asset cost (SAR 75,000)
--   profit_portion    → the bank's profit (SAR 15,000)
--
-- KEY CONSTRAINT: chk_instalment_sum
-- instalment_sar = principal_portion + profit_portion
-- The two portions must always add up to the total instalment.
--
-- paid_amount and paid_date are NULL until payment is received.
-- When paid, they are populated and status changes to PAID.
-- ============================================================

CREATE TABLE finance.murabaha_schedule (
    schedule_id       SERIAL        NOT NULL,
    contract_id       CHAR(15)      NOT NULL,
    instalment_no     INTEGER       NOT NULL,
    due_date          DATE          NOT NULL,
    instalment_sar    NUMERIC(18,2) NOT NULL,
    principal_portion NUMERIC(18,2) NOT NULL,
    profit_portion    NUMERIC(18,2) NOT NULL,
    paid_amount       NUMERIC(18,2),
    paid_date         DATE,
    status            VARCHAR(15)   NOT NULL DEFAULT 'PENDING'
        CHECK (status IN
            ('PENDING', 'PAID', 'OVERDUE', 'SETTLED_EARLY')),
    CONSTRAINT pk_schedule PRIMARY KEY (schedule_id),
    CONSTRAINT fk_ms_contract
        FOREIGN KEY (contract_id)
        REFERENCES finance.murabaha_contract(contract_id),
    CONSTRAINT chk_instalment_sum
        CHECK (instalment_sar = principal_portion + profit_portion)
);
```

---

## Step 10 — Verify All Tables Were Created

```sql
-- ============================================================
-- Run this before inserting any data.
-- Confirm all 9 tables exist across the three schemas.
-- ============================================================

SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_schema IN ('retail', 'finance', 'compliance')
  AND table_type = 'BASE TABLE'
ORDER BY table_schema, table_name;
```

**Expected output:**

```
 table_schema |      table_name
--------------+------------------
 compliance   | aml_alert
 compliance   | kyc_record
 finance      | murabaha_contract
 finance      | murabaha_schedule
 retail       | account
 retail       | branch
 retail       | customer
 retail       | customer_account
 retail       | transaction
```

If any table is missing, re-run that CREATE TABLE block before continuing.

---

## Step 11 — Insert Branch Data

```sql
-- ============================================================
-- Four branches: three physical, one digital.
-- BR004 (Digital Branch) is where mobile and API transactions
-- are associated when no physical branch is involved.
-- ============================================================

INSERT INTO retail.branch
    (branch_id, branch_name, city, region, is_digital)
VALUES
    ('BR001', 'Riyadh Main Branch', 'Riyadh', 'Central Region', FALSE),
    ('BR002', 'Al Olaya Branch',    'Riyadh', 'Central Region', FALSE),
    ('BR003', 'Jeddah Corniche',    'Jeddah', 'Western Region', FALSE),
    ('BR004', 'Digital Branch',     'Riyadh', 'Central Region', TRUE);

-- Verify
SELECT branch_id, branch_name, city, is_digital
FROM retail.branch;
```

**Expected output:** 4 rows.

---

## Step 12 — Insert Customer Data

```sql
-- ============================================================
-- Four customers with realistic Saudi names and data.
--
-- Notice the Arabic names in full_name_ar — this is exactly
-- why we created the database with UTF8 encoding.
-- Without UTF8, these names would fail or become garbage.
--
-- Khalid Al-Qahtani (C000000003) is deliberately set up with:
--   kyc_status = 'EXPIRED'      his KYC has lapsed
--   risk_rating = 'H'           he is high risk
--   kyc_last_reviewed = 2022    over 2 years ago
-- He will appear in the KYC overdue report in Lab 3B.
-- ============================================================

INSERT INTO retail.customer
    (customer_id, national_id, full_name_ar, full_name_en,
     date_of_birth, mobile_number, customer_segment,
     kyc_status, kyc_last_reviewed, risk_rating, branch_id)
VALUES
    ('C000000001', '1234567890123',
     'أحمد العمري',     'Ahmed Al-Omari',
     '1985-03-15', '+966501234567', 'PREMIUM',
     'VERIFIED', '2024-01-10', 'L', 'BR001'),

    ('C000000002', '9876543210987',
     'فاطمة الزهراني',  'Fatima Al-Zahrani',
     '1990-07-22', '+966509876543', 'STANDARD',
     'VERIFIED', '2023-05-20', 'M', 'BR002'),

    ('C000000003', '5555555555555',
     'خالد القحطاني',   'Khalid Al-Qahtani',
     '1978-11-01', '+966505555555', 'PREMIUM',
     'EXPIRED',  '2022-11-15', 'H', 'BR001'),

    ('C000000004', '1111111111111',
     'نورة السعيد',     'Noura Al-Saeed',
     '1995-06-10', '+966501111111', 'STANDARD',
     'VERIFIED', '2024-03-01', 'L', 'BR003');

-- Verify
SELECT customer_id, full_name_en, customer_segment,
       kyc_status, risk_rating
FROM retail.customer
ORDER BY customer_id;
```

**Expected output:** 4 rows.

---

## Step 13 — Insert Account Data

```sql
-- ============================================================
-- Four accounts — one per customer as their primary account.
-- ACC0000000000001 belongs to Ahmed Al-Omari.
-- All transactions in the next step belong to this account.
-- ============================================================

INSERT INTO retail.account
    (account_id, account_number, account_type,
     balance, currency, status, opened_date, branch_id)
VALUES
    ('ACC0000000000001', 'SA01234567890123456789012',
     'CURRENT',  54550.00, 'SAR', 'ACTIVE', '2025-01-01', 'BR001'),

    ('ACC0000000000002', 'SA09876543210987654321098',
     'SAVINGS',  22000.00, 'SAR', 'ACTIVE', '2024-06-15', 'BR002'),

    ('ACC0000000000003', 'SA05555555555555555555555',
     'CURRENT',   8750.00, 'SAR', 'ACTIVE', '2020-03-10', 'BR001'),

    ('ACC0000000000004', 'SA01111111111111111111111',
     'SAVINGS',  45000.00, 'SAR', 'ACTIVE', '2024-01-20', 'BR003');

-- Verify
SELECT account_id, account_type, balance, status
FROM retail.account;
```

**Expected output:** 4 rows.

---

## Step 14 — Link Customers to Accounts

```sql
-- ============================================================
-- Five relationships — four PRIMARY, one JOINT.
-- Ahmed (C000000001) has two rows:
--   PRIMARY on his own account (ACC0000000000001)
--   JOINT on Fatima's savings account (ACC0000000000002)
-- This is a joint savings account — both are linked through
-- the bridge table with different relationship types.
-- ============================================================

INSERT INTO retail.customer_account
    (customer_id, account_id, relationship, linked_at, is_active)
VALUES
    ('C000000001', 'ACC0000000000001', 'PRIMARY', '2025-01-01', TRUE),
    ('C000000002', 'ACC0000000000002', 'PRIMARY', '2024-06-15', TRUE),
    ('C000000003', 'ACC0000000000003', 'PRIMARY', '2020-03-10', TRUE),
    ('C000000004', 'ACC0000000000004', 'PRIMARY', '2024-01-20', TRUE),
    ('C000000001', 'ACC0000000000002', 'JOINT',   '2024-06-15', TRUE);

-- Verify
SELECT ca.customer_id, c.full_name_en,
       ca.account_id, ca.relationship
FROM retail.customer_account ca
JOIN retail.customer c
    ON ca.customer_id = c.customer_id
ORDER BY ca.account_id, ca.relationship;
```

**Expected output:** 5 rows. Ahmed appears twice.

---

## Step 15 — Insert Transactions

```sql
-- ============================================================
-- SIX TRANSACTIONS FOR AHMED AL-OMARI
-- These tell a realistic banking story:
--
-- Jan 05: SAR 50,000 arrives via SARIE (his opening deposit)
-- Jan 10: SAR  2,500 withdrawn from ATM at Riyadh Park Mall
-- Feb 01: SAR  3,750 Murabaha instalment paid via mobile app
-- Feb 15: SAR    450 SADAD bill payment to STC telecom
-- Mar 01: SAR  3,750 second Murabaha instalment via mobile
-- Mar 10: SAR 15,000 cash deposit at Riyadh Main Branch
--
-- balance_after tracks the running balance after each transaction.
-- This snapshot means we can see Ahmed's balance at any moment
-- without recalculating from the entire transaction history.
-- Critical for the <100ms balance query performance requirement.
-- ============================================================

INSERT INTO retail.transaction
    (account_id, txn_date, txn_type, amount_sar,
     direction, balance_after, channel, narrative, status)
VALUES
    ('ACC0000000000001', '2025-01-05', 'SARIE_IN',
     50000.00, 'C', 50000.00, 'API',
     'Opening deposit via SARIE', 'POSTED'),

    ('ACC0000000000001', '2025-01-10', 'DEBIT',
      2500.00, 'D', 47500.00, 'ATM',
     'ATM withdrawal - Riyadh Park Mall', 'POSTED'),

    ('ACC0000000000001', '2025-02-01', 'MRB_PMT',
      3750.00, 'D', 43750.00, 'MOBILE',
     'Murabaha instalment 1 of 24', 'POSTED'),

    ('ACC0000000000001', '2025-02-15', 'SADAD_PMT',
       450.00, 'D', 43300.00, 'MOBILE',
     'STC bill payment via SADAD', 'POSTED'),

    ('ACC0000000000001', '2025-03-01', 'MRB_PMT',
      3750.00, 'D', 39550.00, 'MOBILE',
     'Murabaha instalment 2 of 24', 'POSTED'),

    ('ACC0000000000001', '2025-03-10', 'CREDIT',
     15000.00, 'C', 54550.00, 'BRANCH',
     'Cash deposit at Riyadh Main Branch', 'POSTED');
```

```sql
-- Check which partition each row landed in
-- All 2025 transactions should go to transaction_2025 automatically
SELECT tableoid::regclass AS partition_name,
       COUNT(*)           AS row_count
FROM retail.transaction
GROUP BY tableoid::regclass;
```

**Expected output:**

```
     partition_name      | row_count
-------------------------+-----------
 retail.transaction_2025 |         6
```

All six rows went to the 2025 partition automatically.
PostgreSQL routed them based on the txn_date value — you did nothing extra.

---

## Step 16 — Insert Murabaha Contract and Schedule

```sql
-- ============================================================
-- MURABAHA CONTRACT FOR AHMED
--
-- Asset cost:       SAR 75,000  (what the bank paid for the asset)
-- Profit amount:    SAR 15,000  (the bank's fixed profit)
-- Total sale price: SAR 90,000  (what Ahmed owes in total)
--
-- The CHECK constraint chk_total_price enforces:
-- 75,000 + 15,000 = 90,000 exactly
-- If the numbers do not add up, the INSERT is rejected.
-- ============================================================

INSERT INTO finance.murabaha_contract
    (contract_id, customer_id, account_id,
     asset_cost_sar, profit_amount_sar, total_sale_price,
     ssb_approval_ref, disbursement_date, maturity_date, status)
VALUES
    ('MRB0000000000001', 'C000000001', 'ACC0000000000001',
     75000.00, 15000.00, 90000.00,
     'SSB-2025-001', '2025-01-15', '2027-01-15', 'ACTIVE');
```

```sql
-- ============================================================
-- THREE INSTALMENTS
-- Instalment 1: PAID — matches the Feb 01 MRB_PMT transaction
-- Instalment 2: PAID — matches the Mar 01 MRB_PMT transaction
-- Instalment 3: PENDING — due Apr 01, not yet paid
--
-- Each instalment: SAR 3,750
-- Principal portion: SAR 3,125  (repaying the SAR 75,000 asset)
-- Profit portion:   SAR   625  (the bank's profit share)
-- CHECK: 3,125 + 625 = 3,750 ✓
-- ============================================================

INSERT INTO finance.murabaha_schedule
    (contract_id, instalment_no, due_date,
     instalment_sar, principal_portion, profit_portion,
     paid_amount, paid_date, status)
VALUES
    ('MRB0000000000001', 1, '2025-02-01',
     3750.00, 3125.00, 625.00,
     3750.00, '2025-02-01', 'PAID'),

    ('MRB0000000000001', 2, '2025-03-01',
     3750.00, 3125.00, 625.00,
     3750.00, '2025-03-01', 'PAID'),

    ('MRB0000000000001', 3, '2025-04-01',
     3750.00, 3125.00, 625.00,
     NULL, NULL, 'PENDING');

-- Verify
SELECT instalment_no, due_date, instalment_sar,
       paid_date, status
FROM finance.murabaha_schedule
WHERE contract_id = 'MRB0000000000001'
ORDER BY instalment_no;
```

**Expected output:** 3 rows. Instalments 1 and 2 are PAID.
Instalment 3 shows NULL for paid_date and status = PENDING.

---

## Step 17 — Insert Compliance Data

```sql
-- ============================================================
-- KYC RECORD FOR KHALID AL-QAHTANI
-- His KYC was reviewed on 2022-11-15.
-- It expired on 2023-11-15 (one year later — he is High risk).
-- Today (2025) he is over 2 years overdue for renewal.
-- This will surface in the KYC overdue report in Lab 3B.
-- ============================================================

INSERT INTO compliance.kyc_record
    (customer_id, reviewed_date, outcome, expiry_date, reviewer_id)
VALUES
    ('C000000003', '2022-11-15', 'PASS',
     '2023-11-15', 'KYC_OFFICER_001');


-- ============================================================
-- AML ALERT FOR KHALID'S ACCOUNT
-- Alert type: STRUCTURING
-- Risk score: 78.5 out of 100 — high risk, requires investigation
-- Status: OPEN — not yet reviewed by the AML team
--
-- Structuring = deliberately splitting transactions to stay
-- below the SAR 60,000 SAMA mandatory reporting threshold.
-- We will detect this pattern with SQL in Lab 3B.
-- ============================================================

INSERT INTO compliance.aml_alert
    (account_id, alert_date, alert_type, risk_score, status)
VALUES
    ('ACC0000000000003', CURRENT_TIMESTAMP,
     'STRUCTURING', 78.5, 'OPEN');
```

---

## Step 18 — Final Verification

```sql
-- ============================================================
-- COMPLETE ROW COUNT CHECK
-- Run this to confirm everything loaded correctly.
-- All numbers must match before moving to Lab 3B.
-- ============================================================

SELECT 'retail.branch'             AS table_name, COUNT(*) AS rows FROM retail.branch
UNION ALL
SELECT 'retail.customer',          COUNT(*) FROM retail.customer
UNION ALL
SELECT 'retail.account',           COUNT(*) FROM retail.account
UNION ALL
SELECT 'retail.customer_account',  COUNT(*) FROM retail.customer_account
UNION ALL
SELECT 'retail.transaction',       COUNT(*) FROM retail.transaction
UNION ALL
SELECT 'finance.murabaha_contract',COUNT(*) FROM finance.murabaha_contract
UNION ALL
SELECT 'finance.murabaha_schedule',COUNT(*) FROM finance.murabaha_schedule
UNION ALL
SELECT 'compliance.kyc_record',    COUNT(*) FROM compliance.kyc_record
UNION ALL
SELECT 'compliance.aml_alert',     COUNT(*) FROM compliance.aml_alert;
```

**Expected output:**

```
         table_name          | rows
-----------------------------+------
 retail.branch               |    4
 retail.customer             |    4
 retail.account              |    4
 retail.customer_account     |    5
 retail.transaction          |    6
 finance.murabaha_contract   |    1
 finance.murabaha_schedule   |    3
 compliance.kyc_record       |    1
 compliance.aml_alert        |    1
```

---

## Step 19 — Your First Reporting Query

```sql
-- ============================================================
-- AHMED AL-OMARI'S ACCOUNT STATEMENT
-- This is the query that runs when a customer opens their
-- transaction history in the mobile banking app.
--
-- INTERVAL '90 days' — only show the last 3 months.
-- ORDER BY txn_date DESC — newest first.
-- ============================================================

SELECT
    txn_date,
    txn_type,
    amount_sar,
    direction,
    balance_after,
    channel,
    narrative
FROM retail.transaction
WHERE account_id = 'ACC0000000000001'
  AND txn_date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY txn_date DESC;
```

**Expected output:** 6 transactions, newest first.
The March 10 cash deposit appears at the top.

---

## Step 20 — Branch Summary for SAMA

```sql
-- ============================================================
-- BRANCH TRANSACTION SUMMARY
-- This query feeds the SAMA daily liquidity report.
-- It joins 5 tables to get from a transaction row all the
-- way to the branch the customer belongs to.
--
-- JOIN CHAIN:
-- transaction → account → customer_account → customer → branch
--
-- ca.relationship = 'PRIMARY' prevents double-counting.
-- Joint account holders (like Ahmed on ACC0000000000002)
-- are not counted again — only the PRIMARY holder's branch
-- is attributed the transaction.
-- ============================================================

SELECT
    b.branch_name,
    b.region,
    COUNT(t.txn_id)    AS total_transactions,
    SUM(t.amount_sar)  AS total_volume_sar,
    AVG(t.amount_sar)  AS avg_transaction_sar
FROM retail.transaction t
JOIN retail.account a
    ON t.account_id = a.account_id
JOIN retail.customer_account ca
    ON a.account_id = ca.account_id
    AND ca.relationship = 'PRIMARY'
JOIN retail.customer c
    ON ca.customer_id = c.customer_id
JOIN retail.branch b
    ON c.branch_id = b.branch_id
WHERE t.status = 'POSTED'
GROUP BY b.branch_name, b.region
ORDER BY total_volume_sar DESC;
```

**Expected output:** Riyadh Main Branch with the highest volume.
All 6 of Ahmed's transactions are linked to BR001.

---

> **Lab 3A is complete.**
>
> You have built a production-quality Saudi banking database
> from scratch — with correct encoding, domain-separated schemas,
> partitioned transaction tables, referential integrity enforced
> at every level, and realistic data across all nine tables.
>
> Keep this database running. Lab 3B and Lab 3C build directly on it.

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*