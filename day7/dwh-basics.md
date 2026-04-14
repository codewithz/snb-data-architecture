# Data Warehousing & Snowflake — Architecture Reference
## From DWH Fundamentals to Production Snowflake

> **Scope.** This document covers two things in sequence: (1) what a data warehouse is and how it is designed, and (2) how Snowflake implements those concepts — and in several cases, dramatically simplifies them. Al-Noor Bank is used as the running example throughout. By the end you should be able to reason about schema design decisions, understand why Snowflake makes specific architectural choices, and operate a Snowflake environment with confidence.

---

## Part 1 — Data Warehouse Fundamentals

### 1.1 What a Data Warehouse Is (and Is Not)

A data warehouse is a system optimised for analytical queries across large volumes of historical data. It is explicitly not a system for recording live transactions — that is the job of the Core Banking System (CBS) or any other operational database.

The distinction matters because the two workloads have opposing requirements:

| | Operational DB (CBS) | Data Warehouse |
|---|---|---|
| Primary use | Record individual transactions | Answer business questions across millions of rows |
| Query pattern | Point lookups: "fetch account ACC-123" | Aggregations: "total credit exposure by region, Q1 2024" |
| Write pattern | Continuous, high-frequency inserts/updates | Batch loads, typically nightly |
| Row count returned | 1–100 rows | 10,000–1,000,000,000 rows |
| Schema optimised for | Write speed, data integrity | Read speed, query flexibility |
| Indexes | Many, fine-grained | Few or none (columnar storage replaces them) |
| History retained | Current state only (usually) | Full history — every change, forever |

A bank cannot run SAMA regulatory reports against its CBS. The report would lock tables, compete with live transaction processing, and still be slow. The data warehouse exists specifically to absorb that analytical load without touching the operational system.

### 1.2 The Four Characteristics (Inmon's Definition)

Bill Inmon defined a data warehouse with four properties. These are worth understanding not as trivia but as design constraints:

**Subject-oriented** — organised around business subjects (customers, transactions, products), not around the applications that generate data. The CBS organises data around its own processing logic. The DWH reorganises the same data around questions the business needs to answer.

**Integrated** — data from multiple source systems is cleaned and standardised into consistent formats. "Customer ID" in the CBS might be `C000000001`. In the CRM it might be `SA-CUST-00123`. In the DWH there is one canonical customer identifier. Integration is where most ETL complexity lives.

**Non-volatile** — data in the warehouse is not updated or deleted in the normal operational sense. A transaction that was loaded yesterday stays there. If a correction is needed, a compensating row is added — the original row remains. This makes audit and point-in-time queries straightforward.

**Time-variant** — every row carries a time dimension. Not just "what is the customer's segment" but "what was the customer's segment on 1 January 2024." Regulatory reporting cannot function without this property.

### 1.3 The Kimball Approach — Dimensional Modelling

Ralph Kimball's approach to DWH design is the industry standard for analytical systems. It produces schemas that are fast to query and intuitive for analysts to navigate, at the cost of some normalisation.

The two building blocks are **fact tables** and **dimension tables**.

**Fact tables** store measurements — things that happened, expressed as numbers. Every row in a fact table records one business event at a specific grain.

**Dimension tables** store context — the descriptors that give measurements meaning. A transaction amount means nothing without knowing which branch, which customer, which product, and which date it belongs to.

The relationship between them produces a **star schema** — one central fact table surrounded by dimension tables, each joined on a surrogate key.

```
                    ┌─────────────┐
                    │  DIM_DATE   │
                    │  date_id PK │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────┴──────┐   ┌───────┴────────┐  ┌──────┴──────────┐
│ DIM_CUSTOMER │   │FACT_TRANSACTION│  │   DIM_BRANCH    │
│ dim_cust_sk  ├───┤ date_id    FK  ├──┤  dim_branch_sk  │
│ customer_id  │   │ dim_cust_sk FK │  │  branch_id      │
│ segment      │   │ dim_branch_sk  │  │  region         │
│ risk_rating  │   │ dim_product_sk │  └─────────────────┘
│ kyc_status   │   │ dim_channel_sk │
└──────────────┘   │ amount_sar     │  ┌─────────────────┐
                   │ txn_type       │  │  DIM_PRODUCT    │
                   │ status         ├──┤  dim_product_sk │
                   └───────┬────────┘  │  product_name   │
                           │           │  is_islamic     │
                   ┌───────┴────────┐  └─────────────────┘
                   │  DIM_CHANNEL   │
                   │ dim_channel_sk │
                   │ channel_type   │
                   └────────────────┘
```

### 1.4 Fact Table Design — Grain, Measures, and Additivity

**Grain** is the single most important design decision for a fact table. It defines what one row represents. You must declare the grain before writing any DDL.

For `FACT_TRANSACTION` in the Al-Noor DWH: **one row = one posted banking transaction.**

If you choose the wrong grain — say, one row per day per customer (a summary grain) — you lose the ability to drill into individual transactions, which breaks SAMA audit requirements.

