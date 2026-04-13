# Day 6 — Learning Brief
## Staging · ODS · DWH · Schema Types · NoSQL · CAP · ACID vs BASE
### Al-Noor Bank | SNB Data Management Capability Programme

---

> **What this document is.**
>
> This is your pre-reading and reference brief for Day 6.
> Every concept covered in the day's sessions is explained here —
> what it is, why it exists, how it connects to Saudi banking,
> and where it sits in the Al-Noor architecture.
>
> Read it before the session. Return to it during the labs.
> The concepts build on each other in the order they appear below.

---

## Part 1 — The Data Journey: Where Does Data Live Before the Report?

---

### The Question That Frames the Day

The SAMA daily liquidity report must be on the regulator's
desk by 7:00 AM. The transactions that feed it were posted
in the Core Banking System at 11:00 PM the night before.

Eight hours. Multiple systems. Multiple transformations.
Multiple quality checks. One report.

```
CBS Transaction  ──►  Staging  ──►  ODS  ──►  Data Lake / DWH  ──►  SAMA Report
   (11 PM)                                                              (7 AM)
```

Every layer in that chain has a specific purpose.
Using the wrong layer for the wrong job is one of the most
common and expensive data engineering mistakes in banking.

---

### What is the Staging Layer?

**In one sentence:** The staging layer is an exact, unmodified
copy of data as it arrived from the source system —
a permanent receipt that the data was received, and what it
looked like at the moment of receipt.

**The rule that governs staging:**

```
NOTHING IN STAGING IS EVER MODIFIED AFTER LANDING.

A staging record is written once.
It is never updated.
It is never deleted.

If the data needs to be cleaned, transformed, or corrected —
that happens in the ODS or beyond.
The staging copy remains exactly as it arrived.
```

**Why this rule exists — the banking scenario:**

```
At 2:00 AM, the Staging → ODS transformation runs.
It finds a transaction where txn_type = 'SI'.
The canonical value is 'SARIE_IN'.
The transformation writes 'SARIE_IN' to the ODS row
and stores 'SI' in the stg_source_value column for lineage.

Six months later, SAMA asks:
"What exactly did the CBS send you for transaction TXN-2024-0847?
Was it already classified as SARIE_IN at source,
or did your transformation apply that label?"

With staging preserved: point to the staging record.
Source value = 'SI'. Classification applied in ODS transformation.
Clean answer. Auditable.

Without staging: the original source value is gone.
The transformation overwrote it.
You cannot prove what the CBS actually sent.
That is a lineage gap. A SAMA finding.
```

**What staging looks like in the schema:**

```sql
CREATE TABLE staging.stg_transaction (
    stg_id          BIGSERIAL     PRIMARY KEY,
    source_system   VARCHAR(50),   -- 'FLEXCUBE', 'TEMENOS_T24'
    source_txn_id   VARCHAR(50),   -- the ID as the CBS assigned it
    raw_payload     JSONB,         -- exactly what arrived
    received_at     TIMESTAMPTZ,   -- when we received it
    batch_id        VARCHAR(30),   -- which load run this came from
    load_status     VARCHAR(20)    -- LOADED, FAILED, DUPLICATE
);
```

The raw_payload is the complete source record — unmodified.
Every transformation downstream is traceable back to this row.

---

### What is the ODS?

**ODS stands for Operational Data Store.**

**In one sentence:** The ODS is a cleaned, canonicalised,
near-current view of operational data — not for deep analysis,
but for operational questions that need to be answered
against data that is minutes to hours old.

**The ODS resolves what staging preserves:**

```
Staging says:   txn_type = 'SI'
ODS says:       txn_type = 'SARIE_IN'  (canonical value)

Staging says:   customer_id = '10042385'  (CBS internal ID)
ODS says:       customer_id = 'C000000001'  (CIF number — canonical)

Staging says:   amount = '50000' (string — CBS sent it as text)
ODS says:       amount_sar = 50000.00  (NUMERIC — correct type)
```

**The questions the ODS is designed to answer:**

```
→ Did this customer's payment clear today?  (operational)
→ How many SARIE transactions are currently in PROCESSING?  (operational)
→ Is this customer's KYC status currently VERIFIED?  (operational)
→ What is the last known balance for account ACC0000000000001?  (operational)
```

