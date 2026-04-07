-- 1. BRANCH (no FKs — create first)
CREATE TABLE retail.branch (
  branch_id   CHAR(10)      NOT NULL,
  branch_name VARCHAR(100)  NOT NULL,
  city        VARCHAR(50)   NOT NULL,
  region      VARCHAR(50)   NOT NULL,
  is_digital  BOOLEAN       NOT NULL DEFAULT FALSE,
  created_at  TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT pk_branch PRIMARY KEY (branch_id)
);

-- 2. CUSTOMER (FK to BRANCH)
CREATE TABLE retail.customer (
  customer_id      CHAR(10)       NOT NULL,
  national_id      VARCHAR(15)    NOT NULL, -- PDPL Art.23 Restricted
  full_name_ar     VARCHAR(200)   NOT NULL, -- PDPL Confidential
  full_name_en     VARCHAR(200)   NOT NULL, -- PDPL Confidential
  date_of_birth    DATE           NOT NULL, -- PDPL Art.23 Restricted
  mobile_number    VARCHAR(15)    NOT NULL, -- PDPL Art.23 Restricted
  customer_segment VARCHAR(30)    NOT NULL,
  kyc_status       VARCHAR(20)    NOT NULL
    CHECK (kyc_status IN ('ACTIVE','EXPIRED','PENDING','SUSPENDED')),
  risk_rating      CHAR(1)        NOT NULL
    CHECK (risk_rating IN ('H','M','L')),
  branch_id        CHAR(10)       NOT NULL,
  created_at       TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT pk_customer PRIMARY KEY (customer_id),
  CONSTRAINT uq_customer_nid UNIQUE (national_id),
  CONSTRAINT fk_customer_branch
    FOREIGN KEY (branch_id) REFERENCES retail.branch(branch_id)
);

-- 3. ACCOUNT (FK to BRANCH)
CREATE TABLE retail.account (
  account_id     CHAR(16)       NOT NULL,
  account_number VARCHAR(20)    NOT NULL,
  account_type   VARCHAR(20)    NOT NULL
    CHECK (account_type IN ('CURRENT','SAVINGS','TAWARRUQ','INVESTMENT')),
  balance        NUMERIC(18,2)  NOT NULL DEFAULT 0.00
    CHECK (balance >= 0),
  currency       CHAR(3)        NOT NULL DEFAULT 'SAR',
  status         VARCHAR(15)    NOT NULL DEFAULT 'ACTIVE'
    CHECK (status IN ('ACTIVE','DORMANT','CLOSED','FROZEN')),
  opened_date    DATE           NOT NULL,
  branch_id      CHAR(10)       NOT NULL,
  CONSTRAINT pk_account PRIMARY KEY (account_id),
  CONSTRAINT uq_account_number UNIQUE (account_number),
  CONSTRAINT fk_account_branch
    FOREIGN KEY (branch_id) REFERENCES retail.branch(branch_id)
);

-- 4. CUSTOMER_ACCOUNT bridge (FKs to CUSTOMER and ACCOUNT)
CREATE TABLE retail.customer_account (
  customer_id  CHAR(10)     NOT NULL,
  account_id   CHAR(16)     NOT NULL,
  relationship VARCHAR(30)  NOT NULL
    CHECK (relationship IN ('PRIMARY','JOINT','AUTHORISED_SIGNATORY','GUARDIAN')),
  linked_at    DATE         NOT NULL DEFAULT CURRENT_DATE,
  is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
  CONSTRAINT pk_customer_account PRIMARY KEY (customer_id, account_id),
  CONSTRAINT fk_ca_customer
    FOREIGN KEY (customer_id) REFERENCES retail.customer(customer_id),
  CONSTRAINT fk_ca_account
    FOREIGN KEY (account_id) REFERENCES retail.account(account_id)
);

-- 5. TRANSACTION (FK to ACCOUNT)
CREATE TABLE retail.transaction (
  txn_id        CHAR(18)       NOT NULL,
  account_id    CHAR(16)       NOT NULL,
  txn_date      TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  txn_type      VARCHAR(30)    NOT NULL
    CHECK (txn_type IN (
      'DEBIT','CREDIT','MRB_PMT','MRB_DISB',
      'SADAD_PMT','SARIE_OUT','SARIE_IN',
      'SWIFT_OUT','SWIFT_IN','FEE','PROFIT','REVERSAL')),
  amount_sar    NUMERIC(18,2)  NOT NULL CHECK (amount_sar > 0),
  direction     CHAR(1)        NOT NULL CHECK (direction IN ('D','C')),
  balance_after NUMERIC(18,2)  NOT NULL,
  channel       VARCHAR(20)    NOT NULL
    CHECK (channel IN ('BRANCH','ATM','MOBILE','INTERNET','API','BATCH')),
  status        VARCHAR(15)    NOT NULL DEFAULT 'POSTED'
    CHECK (status IN ('POSTED','PENDING','REVERSED','FAILED')),
  CONSTRAINT pk_transaction PRIMARY KEY (txn_id),
  CONSTRAINT fk_txn_account
    FOREIGN KEY (account_id) REFERENCES retail.account(account_id)
);
CREATE INDEX idx_txn_account_date ON retail.transaction (account_id, txn_date DESC);
CREATE INDEX idx_txn_type_date ON retail.transaction (txn_type, txn_date DESC);