**Measures** are the numeric columns — the things you sum, average, or count. Measures have an additivity property that determines when it is safe to aggregate them:

| Measure type | Can SUM across... | Al-Noor Example |
|---|---|---|
| Fully additive | All dimension combinations | `amount_sar` — safe to sum across date, branch, product, channel |
| Semi-additive | Some dimensions, not all | `balance_after_sar` — safe to sum across customers, NOT across dates (balances at point-in-time) |
| Non-additive | No dimension | A ratio, a percentage — store the components, compute the ratio in the query |

Getting additivity wrong produces incorrect SAMA figures. A SAMA liquidity report that sums `balance_after_sar` across dates is nonsense — it would count the same money multiple times.

**Degenerate dimensions** are attributes that have no dimension table because they do not join to anything — they are just descriptors of the transaction itself. `txn_type`, `direction`, `status` in `FACT_TRANSACTION` are degenerate dimensions. They live directly in the fact table.

### 1.5 Dimension Table Design

**Surrogate keys** — dimension tables use system-generated integer keys (BIGSERIAL in PostgreSQL, AUTOINCREMENT in Snowflake) as the primary key. The natural key from the source system (`customer_id`, `product_code`) is stored as a separate column but is not the join key. This matters for two reasons:

1. A customer's surrogate key changes when their record changes (SCD Type 2). The old surrogate key is permanently linked to historical fact rows. The natural key alone cannot support this.
2. Source system keys are often strings, alphanumeric, or inconsistently formatted. Surrogate keys are always clean integers, which join faster at scale.

**Al-Noor DWH — `FACT_TRANSACTION` DDL (PostgreSQL)**

```sql
-- Grain: one row = one posted banking transaction
CREATE TABLE analytics.fact_transaction (
    fact_txn_sk         BIGSERIAL NOT NULL,

    -- Dimension foreign keys (surrogate keys only — never natural keys)
    date_id             INTEGER NOT NULL,           -- FK to dim_date
    dim_customer_sk     BIGINT NOT NULL,            -- FK to dim_customer
    dim_account_sk      BIGINT NOT NULL,            -- FK to dim_account
    dim_product_sk      BIGINT NOT NULL,            -- FK to dim_product
    dim_branch_sk       BIGINT NOT NULL,            -- FK to dim_branch
    dim_channel_sk      BIGINT NOT NULL,            -- FK to dim_channel

    -- Degenerate dimensions (no separate table warranted)
    txn_type            VARCHAR(30) NOT NULL,       -- MURABAHA_PAYMENT, TRANSFER, etc.
    direction           CHAR(1) NOT NULL,           -- D=debit, C=credit
    status              VARCHAR(15) NOT NULL,       -- POSTED, REVERSED
    source_txn_id       VARCHAR(50),               -- CBS reference — data lineage

    -- Fully additive measures
    amount_sar          NUMERIC(18,2) NOT NULL,
    transaction_count   SMALLINT NOT NULL DEFAULT 1,

    -- Semi-additive measure — comment warns analysts never to SUM across dates
    balance_after_sar   NUMERIC(18,2),             -- WARNING: semi-additive

    etl_load_ts         TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    etl_source_system   VARCHAR(30) NOT NULL,

    CONSTRAINT pk_fact_txn PRIMARY KEY (fact_txn_sk)
) PARTITION BY RANGE (date_id);

-- Annual partition
CREATE TABLE analytics.fact_transaction_2025
    PARTITION OF analytics.fact_transaction
    FOR VALUES FROM (20250101) TO (20260101);

-- Composite indexes on the most common query join patterns
CREATE INDEX idx_fact_txn_date_customer
    ON analytics.fact_transaction (date_id, dim_customer_sk);
CREATE INDEX idx_fact_txn_date_branch
    ON analytics.fact_transaction (date_id, dim_branch_sk);
```

### 1.6 DIM_DATE — The Calendar Dimension

Every DWH needs a date dimension, and it must be pre-populated — not derived at query time. In Saudi banking there are two calendar requirements: Gregorian and Hijri.

```sql
CREATE TABLE analytics.dim_date (
    date_id             INTEGER NOT NULL,      -- YYYYMMDD — the join key
    full_date           DATE NOT NULL,
    day_name_en         VARCHAR(10) NOT NULL,
    month_number        SMALLINT NOT NULL,
    month_name_en       VARCHAR(10) NOT NULL,
    quarter             SMALLINT NOT NULL,
    year                SMALLINT NOT NULL,
    is_weekend          BOOLEAN NOT NULL,      -- Saudi weekend: Friday (DOW=5), Saturday (DOW=6)
    is_public_holiday   BOOLEAN NOT NULL DEFAULT FALSE,
    holiday_name_ar     VARCHAR(100),
    hijri_month         SMALLINT,
    hijri_year          SMALLINT,
    hijri_month_name_ar VARCHAR(30),
    is_ramadan          BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_id)
);

-- Populate for 2025 (PostgreSQL)
INSERT INTO analytics.dim_date (
    date_id, full_date, day_name_en, month_number,
    month_name_en, quarter, year, is_weekend
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER,
    d,
    TO_CHAR(d, 'Day'),
    EXTRACT(MONTH FROM d)::SMALLINT,
    TO_CHAR(d, 'Month'),
    EXTRACT(QUARTER FROM d)::SMALLINT,
    EXTRACT(YEAR FROM d)::SMALLINT,
    EXTRACT(DOW FROM d) IN (5, 6)   -- 5=Friday, 6=Saturday in PostgreSQL
FROM GENERATE_SERIES('2025-01-01'::DATE, '2025-12-31'::DATE, '1 day') AS d;
```