**The questions the ODS is NOT designed to answer:**

```
→ What is the 90-day NPF trend by customer segment?  (analytical — DWH)
→ What was the average Murabaha profit rate in Q3 2023?  (historical — DWH)
→ Generate the SAMA capital adequacy report for Q1 2025  (aggregated — DWH)
```

**ODS characteristics:**

```
┌─────────────────┬──────────────────────────────────────────┐
│ Freshness       │ Minutes to hours after source event      │
│ History depth   │ 30 to 90 days (rolling window)           │
│ Schema style    │ 3NF — normalised for writes and updates  │
│ Purpose         │ Operational reporting — current state    │
│ Who uses it     │ Operations, Customer Service, Compliance │
│ Query type      │ Single customer, single transaction      │
└─────────────────┴──────────────────────────────────────────┘
```

**The ODS is not the DWH. Confusing them is expensive:**

```
A Saudi bank — not named — gradually started running SAMA
capital adequacy calculations directly from the ODS
because the DWH load was slow.

The ODS has 90 days of history.
The CAR calculation requires 12 months of transaction data.
The calculation was silently running on incomplete data.
The error was caught during a SAMA examination — not before it.
```

---

### What is the DWH?

**DWH stands for Data Warehouse.**

**In one sentence:** The Data Warehouse is the permanent,
historical, analytical store — optimised for complex queries
across large datasets, structured for reporting, and designed
to answer questions the ODS cannot.

**DWH characteristics:**

```
┌─────────────────┬──────────────────────────────────────────┐
│ Freshness       │ Nightly batch (typically 02:00–06:00 AM) │
│ History depth   │ 10 years minimum (SAMA mandate)          │
│ Schema style    │ Star / Snowflake — denormalised for reads │
│ Purpose         │ Regulatory reporting, analytics, BI       │
│ Who uses it     │ Risk, Finance, Compliance, SAMA reporting │
│ Query type      │ Aggregations across millions of rows      │
└─────────────────┴──────────────────────────────────────────┘
```

**The DWH answers questions that need history:**

```
→ NPF ratio: which Murabaha contracts had instalments
  overdue > 90 days in Q1 2025?  (needs 90+ days of schedule data)

→ CAR report: what is the risk-weighted asset value
  of the entire financing book?  (needs all active contracts)

→ Trend: how has the average SIMAH score of approved applications
  changed over the last 24 months?  (needs 2 years of history)
```

**The ODS vs DWH decision in one rule:**

```
If the question starts with "currently" or "today" → ODS.
If the question starts with "over the last" or "trend" → DWH.
If the question feeds a SAMA regulatory submission → DWH.
```

---

## Part 2 — Schema Types for the Analytical Layer

The Data Warehouse does not use 3NF. It uses dimensional
modelling. Three patterns exist. Knowing when to use each
is a core data engineering skill.

---

### What is the Star Schema?

**In one sentence:** One central fact table surrounded by
dimension tables — the simplest, fastest analytical structure.

```
                    DIM_DATE
                       │
   DIM_CUSTOMER ────FACT_TRANSACTION──── DIM_PRODUCT
                       │
                    DIM_BRANCH

FACT_TRANSACTION contains:
  → Measurable events: amount_sar, txn_type, direction
  → Foreign keys to every dimension: date_id, customer_id,
    product_id, branch_id
  → Nothing else.

DIMENSION tables contain:
  → Descriptive context: who, what, when, where
  → All attributes in one flat table
  → No further joins required
```

**Why it is fast:**

Every analytical query needs at most one JOIN per dimension.
FACT → DIM_CUSTOMER → done. No chaining through sub-tables.
Pre-joined at load time. Read at query time.

**The Saudi banking addition — DIM_DATE must carry Hijri:**

```sql
CREATE TABLE analytics.dim_date (
    date_id       INTEGER PRIMARY KEY,  -- e.g. 20250315
    full_date     DATE,
    day_name      VARCHAR(20),
    month_name    VARCHAR(20),
    quarter       SMALLINT,
    year          SMALLINT,
    hijri_date    VARCHAR(20),           -- e.g. '1446-09-15'
    hijri_month   VARCHAR(20),
    hijri_year    SMALLINT,
    is_weekend_sa BOOLEAN               -- Friday + Saturday
);
```

