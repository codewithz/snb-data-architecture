# CDC vs SCD: Capturing Change in Data Engineering

## What This Document Covers

Two mechanisms dominate how data engineering teams handle change in source data:

- **CDC (Change Data Capture)** — how you *detect and transport* changes from a source system
- **SCD (Slowly Changing Dimensions)** — how you *store and model* those changes in a warehouse

They solve different problems. CDC is a pipeline concern. SCD is a modelling concern. They are frequently used together, but conflating them causes architectural mistakes.

---

## Part 1 — Change Data Capture (CDC)

### What CDC Is

CDC is a pattern for identifying and streaming row-level changes (INSERT, UPDATE, DELETE) from a transactional source system into a downstream consumer — usually a data warehouse, data lake, or event stream.

The key property: CDC captures *what changed*, *what it changed to*, and *when* — without requiring the application to be modified.

### CDC Mechanisms

| Mechanism | How It Works | Latency | Risk |
|---|---|---|---|
| **Log-based** (Debezium, DMS) | Reads database transaction log (WAL / binlog) | Near real-time | Log retention must be managed |
| **Trigger-based** | DB triggers write changes to a shadow table | Low-medium | Adds write overhead to source |
| **Timestamp-based** | Polls for rows where `updated_at > last_run` | Batch intervals | Misses hard deletes |
| **Diff-based** | Compares full snapshots | High | Only viable for small tables |

Log-based CDC is the production standard for financial systems. It is non-intrusive, captures all DML operations including hard deletes, and operates at sub-second latency.

---

### Real Example: Al-Noor Retail Bank — Murabaha Financing Ledger

Al-Noor's core banking system runs on Oracle. The `murabaha_financing` table is updated whenever a customer makes a profit instalment payment, a restructuring occurs, or an account status changes (active → delinquent → settled).

The analytics team needs these changes reflected in Snowflake within 5 minutes for real-time risk dashboards required under SAMA's credit risk reporting framework.

**Source table (Oracle core banking)**

```sql
CREATE TABLE murabaha_financing (
    financing_id     VARCHAR2(20)    PRIMARY KEY,
    customer_id      VARCHAR2(15)    NOT NULL,
    outstanding_balance NUMBER(18,2) NOT NULL,
    account_status   VARCHAR2(20)    NOT NULL,  -- ACTIVE, DELINQUENT, SETTLED
    last_payment_date DATE,
    updated_at       TIMESTAMP       NOT NULL
);
```

**Debezium configuration — capturing changes from Oracle WAL**

```json
{
  "name": "al-noor-murabaha-cdc",
  "config": {
    "connector.class": "io.debezium.connector.oracle.OracleConnector",
    "database.hostname": "oracle-core.al-noor.internal",
    "database.dbname": "ALNOORPROD",
    "table.include.list": "COREBANK.MURABAHA_FINANCING",
    "topic.prefix": "al-noor",
    "snapshot.mode": "initial",
    "log.mining.strategy": "online_catalog"
  }
}
```

**What a CDC event looks like on the Kafka topic**

```json
{
  "op": "u",
  "ts_ms": 1718012345678,
  "before": {
    "financing_id": "MRB-2024-00847",
    "outstanding_balance": 185000.00,
    "account_status": "ACTIVE"
  },
  "after": {
    "financing_id": "MRB-2024-00847",
    "outstanding_balance": 172500.00,
    "account_status": "ACTIVE",
    "last_payment_date": "2024-06-10",
    "updated_at": "2024-06-10T09:22:15Z"
  }
}
```

`op: "u"` means UPDATE. `before` gives you the prior state. `after` gives you the new state. A delete would be `op: "d"` with `after: null`.

**What happens without CDC**

If the team used a nightly batch job polling `updated_at`, they would miss any records deleted from the source (settled accounts purged from the OLTP system). They would also be blind to intraday changes for 8–14 hours, violating SAMA's near-real-time reporting requirement for credit exposure.

---

## Part 2 — Slowly Changing Dimensions (SCD)

### What SCD Is

SCD is a dimensional modelling pattern that defines *how a data warehouse stores the history of changes* to a dimension entity (customer, product, account, branch).

The core problem: a customer's risk tier changes. Their city changes. Their KYC classification changes. Do you overwrite the old value (losing history), or preserve it (adding complexity)?

SCD Types define that tradeoff.

---

### SCD Type 1 — Overwrite

**Use when:** history is irrelevant; only the current state matters.

The old value is destroyed. No audit trail.

```sql
-- Customer's phone number is corrected
UPDATE dim_customer
SET    phone_number = '+966501234567',
       updated_at   = CURRENT_TIMESTAMP
WHERE  customer_id  = 'C-00291';
```