The `date_id` integer key (YYYYMMDD format) joins faster than a DATE column and makes range filtering trivial: `WHERE date_id BETWEEN 20250101 AND 20250331`.

### 1.7 Slowly Changing Dimensions (SCDs)

A customer's segment, risk rating, and relationship branch are not permanent. They change. When they change, the DWH has a design decision: preserve the history or overwrite it?

The answer depends on the *reason* for the change.

**SCD Type 1 — Overwrite**

Use when the old value was simply wrong — a data entry error, a misspelling, a system migration artefact. There is no business event associated with the change. No one needs to know the old value.

```sql
-- Customer name was misspelled at onboarding — correct it, no history needed
UPDATE analytics.dim_customer
SET    full_name_en = 'Ahmed Al-Omari',
       updated_at   = CURRENT_TIMESTAMP
WHERE  customer_id = 'C000000001'
AND    is_current   = TRUE;
```

**SCD Type 2 — New Row**

Use when the change represents a real business event. A customer upgrading from RETAIL to PREMIUM segment is a real event. SAMA regulatory reports run retroactively must use the segment that was active at the time of the transaction — not the current segment.

SCD Type 2 adds `effective_from`, `effective_to`, and `is_current` to the dimension table. Each historical state gets its own row with its own surrogate key.

```sql
-- Step 1: Expire the current record
UPDATE analytics.dim_customer
SET    effective_to = '2025-03-14',
       is_current   = FALSE
WHERE  customer_id = 'C000000001'
AND    is_current   = TRUE;

-- Step 2: Insert the new current record
INSERT INTO analytics.dim_customer (
    customer_id, full_name_en, customer_segment, risk_rating,
    kyc_status, nationality, branch_id, branch_name,
    region, effective_from, effective_to, is_current
)
SELECT
    customer_id, full_name_en,
    'PREMIUM',          -- new segment
    risk_rating, kyc_status, nationality,
    branch_id, branch_name, region,
    '2025-03-15',       -- effective from the change date
    NULL,               -- no end date — currently active
    TRUE
FROM analytics.dim_customer
WHERE customer_id = 'C000000001'
AND   effective_to = '2025-03-14';
```

After this operation, the dimension table has two rows for `C000000001`:
- Row A: `dim_customer_sk=101`, segment=RETAIL, effective 2024-01-01 → 2025-03-14
- Row B: `dim_customer_sk=247`, segment=PREMIUM, effective 2025-03-15 → NULL

A fact row loaded in January 2025 was linked to `dim_customer_sk=101` at load time. A fact row loaded in April 2025 links to `dim_customer_sk=247`. The query result automatically returns the correct historical segment — no special query logic required.

**Mandatory SCD Type 2 attributes in the Al-Noor DWH** (all affect SAMA regulatory reporting):

- `customer_segment` — affects credit risk category
- `risk_rating` — directly used in capital adequacy calculations
- `relationship_branch` — used in branch-level SAMA submissions
- `kyc_status` — required for SAMA AML reporting

**SCD Type 3 — Previous Value Column**

Adds a `previous_value` column alongside the current value. Stores only one level of history. Use sparingly — only when exactly one previous state is needed and full history is not required.

```sql
ALTER TABLE analytics.dim_customer
ADD COLUMN prev_customer_segment VARCHAR(30);

-- On change: shift current to previous, write new current
UPDATE analytics.dim_customer
SET    prev_customer_segment = customer_segment,
       customer_segment      = 'PREMIUM'
WHERE  customer_id = 'C000000001';
```

**SCD Type 6 — Hybrid (1+2+3)**

The surrogate key changes with each state (Type 2), but a `current_segment` column on every historical row always reflects the latest value (Type 1 overwrite), and a `previous_segment` column carries the immediate prior state (Type 3). Useful for Customer 360 views that need both historical accuracy and current-state convenience.

### 1.8 The ETL vs ELT Distinction

**ETL (Extract → Transform → Load)** — data is extracted from the source, transformed outside the target system (in a separate tool or compute layer), and loaded in clean form. The transformation happens before landing in the warehouse.

**ELT (Extract → Load → Transform)** — raw data is loaded directly into the warehouse first. Transformations run inside the warehouse using the warehouse's own compute. This is the modern pattern because warehouse compute (Snowflake, BigQuery, Redshift) is now cheap enough that it is more efficient to transform inside than to maintain a separate compute layer.