SAMA submissions, Zakat calculations, and some regulatory
reporting reference Hijri dates. A date dimension without
Hijri forces runtime conversion on every report — slow and
error-prone. Store both.

**Best for:** Single subject area dashboards, SAMA regulatory
reports, branch sales reporting.

---

### What is the Snowflake Schema?

**In one sentence:** A Star Schema where the dimension tables
have been normalised — broken into sub-dimension tables
to eliminate redundancy.

**The problem it solves:**

```
In the Star Schema, DIM_CUSTOMER looks like this:

customer_id │ full_name │ segment │ segment_manager │ segment_min_balance
C000000001  │ Ahmed     │ PREMIUM │ Ibrahim Al-Saud │ 50,000
C000000002  │ Fatima    │ PREMIUM │ Ibrahim Al-Saud │ 50,000
C000000003  │ Khalid    │ PREMIUM │ Ibrahim Al-Saud │ 50,000

If Ibrahim Al-Saud is replaced as segment manager,
every PREMIUM customer row must be updated.
50,000 rows. Risk of partial update. Inconsistency possible.

In the Snowflake Schema:

DIM_CUSTOMER        →    DIM_CUSTOMER_SEGMENT
customer_id              segment_id
segment_id FK            segment_name
full_name                segment_manager
                         segment_min_balance

One update to DIM_CUSTOMER_SEGMENT propagates automatically.
```

**In Al-Noor Bank context:**

The product catalogue with Sharia compliance attributes is
the strongest use case. `ssb_approval_ref` applies to every
product in a category. Changing it requires updating one row
in DIM_PRODUCT_CATEGORY — not every product row.

**The trade-off:**

```
More joins per query → slower on row-based databases.
On columnar databases (Snowflake the platform, Redshift,
BigQuery) the performance difference is smaller because
columnar compression handles wide multi-join queries well.
```

**Best for:** Large dimension tables with repeated reference
data that changes — product categories, customer segments,
branch hierarchies.

---

### What is the Galaxy Schema?

**In one sentence:** Multiple fact tables sharing the same
dimension tables — the natural structure of a full enterprise
data warehouse.

```
                    DIM_DATE
                   /         \
FACT_TRANSACTION              FACT_MURABAHA_SCHEDULE
                   \         /
                  DIM_CUSTOMER
                   \         /
FACT_AML_ALERT ─── DIM_PRODUCT

Three fact tables. Shared dimensions. No duplication.
```

**Why shared dimensions matter:**

```
Without shared dimensions:

DIM_CUSTOMER_TRANSACTIONS  (one definition)
DIM_CUSTOMER_MURABAHA      (a different definition)

A query crossing both fact tables joins two different
definitions of the same customer.
Results do not reconcile.
SAMA asks why the customer count in the transaction report
does not match the customer count in the NPF report.
There is no clean answer.

With shared dimensions:

One DIM_CUSTOMER. One definition.
Every fact table references the same customer record.
Cross-domain queries always reconcile.
```

**Best for:** Enterprise data warehouses serving multiple
business domains simultaneously — transactions, Islamic
finance, credit risk, compliance — all in one warehouse.

**The progression:**

```
Start with Star Schema (single subject area).
Add Snowflake when a dimension becomes too large and repetitive.
Move to Galaxy when multiple subject areas need to share dimensions.
```

---

## Part 3 — How NoSQL Fits Into the Architecture

---

### What is NoSQL and Why Does It Exist?

NoSQL is not a replacement for relational databases.
It is a category of databases designed for specific problems
that relational databases solve poorly.

**The three problems NoSQL solves:**