**When Al-Noor uses Type 1:** Correcting a data entry error on a customer's national ID (Iqama) number. The old value was wrong — there is no legitimate reason to preserve it.

---

### SCD Type 2 — Add a New Row (Full History)

**Use when:** history must be preserved and queryable. This is the standard for analytical workloads where you need point-in-time accuracy.

Each change creates a new row. The previous row is closed with an `effective_to` date. The active record is flagged.

**Schema**

```sql
CREATE TABLE dim_customer (
    customer_sk      BIGINT       PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    customer_id      VARCHAR(15)  NOT NULL,          -- natural key
    full_name        VARCHAR(100) NOT NULL,
    risk_tier        VARCHAR(10)  NOT NULL,           -- LOW, MEDIUM, HIGH
    kyc_status       VARCHAR(20)  NOT NULL,
    effective_from   DATE         NOT NULL,
    effective_to     DATE,                            -- NULL = current record
    is_current       BOOLEAN      NOT NULL DEFAULT TRUE
);
```

**Real example: Al-Noor customer risk tier upgrade**

Customer Reem Al-Ghamdi (C-00291) is reclassified from LOW to HIGH risk by the AML team on 14 June 2024 — triggering a SAMA PDPL-compliant audit trail requirement.

*Step 1 — Close the existing record*

```sql
UPDATE dim_customer
SET    effective_to = '2024-06-13',
       is_current   = FALSE
WHERE  customer_id  = 'C-00291'
  AND  is_current   = TRUE;
```

*Step 2 — Insert the new record*

```sql
INSERT INTO dim_customer (
    customer_id, full_name, risk_tier, kyc_status,
    effective_from, effective_to, is_current
)
VALUES (
    'C-00291', 'Reem Al-Ghamdi', 'HIGH', 'VERIFIED',
    '2024-06-14', NULL, TRUE
);
```

*Resulting table state*

| customer_sk | customer_id | risk_tier | effective_from | effective_to | is_current |
|---|---|---|---|---|---|
| 1001 | C-00291 | LOW | 2024-01-01 | 2024-06-13 | FALSE |
| 1002 | C-00291 | HIGH | 2024-06-14 | NULL | TRUE |

*Querying point-in-time: what was Reem's risk tier on 1 March 2024?*

```sql
SELECT risk_tier
FROM   dim_customer
WHERE  customer_id    = 'C-00291'
  AND  effective_from <= '2024-03-01'
  AND  (effective_to  >= '2024-03-01' OR effective_to IS NULL);
-- Returns: LOW
```

**Why this matters for Al-Noor:** SAMA audit teams regularly request point-in-time customer state during regulatory reviews. Without SCD Type 2, the bank cannot reconstruct what classification a customer held at the time of a specific transaction.

---

### SCD Type 3 — Add a Column

**Use when:** you only need to track one prior value and the transition between them.

```sql
ALTER TABLE dim_customer
ADD COLUMN  previous_risk_tier VARCHAR(10),
ADD COLUMN  risk_tier_changed_at DATE;
```

```sql
UPDATE dim_customer
SET    previous_risk_tier   = risk_tier,
       risk_tier            = 'HIGH',
       risk_tier_changed_at = '2024-06-14'
WHERE  customer_id = 'C-00291';
```

*Resulting row*

| customer_id | risk_tier | previous_risk_tier | risk_tier_changed_at |
|---|---|---|---|
| C-00291 | HIGH | LOW | 2024-06-14 |

**Limitation:** A third change destroys the second value. You can only ever see "current" and "previous one". This is rarely sufficient for compliance use cases.

**When Al-Noor uses Type 3:** Branch managers want a quick "was this customer previously a different tier" flag in a customer 360 view, with no need for full history navigation. One column change is enough.

---

### SCD Type 4 — History Table

**Use when:** the main dimension table must remain lean (no extra rows) but full history is required in a separate audit table.

```sql
-- Lean operational dimension
CREATE TABLE dim_customer (
    customer_id  VARCHAR(15) PRIMARY KEY,
    risk_tier    VARCHAR(10),
    kyc_status   VARCHAR(20),
    updated_at   TIMESTAMP
);

-- Separate history table
CREATE TABLE dim_customer_history (
    history_sk   BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    customer_id  VARCHAR(15),
    risk_tier    VARCHAR(10),
    kyc_status   VARCHAR(20),
    valid_from   TIMESTAMP,
    valid_to     TIMESTAMP,
    changed_by   VARCHAR(50)  -- operator ID, useful for SAMA audit trails
);
```