In the Al-Noor platform: raw CBS extracts land in Snowflake's `staging` schema as-is. dbt models then run SQL transformations inside Snowflake to produce the `analytics` schema fact and dimension tables. This is ELT.

### 1.9 The Al-Noor EDW — Four Subject Marts

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AL-NOOR ENTERPRISE DWH                        │
│                                                                     │
│  ┌─────────────────┐   ┌─────────────────┐                         │
│  │ TRANSACTIONS    │   │ ISLAMIC FINANCE │                         │
│  │ MART            │   │ MART            │                         │
│  │ FACT_TRANSACTION│   │ FACT_MURABAHA   │                         │
│  │ FACT_PAYMENT    │   │ FACT_MURABAHA   │                         │
│  │                 │   │   _SCHEDULE     │                         │
│  └────────┬────────┘   └────────┬────────┘                         │
│           │                     │                                   │
│  ┌────────┴─────────────────────┴──────────────────┐               │
│  │            SHARED DIMENSIONS                    │               │
│  │  DIM_DATE · DIM_CUSTOMER · DIM_ACCOUNT          │               │
│  │  DIM_PRODUCT · DIM_BRANCH · DIM_CHANNEL         │               │
│  │  DIM_CURRENCY                                   │               │
│  └────────┬─────────────────────┬──────────────────┘               │
│           │                     │                                   │
│  ┌────────┴────────┐   ┌────────┴────────┐                         │
│  │ CUSTOMER 360    │   │ RISK &          │                         │
│  │ MART            │   │ COMPLIANCE MART │                         │
│  │ (DIM_CUSTOMER   │   │ FACT_AML_ALERT  │                         │
│  │  SCD Type 2)    │   │ FACT_KYC_EVENT  │                         │
│  └─────────────────┘   └─────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
```

Shared dimensions ensure that a SAMA report joining the Transactions Mart and the Islamic Finance Mart uses the same customer, branch, and product records — no reconciliation required.

---

## Part 2 — Snowflake Architecture and Operations

### 2.1 Why Snowflake and Not PostgreSQL for the DWH

PostgreSQL is an excellent transactional database. It is the wrong tool for an analytical warehouse at scale, and the specific failure modes matter:

| Requirement | PostgreSQL Reality | Snowflake Solution |
|---|---|---|
| SAMA report in <2s on 1 billion rows | Requires careful partitioning, indexing, query tuning, hardware | Columnar micro-partitions with automatic pruning — no index management |
| 15 analysts concurrently at 7 AM | CPU contention, query queuing, possible deadlocks | Multi-cluster warehouse — each team gets dedicated compute |
| 500K rows/day growing for 10 years | Manual partition management, table bloat, VACUUM scheduling | Serverless auto-scaling — zero DBA intervention |
| Point-in-time table state for SAMA audit | Manual reconstruction from SCD history | Time Travel — `AT (TIMESTAMP => ...)` in one line |
| PDPL right to erasure (customer data deletion) | Complex UPDATE across partitioned tables, index rebuilds | `DELETE` statement — propagated automatically, auditable via Time Travel |
| Dev/test data cloning | pg_dump → restore (hours) | `CREATE TABLE ... CLONE` — zero-copy, instant |

The core issue is that PostgreSQL uses a row-store format and shared compute. Every query competes for the same CPU and I/O. Snowflake separates storage from compute entirely, uses columnar storage that reads only the columns a query touches, and allows multiple compute clusters to run against the same data simultaneously.

### 2.2 Snowflake's Three-Layer Architecture

Snowflake's architecture has three distinct layers. Understanding the separation is essential for reasoning about performance, cost, and failure modes.

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1 — CLOUD SERVICES                                        │
│  Authentication · Query parsing · Optimisation · Metadata       │
│  Transaction management · Security & RBAC                       │
│  (Runs 24/7 on Snowflake-managed infrastructure)                │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 2 — COMPUTE (Virtual Warehouses)                          │
│  al_noor_etl_wh      al_noor_analytics_wh    al_noor_ml_wh      │
│  ┌────────────┐       ┌────────────┐          ┌────────────┐    │
│  │ Worker     │       │ Worker     │          │ Worker     │    │
│  │ nodes      │       │ nodes      │          │ nodes      │    │
│  └────────────┘       └────────────┘          └────────────┘    │
│  (Auto-suspend when idle. Auto-resume on query. Pay per second) │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 3 — STORAGE                                               │
│  Columnar micro-partitions · Auto-encrypted · S3/Azure/GCS      │
│  All virtual warehouses read from the same storage layer         │
│  (Pay per TB stored. Independent of compute costs)              │
└──────────────────────────────────────────────────────────────────┘
```

**Key implication of this architecture:** Five virtual warehouses can run simultaneously against the same data — ETL pipeline, SAMA reporting, analyst queries, ML feature extraction, data quality checks. They do not compete. Adding a new team does not slow down existing workloads. This is architecturally impossible in a shared-compute system like PostgreSQL.

### 2.3 Virtual Warehouses — Compute as a Configurable Resource