```
PROBLEM 1: THE SPARSE ATTRIBUTE PROBLEM
  Al-Noor Bank serves individuals and corporates.
  Individuals have a national_id, date_of_birth, monthly_income.
  Corporates have commercial_reg_no, gosi_id, vat_number.

  In a relational table: every individual row has NULL in
  the corporate columns. Every corporate row has NULL in the
  individual columns. In a large table, this is expensive.

  In a document database (MongoDB):
  Each customer document contains only the attributes that
  apply to that customer. No NULLs. No wasted storage.

PROBLEM 2: THE NESTED DATA PROBLEM
  A KYC document for Al-Noor Bank contains:
  identity details, verification results, document scans,
  audit trail, compliance notes, reviewer comments.

  In a relational database: seven tables, multiple JOINs.
  In a document database: one document. Everything together.
  Reads are a single fetch. No joins. Faster.

PROBLEM 3: THE WRITE THROUGHPUT PROBLEM
  100,000 payment events per minute during Eid al-Adha peak.
  A single RDBMS instance cannot handle writes at that rate.
  A distributed key-value store or time-series store can.
```

---

### The CAP Theorem — What It Is and Why It Matters

The CAP Theorem states that in a distributed database system,
you can guarantee at most **two** of the following three
properties simultaneously. Never all three.

```
C — CONSISTENCY
    Every read receives the most recent write or an error.
    All nodes see the same data at the same time.

A — AVAILABILITY
    Every request receives a response (not necessarily
    the most recent data).
    The system is always operational.

P — PARTITION TOLERANCE
    The system continues to operate even when network
    communication between nodes is lost.
```

**In a real distributed system, P is not optional.**
Networks fail. Packets are dropped. Partitions happen.
Every distributed database must tolerate network partitions.
The real choice is between C and A when a partition occurs.

**What this means in practice:**

```
CP — Consistency + Partition Tolerance
   When a partition occurs, the system becomes unavailable
   rather than return stale data.
   Examples: HBase, MongoDB (strong consistency mode),
             traditional RDBMS in cluster mode.
   Al-Noor use: Murabaha contract writes. Account balance
   updates. Financial data where stale reads are dangerous.

AP — Availability + Partition Tolerance
   When a partition occurs, the system stays available but
   may return stale data.
   Examples: Cassandra, CouchDB, DynamoDB.
   Al-Noor use: Customer profile cache. Product catalogue
   serving. OTP delivery logs. Data where brief staleness
   is acceptable.
```

**The banking application of CAP:**

```
A Murabaha contract is CP territory.
A customer's account balance must be consistent.
If the system cannot guarantee consistency, it must return
an error — not a potentially wrong balance.
Approving financing against a stale balance is a risk event.

A customer's profile photo in the mobile app is AP territory.
If the profile picture is 30 seconds stale, the customer
does not notice and no harm occurs.
Availability matters more than instant consistency here.

CAP forces you to classify your data explicitly:
what requires strong consistency, what tolerates eventual.
```

---

### ACID vs BASE — The Consistency Models

These are not technologies. They are **property guarantees**
that different databases make about their data.

---

#### ACID — What It Means

```
A — ATOMICITY
    A transaction is all or nothing.
    A Murabaha contract write either creates the contract
    AND the 240 schedule rows AND updates the quota counter,
    or none of it happens.
    Partial writes do not exist.

C — CONSISTENCY
    A transaction takes the database from one valid state
    to another valid state.
    The CHECK constraint total_sale_price = cost + profit
    is never violated — not even momentarily.
    If the values do not add up, the transaction is rejected.

I — ISOLATION
    Concurrent transactions do not interfere with each other.
    Transaction A reading a balance while Transaction B
    is updating it sees a consistent view — either the
    balance before the update or after. Never in the middle.

D — DURABILITY
    Once committed, a transaction survives any subsequent failure.
    A power cut immediately after COMMIT does not lose the data.
    The write is on disk. It persists.
```

**ACID is non-negotiable for:**

```
→ Account balance updates
→ Murabaha contract creation and schedule generation
→ Payment status transitions
→ Inventory quota increments on FULFILLED
→ Any write where "partial completion" is a regulatory disaster
```

---

#### BASE — What It Means

```
BA — BASICALLY AVAILABLE
     The system guarantees availability — it responds to requests.
     The response may not reflect the latest write.

S  — SOFT STATE
     The state of the system may change over time
     even without new input — as eventual consistency
     propagates across nodes.

E  — EVENTUALLY CONSISTENT
     Given enough time and no new updates, all replicas
     will converge to the same value.
     "Eventually" may mean milliseconds or seconds —
     not hours or days in a well-designed system.
```