-- 6. MURABAHA_CONTRACT (FK to CUSTOMER)
CREATE TABLE retail.murabaha_contract (
  contract_id       CHAR(15)       NOT NULL,
  customer_id       CHAR(10)       NOT NULL,
  asset_cost_sar    NUMERIC(18,2)  NOT NULL, -- PDPL Restricted
  profit_amount_sar NUMERIC(18,2)  NOT NULL, -- PDPL Restricted
  total_sale_price  NUMERIC(18,2)  NOT NULL, -- PDPL Restricted
  ssb_approval_ref  VARCHAR(50)    NOT NULL,
  disbursement_date DATE           NOT NULL,
  maturity_date     DATE           NOT NULL,
  status            VARCHAR(15)    NOT NULL DEFAULT 'ACTIVE'
    CHECK (status IN ('ACTIVE','COMPLETED','DEFAULTED','SETTLED_EARLY')),
  CONSTRAINT pk_murabaha PRIMARY KEY (contract_id),
  CONSTRAINT fk_mrb_customer
    FOREIGN KEY (customer_id) REFERENCES retail.customer(customer_id),
  CONSTRAINT chk_total_price
    CHECK (total_sale_price = asset_cost_sar + profit_amount_sar)
);

-- 7. MURABAHA_SCHEDULE (FK to MURABAHA_CONTRACT)
CREATE TABLE retail.murabaha_schedule (
  schedule_id      SERIAL         NOT NULL,
  contract_id      CHAR(15)       NOT NULL,
  instalment_no    INTEGER        NOT NULL,
  due_date         DATE           NOT NULL,
  instalment_sar   NUMERIC(18,2)  NOT NULL,
  principal_portion NUMERIC(18,2) NOT NULL,
  profit_portion   NUMERIC(18,2)  NOT NULL,
  payment_date     DATE,          -- NULL = not yet paid
  status           VARCHAR(15)    NOT NULL DEFAULT 'PENDING'
    CHECK (status IN ('PENDING','PAID','OVERDUE','SETTLED_EARLY')),
  CONSTRAINT pk_murabaha_schedule PRIMARY KEY (schedule_id),
  CONSTRAINT fk_ms_contract
    FOREIGN KEY (contract_id) REFERENCES retail.murabaha_contract(contract_id),
  CONSTRAINT chk_instalment_sum
    CHECK (instalment_sar = principal_portion + profit_portion)
);

-- 8. KYC_RECORD (FK to CUSTOMER)
CREATE TABLE retail.kyc_record (
  kyc_id        SERIAL       NOT NULL,
  customer_id   CHAR(10)     NOT NULL,
  reviewed_date DATE         NOT NULL,
  outcome       VARCHAR(20)  NOT NULL
    CHECK (outcome IN ('PASS','FAIL','PENDING','ESCALATED')),
  expiry_date   DATE         NOT NULL,
  reviewer_id   VARCHAR(50)  NOT NULL,
  CONSTRAINT pk_kyc_record PRIMARY KEY (kyc_id),
  CONSTRAINT fk_kyc_customer
    FOREIGN KEY (customer_id) REFERENCES retail.customer(customer_id)
);

-- 9. AML_ALERT (FK to ACCOUNT)
CREATE TABLE retail.aml_alert (
  alert_id   SERIAL         NOT NULL,
  account_id CHAR(16)       NOT NULL,
  alert_date TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  alert_type VARCHAR(30)    NOT NULL
    CHECK (alert_type IN ('STRUCTURING','UNUSUAL_PATTERN','WATCHLIST_MATCH','LARGE_CASH')),
  risk_score NUMERIC(5,2)   NOT NULL
    CHECK (risk_score BETWEEN 0 AND 100),
  status     VARCHAR(15)    NOT NULL DEFAULT 'OPEN'
    CHECK (status IN ('OPEN','INVESTIGATING','CLOSED','ESCALATED')),
  CONSTRAINT pk_aml_alert PRIMARY KEY (alert_id),
  CONSTRAINT fk_alert_account
    FOREIGN KEY (account_id) REFERENCES retail.account(account_id)
);