A virtual warehouse is a cluster of compute nodes that executes queries. It has no data of its own — it reads from the storage layer.

Key properties:
- **Size** — XS, S, M, L, XL, 2XL, ... Each size doubles the compute (and cost). An XS is 1 credit/hour. A S is 2 credits/hour. You pick the size based on query complexity, not data volume.
- **Auto-suspend** — the warehouse suspends after N seconds of inactivity. No queries running = no credits consumed. In free tier, set `AUTO_SUSPEND = 60` to avoid burning credits.
- **Auto-resume** — resumes automatically when a query arrives. The first query after suspension has ~1–2 second startup latency.
- **Multi-cluster** — a warehouse can scale out from 1 to N clusters if concurrent query load exceeds single-cluster capacity. Each additional cluster doubles cost but eliminates queuing.

```sql
-- ETL warehouse — slightly larger, can scale out for parallel Airflow tasks
CREATE WAREHOUSE al_noor_etl_wh
    WAREHOUSE_SIZE    = 'SMALL'
    AUTO_SUSPEND      = 120          -- 2 minutes idle → suspend
    AUTO_RESUME       = TRUE
    MAX_CLUSTER_COUNT = 2            -- scale to 2 clusters if load spikes
    COMMENT           = 'Nightly ELT — Airflow + dbt';

-- Analytics warehouse — smallest size for reporting queries
CREATE WAREHOUSE al_noor_analytics_wh
    WAREHOUSE_SIZE    = 'XSMALL'
    AUTO_SUSPEND      = 60
    AUTO_RESUME       = TRUE
    COMMENT           = 'SAMA reporting, Power BI, Apache Superset';
```

### 2.4 Columnar Storage and Micro-Partitions

PostgreSQL stores data in **pages** — each page contains multiple full rows. A query that touches only 2 columns of a 30-column table still reads the full page, loading all 30 columns off disk.

Snowflake stores data in **micro-partitions** — immutable files of 50–500 MB, stored in columnar format. A query touching 2 columns reads only those 2 columns from storage. For a 100-column fact table running a 5-column SAMA report, this eliminates 95% of I/O.

Each micro-partition carries **metadata** — min value, max value, null count, distinct count per column. The Cloud Services layer uses this metadata for **partition pruning**: if a query filters `WHERE date_id BETWEEN 20250101 AND 20250331`, Snowflake reads the min/max metadata of every micro-partition and skips any partition where `max(date_id) < 20250101` or `min(date_id) > 20250331`. For a 7-year fact table, this might skip 85% of all storage reads before executing a single query.

**CLUSTER BY** — for very large tables (hundreds of billions of rows), you can declare a clustering key. Snowflake will periodically reorganise micro-partitions so that rows with the same clustering key value end up in the same partitions, improving pruning effectiveness.

```sql
-- fact_transaction clustered by date and txn_type
-- SAMA reports almost always filter on date; branch reports often add txn_type
CREATE TABLE fact_transaction (
    ...
) CLUSTER BY (date_id, txn_type);
```

For tables under ~1 TB, `CLUSTER BY` is usually unnecessary. Snowflake's automatic micro-partition organisation is already effective.

### 2.5 Snowflake Object Hierarchy

```
ORGANISATION (Snowflake account group — enterprise-level)
└── ACCOUNT (your Snowflake instance, e.g. al-noor.snowflakecomputing.com)
    ├── DATABASE (al_noor_dwh)
    │   ├── SCHEMA (staging)
    │   │   └── TABLES, VIEWS, STAGES, PIPES
    │   ├── SCHEMA (analytics)
    │   │   └── TABLES, VIEWS
    │   └── SCHEMA (compliance)
    │       └── TABLES, VIEWS
    ├── WAREHOUSE (al_noor_etl_wh)
    ├── WAREHOUSE (al_noor_analytics_wh)
    └── ROLES (etl_pipeline_role, analyst_role, compliance_role)
```

Every action in Snowflake requires two things: a role with the appropriate privilege, and an active warehouse to execute compute. Forgetting to `USE WAREHOUSE` is the most common first-time error.

### 2.6 Role-Based Access Control (RBAC)

Snowflake uses a role hierarchy. Permissions are granted to roles, not to users directly. Users are granted roles.

Built-in roles (from highest to lowest privilege):
- `ACCOUNTADMIN` — full account control, billing visibility. Only for account owners.
- `SYSADMIN` — creates databases, warehouses, and objects. Day-to-day admin.
- `SECURITYADMIN` — creates users and roles, manages grants.
- `USERADMIN` — creates users and roles only.
- `PUBLIC` — every user automatically has this role.