**BASE is acceptable for:**

```
→ Customer OTP tokens (Redis) — 30-second TTL, brief staleness fine
→ Product catalogue cache — 5-minute cache, stale rate harmless
→ Kafka event queue — messages delivered at least once, reprocessable
→ Customer interaction history in MongoDB — reading yesterday's
  chat history 500ms stale is not a risk event
→ API rate limiter counters — brief over-counting is acceptable
```

**BASE is NEVER acceptable for:**

```
→ Account balances
→ Murabaha contract terms
→ Regulatory report figures
→ Application approval decisions
→ Quota enforcement counts
→ Payment amounts
```

**The practical decision framework:**

```
Before choosing a database technology, classify the data:

  Could a brief period of stale data cause:
  → A financial loss?          → ACID required
  → A regulatory violation?    → ACID required
  → A contract dispute?        → ACID required
  → A minor UX inconvenience?  → BASE acceptable
  → No noticeable impact?      → BASE acceptable

If you are unsure which category your data falls into,
default to ACID. The cost of wrong consistency is
always higher than the cost of unnecessary consistency.
```

---

## Part 4 — How NoSQL Sits in the Data Architecture

---

### The Four-Layer Model — Where Each Database Lives

```
LAYER 4 — SEMANTIC
  BI Tools, SAMA dashboards, APIs, Open Banking portal
  No database here — reads from Layer 3.

LAYER 3 — ANALYTICAL
  Snowflake (DWH) — Star/Galaxy schema — ACID
  10 years of transaction history.
  SAMA regulatory reports sourced here.

LAYER 2 — INTEGRATION
  PostgreSQL (ODS) — 3NF — ACID
    → Canonical operational data, 30–90 day window
  MongoDB (Document Store) — BASE/AP
    → KYC documents, customer profiles, event logs
  Redis (Cache) — BASE/AP volatile
    → OTP tokens, session state, API rate limiters
  Kafka (Event Stream) — AT LEAST ONCE delivery
    → Real-time CDC from CBS, payment events, AML feeds

LAYER 1 — OPERATIONAL (Source Systems)
  Core Banking System (T24 / FLEXCUBE) — ACID
  KYC Platform — ACID for verification records
  Payment Hub — ACID for payment records
```

**The rule: match the database to the workload, not to familiarity.**

---

### When to Choose RDBMS (PostgreSQL)

```
CHOOSE RDBMS WHEN:

→ The data has a well-defined, stable schema
  Customer identity columns do not change unpredictably.
  Payment attributes are known in advance.

→ The data requires referential integrity across entities
  A payment must reference a valid account.
  An application must reference a valid customer and product.
  Foreign keys enforce this — MongoDB cannot.

→ The data requires ACID transactions across multiple tables
  FULFILLED: update application + create account + update quota
  All or nothing. One transaction. RDBMS.

→ The data feeds SAMA regulatory reports
  The report figure must be traceable to a source transaction.
  That traceability is enforced by the relational schema.

→ Complex queries join many entities
  NPF ratio: joins contract, schedule, customer, product.
  RDBMS with proper indexes handles this correctly.

→ Compliance and audit requirements are strict
  Immutability triggers. CHECK constraints. Audit history.
  These are RDBMS-native capabilities.

AL-NOOR EXAMPLES:
  retail.customer       → RDBMS (identity, referential integrity)
  retail.account        → RDBMS (balance, ACID transactions)
  orders_domain.*       → RDBMS (application lifecycle, immutable history)
  payments.payment      → RDBMS (financial transaction, ACID)
  analytics.fact_*      → RDBMS / Snowflake (DWH)
```

---

### When to Choose NoSQL (MongoDB, Redis, Kafka)