**When Al-Noor uses Type 4:** The customer master dimension is used by operational BI tools that join it millions of times per day. Adding SCD Type 2 rows would bloat the join. The history table sits separately, queried only when compliance needs a full audit log.

---

### SCD Type 6 — Hybrid (Type 1 + 2 + 3)

Type 6 combines all three: each change creates a new row (Type 2), the current value is propagated back to all historical rows (Type 1 overwrite of a `current_*` column), and the previous value is stored inline (Type 3).

```sql
CREATE TABLE dim_customer (
    customer_sk          BIGINT PRIMARY KEY,
    customer_id          VARCHAR(15),
    -- Type 2 columns
    risk_tier            VARCHAR(10),   -- value at this point in time
    effective_from       DATE,
    effective_to         DATE,
    is_current           BOOLEAN,
    -- Type 3 column
    previous_risk_tier   VARCHAR(10),
    -- Type 1 column (always current, updated across all rows)
    current_risk_tier    VARCHAR(10)
);
```

This allows analysts to query current state without a filter (`WHERE is_current = TRUE`), while still supporting point-in-time lookups and one-step-back comparisons. The tradeoff is maintenance complexity — every change triggers updates across all historical rows to refresh `current_risk_tier`.

---

## Part 3 — CDC and SCD Working Together

CDC and SCD are not alternatives — they operate at different layers of the pipeline.

```
Source DB (Oracle)
      │
      │  CDC (Debezium → Kafka)
      │  Captures: what changed, when, before/after state
      ▼
Kafka Topic: al-noor.murabaha_financing
      │
      │  Stream processor (Airflow / dbt / Flink)
      │  Applies SCD logic to incoming CDC events
      ▼
Snowflake: dim_customer (SCD Type 2)
           fact_murabaha_payments
```

**The pattern in practice**

When a CDC event arrives with `op: "u"` (update):

1. Look up the current record in `dim_customer` by `customer_id`
2. If the change is to a Type 2 attribute (e.g., `risk_tier`): close the current row, insert a new one
3. If the change is to a Type 1 attribute (e.g., correcting a typo): overwrite in place
4. Write the fact record referencing the correct `customer_sk` for that point in time

**dbt snapshot implementing SCD Type 2 from a CDC-fed staging table**

```sql
{% snapshot dim_customer_snapshot %}

{{
  config(
    target_schema = 'snapshots',
    unique_key    = 'customer_id',
    strategy      = 'check',
    check_cols    = ['risk_tier', 'kyc_status', 'segment_code']
  )
}}

SELECT
    customer_id,
    full_name,
    risk_tier,
    kyc_status,
    segment_code,
    updated_at
FROM {{ ref('stg_customers') }}

{% endsnapshot %}
```

dbt manages `dbt_valid_from`, `dbt_valid_to`, and `dbt_scd_id` automatically. The staging model (`stg_customers`) is fed from the CDC-populated raw table.

---

## Summary Comparison

| Dimension | CDC | SCD |
|---|---|---|
| **Layer** | Pipeline / transport | Data modelling / storage |
| **Answers** | "What changed in the source?" | "How do we store that change?" |
| **Tool examples** | Debezium, AWS DMS, Fivetran | dbt snapshots, custom ETL, Airflow |
| **Output** | Event stream of row-level changes | Versioned rows in a dimension table |
| **Operates on** | Source system (OLTP) | Target system (warehouse) |
| **Key concern** | Latency, completeness, ordering | History retention, query performance |
| **Used without the other?** | Yes — CDC alone for event streaming | Yes — SCD from batch loads without CDC |

---

## Common Mistakes

**Treating CDC as a replacement for SCD**
CDC tells you a change happened. It does not preserve that change in a queryable historical form in your warehouse. You still need SCD to model the history correctly.

**Using SCD Type 1 on regulated attributes**
Overwriting a customer's risk classification, KYC status, or account segment in a financial warehouse destroys the audit trail. Under SAMA DMF and PDPL, this creates a compliance gap. Any attribute referenced in a regulatory report needs SCD Type 2 (or Type 4).

**Timestamp-based CDC missing hard deletes**
`WHERE updated_at > :last_run` will never catch rows that were physically deleted from the source. Log-based CDC (Debezium) captures `op: "d"` events. Timestamp polling does not. In Al-Noor's context, settled Murabaha accounts purged from the OLTP after 90 days would silently disappear from the warehouse without log-based CDC.

**Not aligning SCD type to reporting requirements before building**
Teams that default to SCD Type 2 for everything end up with dimension tables growing unboundedly and complex joins. Validate which attributes actually require historical queries before choosing the type. Most operational attributes need Type 1. Regulatory and analytical attributes need Type 2.