```sql
-- Run as SECURITYADMIN
CREATE ROLE etl_pipeline_role    COMMENT = 'Airflow service account — full write on analytics schema';
CREATE ROLE analyst_role         COMMENT = 'Read-only on analytics schema';
CREATE ROLE compliance_role      COMMENT = 'Read on analytics + compliance schemas';
CREATE ROLE sama_reporting_role  COMMENT = 'Restricted read for SAMA report generation';

-- Grant warehouse usage
GRANT USAGE ON WAREHOUSE al_noor_etl_wh       TO ROLE etl_pipeline_role;
GRANT USAGE ON WAREHOUSE al_noor_analytics_wh TO ROLE analyst_role;
GRANT USAGE ON WAREHOUSE al_noor_analytics_wh TO ROLE compliance_role;
GRANT USAGE ON WAREHOUSE al_noor_analytics_wh TO ROLE sama_reporting_role;

-- Grant database and schema access
GRANT USAGE ON DATABASE al_noor_dwh TO ROLE etl_pipeline_role;
GRANT USAGE ON DATABASE al_noor_dwh TO ROLE analyst_role;
GRANT USAGE ON SCHEMA al_noor_dwh.analytics TO ROLE etl_pipeline_role;
GRANT USAGE ON SCHEMA al_noor_dwh.analytics TO ROLE analyst_role;

-- ETL role gets full write on analytics
GRANT ALL PRIVILEGES ON SCHEMA al_noor_dwh.analytics TO ROLE etl_pipeline_role;

-- Analyst role gets read-only on all current and future tables
GRANT SELECT ON ALL TABLES IN SCHEMA al_noor_dwh.analytics TO ROLE analyst_role;
GRANT SELECT ON FUTURE TABLES IN SCHEMA al_noor_dwh.analytics TO ROLE analyst_role;

-- Assign roles to users
GRANT ROLE etl_pipeline_role   TO USER airflow_service;
GRANT ROLE analyst_role        TO USER rania_al_harbi;
GRANT ROLE sama_reporting_role TO USER sama_reporting_bot;
```

**GRANT ON FUTURE TABLES** is critical — without it, every new table created in the schema requires a separate `GRANT SELECT` before analysts can query it.

### 2.7 Snowflake DDL — Key Differences from PostgreSQL

Snowflake SQL is mostly ANSI-standard with some important differences:

| Feature | PostgreSQL | Snowflake |
|---|---|---|
| Auto-increment | `BIGSERIAL` or `GENERATED ALWAYS AS IDENTITY` | `NUMBER AUTOINCREMENT` or `IDENTITY` |
| Timezone-aware timestamp | `TIMESTAMPTZ` | `TIMESTAMP_TZ` |
| Generate series | `GENERATE_SERIES(start, end, step)` | `TABLE(GENERATOR(ROWCOUNT => n))` + `DATEADD` |
| Day of week numbering | Sunday=0, Monday=1, ..., Saturday=6 | Sunday=1, Monday=2, ..., Saturday=7 |
| Saudi weekend (Fri+Sat) | `DOW IN (5, 6)` | `DAYOFWEEK IN (6, 7)` |
| Table indexes | `CREATE INDEX` | Not supported — micro-partition pruning replaces them |
| Clustering | Manual partitioning | `CLUSTER BY (col1, col2)` |
| JSON querying | `->` and `->>` operators | `PARSE_JSON()`, `col:field::type` |

**`dim_customer` in Snowflake:**

```sql
USE DATABASE al_noor_dwh;
USE SCHEMA analytics;
USE WAREHOUSE al_noor_etl_wh;

CREATE TABLE dim_customer (
    dim_customer_sk   NUMBER AUTOINCREMENT PRIMARY KEY,
    customer_id       VARCHAR(10) NOT NULL,
    full_name_en      VARCHAR(200),
    customer_segment  VARCHAR(30),
    risk_rating       CHAR(1),
    kyc_status        VARCHAR(20),
    nationality       CHAR(3),
    branch_id         VARCHAR(10),
    branch_name       VARCHAR(100),
    region            VARCHAR(50),
    effective_from    DATE NOT NULL,
    effective_to      DATE,
    is_current        BOOLEAN NOT NULL DEFAULT TRUE
) CLUSTER BY (customer_id, is_current);
-- CLUSTER BY here improves pruning for SCD2 lookups:
-- "find the current record for customer_id X" is the hottest query pattern
```

**`fact_transaction` in Snowflake:**

```sql
CREATE TABLE fact_transaction (
    fact_txn_sk       NUMBER AUTOINCREMENT PRIMARY KEY,
    date_id           INTEGER NOT NULL,
    dim_customer_sk   NUMBER NOT NULL,
    dim_account_sk    NUMBER NOT NULL,
    dim_product_sk    NUMBER NOT NULL,
    dim_branch_sk     NUMBER NOT NULL,
    dim_channel_sk    NUMBER NOT NULL,
    txn_type          VARCHAR(30) NOT NULL,
    direction         CHAR(1) NOT NULL,
    status            VARCHAR(15) NOT NULL,
    source_txn_id     VARCHAR(50),
    amount_sar        NUMBER(18,2) NOT NULL,
    etl_load_ts       TIMESTAMP_TZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    etl_source_system VARCHAR(30) NOT NULL,
    FOREIGN KEY (date_id)          REFERENCES dim_date(date_id),
    FOREIGN KEY (dim_customer_sk)  REFERENCES dim_customer(dim_customer_sk)
) CLUSTER BY (date_id, txn_type);
```