```
CHOOSE MONGODB WHEN:

→ The schema varies significantly between records
  A corporate customer document looks very different
  from an individual customer document.
  Fields that apply to one do not apply to the other.

→ The data is naturally hierarchical or nested
  A KYC record has sub-documents: verification results,
  document references, reviewer notes, audit trail.
  Storing this in MongoDB avoids six relational tables.

→ Documents are read as a whole unit most of the time
  Fetch the complete customer profile in one query.
  Not a JOIN across five tables.

→ The schema evolves rapidly during product development
  A new field can be added to new documents without
  a schema migration that locks a 50M-row table.

→ Write patterns are high-volume and schema-inconsistent
  Customer interaction logs, mobile app event streams,
  clickstream data — every event has different attributes.

AL-NOOR EXAMPLES:
  Customer profile documents (individual + corporate in one collection)
  KYC document store (verification payloads, scan references)
  Customer interaction history (chat logs, call notes)
  Audit event logs (platform-level events with variable schema)

────────────────────────────────────────────────────────────────

CHOOSE REDIS WHEN:

→ The data is ephemeral — it has a defined lifetime
  OTP tokens: valid for 5 minutes. DELETE after use.
  Session tokens: valid for 30 minutes. AUTO-EXPIRE.

→ Sub-millisecond read latency is required
  An API rate limiter that runs on every request
  cannot afford a PostgreSQL query on every call.
  Redis reads in microseconds.

→ The data can tolerate loss on failure
  If Redis crashes and OTP tokens are lost,
  customers re-request new tokens. Annoying. Not dangerous.
  Never store Murabaha contract terms in Redis.

→ Simple data structures — keys, counters, queues
  idempotency:PMT-2025-0042 → "processed"
  rate_limit:C000000001:API → counter

AL-NOOR EXAMPLES:
  OTP tokens for digital onboarding verification
  Payment idempotency keys (prevent duplicate SARIE submissions)
  API rate limiters for SAMA Open Banking endpoints
  Session state for the mobile banking app

────────────────────────────────────────────────────────────────

CHOOSE KAFKA WHEN:

→ Data moves between systems in real time
  A CBS transaction must reach the AML system in < 500ms.
  A batch ETL job running every hour cannot achieve this.

→ Multiple consumers need the same event
  One payment event consumed by:
  → The ODS (for operational reporting)
  → The AML system (for fraud detection)
  → The notification service (for customer SMS)
  → The DWH pipeline (for analytics)
  Kafka delivers it to all four simultaneously.

→ Write volume exceeds what a single RDBMS can absorb
  100,000 events per minute at peak.
  Kafka buffers them and delivers at the rate consumers
  can process.

→ The producing system and consuming system must be decoupled
  The CBS does not need to know the ODS exists.
  It publishes to a Kafka topic. The ODS subscribes.

AL-NOOR EXAMPLES:
  CBS transaction feed → ODS staging
  Payment completion events → Notification service + AML
  Application status changes → Audit log + Customer comms
  Real-time balance updates → Customer mobile app
```

---

### The Polyglot Architecture — All Together

```
                    AL-NOOR DIGITAL RETAIL PLATFORM
                                │
                    ┌───────────┴────────────┐
                    │    CORE BANKING SYSTEM │
                    │    (T24 / FLEXCUBE)    │
                    └───────────┬────────────┘
                                │
                    Kafka CDC stream (real-time)
                    + nightly batch extract
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
    PostgreSQL ODS         MongoDB                 Redis
    (ACID)                 (BASE/AP)               (volatile)
                                                   
    Canonical data         KYC documents           OTP tokens
    Customer identity      Customer profiles       Session state
    Payment records        Interaction history     Rate limiters
    Application audit      Audit event logs        Idempotency keys
    trail
          │
          │ nightly ELT (Airflow + dbt)
          ▼
    Snowflake DWH
    (ACID on columnar)

    Star / Galaxy schema
    SAMA regulatory reports
    NPF ratio · CAR · LCR
    10-year transaction history
```

**The rule for Al-Noor Bank:**

```
Financial data — account balances, contract terms,
payment amounts, application decisions → PostgreSQL (ACID).

Operational supporting data — profile documents, event logs,
interaction history → MongoDB (BASE, acceptable staleness).

Ephemeral data — tokens, counters, session state → Redis.

Events in motion — real-time feeds between systems → Kafka.

Historical analytical data — SAMA reports, trends, DWH → Snowflake.

No single database serves all five purposes well.
The right architecture uses the right tool for each job.
```

---

## Part 5 — Quick Reference: Everything on One Page