### 2.8 DIM_DATE in Snowflake — GENERATOR Syntax

PostgreSQL has `GENERATE_SERIES`. Snowflake does not. The equivalent uses `TABLE(GENERATOR(ROWCOUNT => n))` with `ROW_NUMBER()` and `DATEADD`:

```sql
INSERT INTO al_noor_dwh.analytics.dim_date (
    date_id, full_date, day_name_en, month_number,
    month_name_en, quarter, year, is_weekend
)
SELECT
    TO_NUMBER(TO_CHAR(d::DATE, 'YYYYMMDD'))    AS date_id,
    d::DATE                                     AS full_date,
    DAYNAME(d::DATE)                            AS day_name_en,
    MONTH(d::DATE)                              AS month_number,
    MONTHNAME(d::DATE)                          AS month_name_en,
    QUARTER(d::DATE)                            AS quarter,
    YEAR(d::DATE)                               AS year,
    DAYOFWEEK(d::DATE) IN (6, 7)               AS is_weekend  -- Fri=6, Sat=7 in Snowflake
FROM (
    SELECT DATEADD('day',
                   ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1,
                   '2025-01-01') AS d
    FROM TABLE(GENERATOR(ROWCOUNT => 365))
);
```

### 2.9 Time Travel

Snowflake retains a history of every change to every table for up to 90 days (1 day on free tier). You can query any table as it existed at any past point in time — with no additional infrastructure and no prior setup beyond the retention period setting.

**Syntax:**

```sql
-- Point-in-time query — how did the table look at this exact timestamp?
SELECT * FROM fact_transaction
AT (TIMESTAMP => '2025-01-01 00:00:00'::TIMESTAMP_TZ);

-- Offset query — how did the table look 30 days ago?
SELECT * FROM fact_transaction
AT (OFFSET => -60 * 60 * 24 * 30);   -- seconds

-- Statement query — how did the table look immediately before a specific statement ran?
SELECT * FROM dim_customer
BEFORE (STATEMENT => '019c3b5d-0504-ba6e-0001-23d200010012');

-- Get the most recent statement ID
SELECT LAST_QUERY_ID();
```

**SAMA audit use case:** A capital adequacy report was submitted in January 2025. SAMA queries the submitted figures in September 2025. Using Time Travel, the exact state of `fact_transaction` at the moment the January report ran is retrievable in one query.

**PDPL right to erasure use case:**

```sql
-- Step 1: Archive what will be deleted (before deleting)
SELECT * FROM fact_transaction
AT (OFFSET => -60 * 60 * 24 * 30)    -- 30 days ago
WHERE source_txn_id IN (
    SELECT source_txn_id FROM staging.stg_transactions
    WHERE account_id IN (
        SELECT account_id FROM dim_account
        WHERE  customer_id = 'C000000001'
    )
);

-- Step 2: Execute the deletion
DELETE FROM analytics.dim_customer
WHERE customer_id = 'C000000001';

-- Step 3: Verify — confirm the record existed before deletion
SELECT customer_id, full_name_en, effective_from
FROM analytics.dim_customer
BEFORE (STATEMENT => LAST_QUERY_ID())
WHERE customer_id = 'C000000001';
-- Returns the deleted record — Time Travel proves existence for compliance log
```

### 2.10 Zero-Copy Cloning

Snowflake can create an instant, full-size copy of any table, schema, or database without duplicating the underlying storage. The clone shares the original's micro-partitions until either copy writes new data.

```sql
-- Create a development copy of the full DWH — instant, no storage cost
CREATE DATABASE al_noor_dwh_dev CLONE al_noor_dwh;

-- Clone a single table for testing an ELT fix
CREATE TABLE analytics.fact_transaction_backup
CLONE analytics.fact_transaction;
```

Use cases: ETL development (test against production-scale data without affecting production), schema migration testing, SAMA audit snapshots that need to be preserved independently of live data.

### 2.11 Stages and the COPY INTO Pattern

Snowflake does not support direct INSERT from external files through a JDBC connection the way PostgreSQL does. Data lands in a **Stage** first, then is loaded into a table via `COPY INTO`.

A Stage is a pointer to a storage location — either an internal Snowflake location or an external cloud bucket (S3, ADLS, GCS).

```sql
-- Create an internal stage for the CBS daily extract
CREATE STAGE al_noor_dwh.staging.cbs_extract_stage
    COMMENT = 'Landing zone for CBS daily Parquet extracts';

-- Upload a file to the internal stage (done from SnowSQL CLI or Airflow)
-- PUT file:///local/path/transactions_2025-01-15.parquet @staging.cbs_extract_stage;

-- Load from stage into staging table
COPY INTO staging.stg_transactions
FROM @staging.cbs_extract_stage/transactions_2025-01-15.parquet
FILE_FORMAT = (TYPE = 'PARQUET')
ON_ERROR = 'ABORT_STATEMENT';  -- fail the entire load on any error
```

`ON_ERROR = 'CONTINUE'` skips bad rows. `ON_ERROR = 'ABORT_STATEMENT'` rolls back the entire load on any error. For SAMA-submitted data, `ABORT_STATEMENT` is the correct default — partial loads are worse than no load.

### 2.12 Query Profile — Reading Snowflake's Execution Plan

After any query, the Snowflake UI shows a **Query Profile** — a graphical execution plan that breaks down time spent in each operation.

Key metrics to read:
- **Bytes scanned** — total storage read. Compare against **Bytes scanned from cache** (in-memory from a previous run on the same warehouse).
- **Partitions scanned vs total partitions** — partition pruning effectiveness. If you scanned 50 of 10,000 partitions, your `CLUSTER BY` and filter predicates are working well. If you scanned 9,800 of 10,000, they are not.
- **Spillage to disk** — if intermediate data does not fit in the warehouse's memory, Snowflake spills to local SSD (fast) or remote storage (slow). Spill indicates the warehouse size is too small for the join or aggregation.
- **Percentage per node** — skewed distribution means some worker nodes are doing most of the work. Usually caused by data skew on join keys.

---

## Part 3 — dbt + Snowflake (ELT in Practice)

### 3.1 What dbt Does

dbt (data build tool) runs SQL `SELECT` statements inside Snowflake and materialises the results as tables or views. Each model is one `.sql` file. dbt handles dependency resolution, incremental loading, documentation, and testing.

The `fact_transaction` dbt model runs inside Snowflake — no data leaves the warehouse during transformation:

```sql
-- models/analytics/fact_transaction.sql
{{ config(
    materialized      = 'incremental',
    unique_key        = 'source_txn_id',
    cluster_by        = ['date_id', 'txn_type'],
    snowflake_warehouse = 'al_noor_etl_wh'
) }}

SELECT
    TO_NUMBER(TO_CHAR(ot.txn_date, 'YYYYMMDD'))  AS date_id,
    dc.dim_customer_sk,
    da.dim_account_sk,
    dp.dim_product_sk,
    db.dim_branch_sk,
    dch.dim_channel_sk,
    ot.txn_type,
    ot.direction,
    ot.status,
    ot.source_txn_id,
    ot.amount_sar,
    1                                             AS transaction_count,
    CURRENT_TIMESTAMP()                           AS etl_load_ts,
    ot.source_system                              AS etl_source_system
FROM {{ source('staging', 'stg_transactions') }}   ot
JOIN {{ ref('dim_customer') }}                     dc
    ON dc.customer_id = ot.customer_id AND dc.is_current
JOIN {{ ref('dim_account') }}                      da ON da.account_id  = ot.account_id
JOIN {{ ref('dim_product') }}                      dp ON dp.product_id  = ot.product_id
JOIN {{ ref('dim_branch') }}                       db ON db.branch_id   = ot.branch_id
JOIN {{ ref('dim_channel') }}                      dch ON dch.channel_id = ot.channel_id
WHERE ot.status = 'POSTED'
{% if is_incremental() %}
    AND ot.txn_date >= (SELECT MAX(etl_load_ts) FROM {{ this }})
{% endif %}
```

`is_incremental()` evaluates to `TRUE` on all runs except the first. On incremental runs, only new records are inserted — the full table is not rebuilt nightly. For a 7-year fact table with 1.3 billion rows, this is the difference between a 2-minute load and a 4-hour rebuild.

---

## Key Architecture Decisions — Summary

| Decision | Rationale |
|---|---|
| Star schema over 3NF normalisation | 3NF reduces redundancy but requires many joins. Star schema denormalises into fact + dimensions — fewer joins, faster analytical queries. |
| Surrogate keys over natural keys in dimensions | Natural keys change (customer IDs migrated, product codes reused). Surrogate keys are stable. SCD Type 2 requires surrogate keys. |
| Integer YYYYMMDD as date_id | Joins faster than DATE. Range filtering intuitive: `BETWEEN 20250101 AND 20250331`. |
| SCD Type 2 for regulatory attributes | SAMA retroactive reporting requires point-in-time accuracy. Overwriting (Type 1) destroys audit evidence. |
| Snowflake for DWH, PostgreSQL for ODS | Snowflake: analytical scale, Time Travel, compute separation. PostgreSQL: operational near-current store, CDC source, transactional workloads. |
| CLUSTER BY instead of indexes | Snowflake micro-partitions replace row-store indexes. CLUSTER BY guides micro-partition organisation for the most common filter patterns. |
| dbt for transformations | SQL-native, version-controlled, testable, incremental. Transformations run inside Snowflake — no separate compute layer to operate. |
| 90-day Time Travel retention | SAMA requires audit evidence. PDPL requires demonstrable erasure. 90 days covers both without the cost of 365-day retention. |

---

*Lab exercises covering all Snowflake operations — account setup, RBAC, DDL, data loading, time travel, and query profiling — are in the companion lab document: `Day7-Snowflake-Labs.md`.*