```
┌──────────────────┬────────────────┬───────────────────────────────┐
│ Concept          │ One Line       │ Al-Noor Example               │
├──────────────────┼────────────────┼───────────────────────────────┤
│ Staging          │ Raw receipt    │ stg_transaction — unmodified  │
│                  │ of source data │ CBS payload, never changed    │
├──────────────────┼────────────────┼───────────────────────────────┤
│ ODS              │ Clean current  │ ods_transaction — canonical   │
│                  │ operational    │ types, 90-day window          │
│                  │ view           │                               │
├──────────────────┼────────────────┼───────────────────────────────┤
│ DWH              │ Historical     │ Snowflake — 10-year history   │
│                  │ analytical     │ SAMA CAR, NPF reports         │
│                  │ store          │                               │
├──────────────────┼────────────────┼───────────────────────────────┤
│ Star Schema      │ Fact table     │ FACT_TRANSACTION surrounded   │
│                  │ + flat dims    │ by DIM_DATE, DIM_CUSTOMER     │
├──────────────────┼────────────────┼───────────────────────────────┤
│ Snowflake Schema │ Star with      │ DIM_PRODUCT →                 │
│                  │ normalised     │ DIM_PRODUCT_CATEGORY          │
│                  │ sub-dimensions │ (SSB approval ref centralised)│
├──────────────────┼────────────────┼───────────────────────────────┤
│ Galaxy Schema    │ Multiple facts │ FACT_TRANSACTION +            │
│                  │ sharing dims   │ FACT_MURABAHA +               │
│                  │                │ FACT_AML_ALERT                │
│                  │                │ all sharing DIM_CUSTOMER      │
├──────────────────┼────────────────┼───────────────────────────────┤
│ CAP Theorem      │ Choose 2 of 3: │ Account balance → CP          │
│                  │ Consistency,   │ (must be consistent)          │
│                  │ Availability,  │ Profile cache → AP            │
│                  │ Partition tol. │ (availability preferred)      │
├──────────────────┼────────────────┼───────────────────────────────┤
│ ACID             │ All or nothing,│ Murabaha contract creation    │
│                  │ consistent,    │ Payment FULFILLED transaction  │
│                  │ isolated,      │ Quota counter increment       │
│                  │ durable        │                               │
├──────────────────┼────────────────┼───────────────────────────────┤
│ BASE             │ Basically      │ OTP token in Redis            │
│                  │ available,     │ Customer profile in MongoDB   │
│                  │ eventually     │ Product catalogue cache       │
│                  │ consistent     │                               │
├──────────────────┼────────────────┼───────────────────────────────┤
│ RDBMS            │ Choose when    │ PostgreSQL for all financial  │
│ (PostgreSQL)     │ schema stable, │ data — accounts, contracts,   │
│                  │ ACID needed,   │ payments, applications        │
│                  │ FK integrity   │                               │
├──────────────────┼────────────────┼───────────────────────────────┤
│ MongoDB          │ Choose when    │ KYC documents, customer       │
│                  │ schema varies, │ profiles, interaction logs    │
│                  │ docs nested,   │                               │
│                  │ writes fast    │                               │
├──────────────────┼────────────────┼───────────────────────────────┤
│ Redis            │ Choose when    │ OTP tokens, session state,    │
│                  │ ephemeral,     │ idempotency keys,             │
│                  │ microsecond    │ API rate limiters             │
│                  │ latency needed │                               │
├──────────────────┼────────────────┼───────────────────────────────┤
│ Kafka            │ Choose when    │ CBS → ODS real-time feed      │
│                  │ real-time,     │ Payment events → AML          │
│                  │ multi-consumer,│ Application events →          │
│                  │ decoupled      │ Notification service          │
└──────────────────┴────────────────┴───────────────────────────────┘
```

---

> **The central principle of Day 6:**
>
> No single database technology solves every data problem well.
> The skill is not knowing how to use each tool in isolation.
> The skill is knowing which tool to choose for which data,
> and being able to defend that choice when challenged —
> by a colleague, by a vendor, or by a SAMA examiner
> asking why your regulatory report is sourced from
> a MongoDB collection instead of a relational fact table.
>
> Every technology choice is a trade-off.
> The architect's job is to make the trade-off explicit,
> document it, and own the consequences.

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*