### Lab 1A — Architecture Review (45 minutes)
 
**The eight systems:**
 
| System | Layer | Reasoning |
|---|---|---|
| FLEX-CBS (Oracle FLEXCUBE) | Layer 1 — Operational | Core banking, OLTP, vendor-controlled schema |
| CRM-360 (Salesforce) | Layer 1 — Operational | Customer engagement system, operational write workload |
| PayHub (In-house payment processing) | Layer 1/2 boundary | Operational for payment processing, but may expose integration APIs — discuss whether it acts as both source and integration hub |
| AML-Guard (NICE Actimize) | Layer 1/2 boundary | Operational for alert generation, but analytically complex — many implementations read from Layer 2 to avoid CBS load |
| RiskCalc (SAS) | Layer 3 — Analytical | Risk analytics reads from DWH, not CBS — should not query Layer 1 directly. If it does, that is the governance risk to identify |
| BranchBI (MicroStrategy) | Layer 4 — Semantic | Reporting and visualisation tool |
| DataLake-S3 (AWS S3) | Layer 2/3 spanning | Raw zone = Integration Layer. Curated zone = Analytical Layer. Three-zone pattern is intentional |
| EDW-Teradata | Layer 3 — Analytical | Enterprise data warehouse |
 
**Task 2 — Governance risks to identify (at least two; here are the strongest answers):**
 
1. **RiskCalc querying CBS directly**: If RiskCalc reads from FLEX-CBS rather than from the EDW, it is creating load on a transactional system and producing risk calculations that bypass the governed, quality-assured data in Layer 3. This is both a performance risk and a data quality risk — CBS data is not cleansed or conformed.
 
2. **No canonical customer record**: If CRM-360 and FLEX-CBS hold separate customer records with no synchronisation mechanism, the institution has two definitions of CUSTOMER. Any report joining customer attributes across the two systems will produce inconsistent results. Open Banking consent management will also break — you cannot link a consent to a customer if you do not have a single authoritative customer identifier.
 
3. **DataLake-S3 without zone separation**: If the S3 bucket does not enforce Raw/Cleansed/Curated zone separation, analysts may be querying raw, unvalidated data and treating it as if it were curated. PDPL classification also becomes impossible to enforce without zone-level access controls.
 
**Task 3 — SADAD Payment to SAMA Liquidity Report data flow (the correct sequence):**
 
> PayHub records SADAD transaction → Kafka CDC stream (Debezium) captures change event → Staging DB receives raw copy with capture_ts → ODS standardises to canonical payment model → Data Lake Cleansed zone → dbt transformation to Liquidity Fact Table in EDW-Teradata → SAMA Weekly Liquidity Report reads from EDW via BranchBI
 
**Task 4 — PDPL improvement examples (any architecturally justified answer is valid):**
 
- Column-level masking on PII columns (NID, DOB, account numbers) in EDW-Teradata for non-production access
- Automated retention policy enforcement on the S3 raw zone with object lifecycle rules
- PDPL classification tags on every S3 object at landing time (Public/Internal/Confidential/Restricted)
- Consent management table in FLEX-CBS or CRM-360 linked to customer records, referenced by the Open Banking API layer


### Lab 1B — Conceptual Model Design (45 minutes)
 
**Target ERD (entities and relationships):**
 
```
CUSTOMER 🔒 ←——— CUSTOMER_ACCOUNT (bridge) ———→ ACCOUNT
                                                      |
                                              TRANSACTION
                                                      |
                                               PAYMENT
                                                      |
BRANCH ←——— ACCOUNT                          MURABAHA_CONTRACT 🔒
                                                      |
KYC_RECORD 🔒 ——— CUSTOMER 🔒          CREDIT_FACILITY (if using subtype)
```
 
**Entity relationships with cardinality:**
 
- CUSTOMER to ACCOUNT: many-to-many (joint accounts) → resolved via CUSTOMER_ACCOUNT bridge
  - CUSTOMER_ACCOUNT attributes: relationship_type, linked_at, is_primary_holder, is_active
- ACCOUNT to TRANSACTION: one-to-many
- ACCOUNT to BRANCH: many-to-one (account belongs to one branch, branch has many accounts)
- TRANSACTION to PAYMENT: one-to-one or one-to-many depending on payment type
- CUSTOMER to KYC_RECORD: one-to-many (KYC checks are point-in-time, customer has history)
- MURABAHA_CONTRACT: can be standalone or subtype of CREDIT_FACILITY
 
**🔒 PDPL-sensitive entities:** CUSTOMER, KYC_RECORD, MURABAHA_CONTRACT (contains NID, financial terms linked to individual)
 
**Three review criteria debrief:**
 
**1. CUSTOMER vs ACCOUNT separation:**
*"The most common error is collapsing these into one entity — CUSTOMER_ACCOUNT. The problem: a customer exists before they open an account. They exist after they close one. A customer who is a prospect in the CRM but has no account yet has no representation in a collapsed model. Separate these always."*
 
**2. MURABAHA_CONTRACT modelling:**
*"Two valid approaches. Standalone entity: simpler queries, but adding Tawarruq or Ijara later requires new tables and new relationships. Subtype of CREDIT_FACILITY: extensible — Tawarruq is just another subtype — but joins are more complex. There is no wrong answer. The architecture must document the decision and the reasoning. What matters is that the decision is explicit, not accidental."*
 
**3. Joint account many-to-many:**
*"CUSTOMER to ACCOUNT is many-to-many because of joint accounts. A husband and wife share an account — two customers, one account. A single customer may hold multiple accounts — one customer, many accounts. The bridge entity CUSTOMER_ACCOUNT is mandatory. It should carry at minimum: relationship_type (primary/joint/authorised signatory), linked_at timestamp, is_active flag."*


# Normalisation vs Denormalisation
## A Simple Guide with Everyday Examples

---

## What is Normalisation?

Normalisation is the process of organising a database to **reduce repetition** and **prevent data problems**.

Think of it like organising your wardrobe.

> If you throw everything into one drawer — socks, shirts, trousers — you can find things eventually. But when you need to update something (move your winter clothes out), you have to search through everything. A organised wardrobe with separate sections for each type of clothing is faster, cleaner, and easier to maintain.

Normalisation does the same thing for your database tables.

---

## What Problems Does It Solve?

When data is not normalised, three types of problems appear:

**Insert Anomaly** — you cannot add data without adding something else first.
> You want to add a new product to the system but cannot because no customer has ordered it yet.

**Update Anomaly** — changing one fact requires updating many rows.
> A supplier changes their phone number. It is stored in 400 order rows. You update 300 and miss 100. Now your data is inconsistent.

**Delete Anomaly** — deleting one thing accidentally removes something else.
> You delete the last order for a customer. Their address disappears from the system entirely because it was only stored on the order row.

---

## The Three Normal Forms

---

### First Normal Form — 1NF
**Rule: Every column must hold one single value. No lists, no groups.**

#### Violation Example

Imagine a simple order table:

| order_id | customer_name | products_ordered |
|---|---|---|
| 1001 | Sarah | Pen, Notebook, Ruler |
| 1002 | James | Laptop |
| 1003 | Aisha | Phone, Case, Charger |

**The problem:**
products_ordered contains multiple values in one column.
You cannot answer "how many orders included a Notebook?" without reading and parsing every single row manually. You also cannot sort, filter, or index this column properly.

#### Fixed — In 1NF

Split the multi-value column into separate rows:

| order_id | customer_name | product |
|---|---|---|
| 1001 | Sarah | Pen |
| 1001 | Sarah | Notebook |
| 1001 | Sarah | Ruler |
| 1002 | James | Laptop |
| 1003 | Aisha | Phone |
| 1003 | Aisha | Case |
| 1003 | Aisha | Charger |

Now every column holds exactly one value. You can query, sort, and filter cleanly.

**Simple definition:**
> 1NF = One value per cell. No comma-separated lists. No repeating groups.

---

### Second Normal Form — 2NF
**Rule: Every non-key column must depend on the WHOLE primary key — not just part of it.**

This only matters when you have a **composite primary key** (two or more columns together forming the key).

#### Violation Example

A school exam results table with a composite key of (student_id + subject_id):

| student_id | subject_id | student_name | teacher_name | score |
|---|---|---|---|---|
| S01 | MATH | Sarah | Mr Ahmed | 88 |
| S01 | ENG | Sarah | Ms Fatima | 76 |
| S02 | MATH | James | Mr Ahmed | 91 |
| S02 | ENG | James | Ms Fatima | 83 |

**The problem:**
- student_name depends only on student_id — not on the full key
- teacher_name depends only on subject_id — not on the full key

If Sarah changes her name, you update multiple rows.
If Mr Ahmed is replaced, you update multiple rows.
These are **partial dependencies** — they violate 2NF.

#### Fixed — In 2NF

Break into three tables:

**STUDENTS**
| student_id | student_name |
|---|---|
| S01 | Sarah |
| S02 | James |

**SUBJECTS**
| subject_id | teacher_name |
|---|---|
| MATH | Mr Ahmed |
| ENG | Ms Fatima |

**EXAM_RESULTS**
| student_id | subject_id | score |
|---|---|---|
| S01 | MATH | 88 |
| S01 | ENG | 76 |
| S02 | MATH | 91 |
| S02 | ENG | 83 |

Now student_name lives in one place. Teacher_name lives in one place. One update, no inconsistency.

**Simple definition:**
> 2NF = Every column depends on the full primary key — not just half of it.

---

### Third Normal Form — 3NF
**Rule: Non-key columns must depend ONLY on the primary key — not on each other.**

If Column A determines Column B, and Column B determines Column C — then C does not belong in this table. That is called a **transitive dependency**.

#### Violation Example

An employee table:

| employee_id | employee_name | department_id | department_name | department_floor |
|---|---|---|---|---|
| E01 | Sarah | D01 | Marketing | Floor 3 |
| E02 | James | D01 | Marketing | Floor 3 |
| E03 | Aisha | D02 | Finance | Floor 7 |
| E04 | Khalid | D02 | Finance | Floor 7 |

**The problem:**
- department_name depends on department_id — not directly on employee_id
- department_floor depends on department_id — not directly on employee_id

The chain is: employee_id → department_id → department_name → department_floor

This is a transitive dependency. If Marketing moves to Floor 5, you update every employee row in that department. Miss one row and the data is inconsistent.

#### Fixed — In 3NF

Break into two tables:

**EMPLOYEES**
| employee_id | employee_name | department_id |
|---|---|---|
| E01 | Sarah | D01 |
| E02 | James | D01 |
| E03 | Aisha | D02 |
| E04 | Khalid | D02 |

**DEPARTMENTS**
| department_id | department_name | department_floor |
|---|---|---|
| D01 | Marketing | Floor 3 |
| D02 | Finance | Floor 7 |

Now if Marketing moves floors, you update one row in DEPARTMENTS. Done.

**Simple definition:**
> 3NF = Columns depend on the key, the whole key, and nothing but the key.

---

## Quick Summary — All Three Normal Forms

| Normal Form | The Rule | The Problem It Solves |
|---|---|---|
| 1NF | One value per cell | Multi-value columns that cannot be queried cleanly |
| 2NF | Depend on the whole key | Partial dependencies in composite key tables |
| 3NF | Depend only on the key | Transitive dependencies between non-key columns |

---

## What is Denormalisation?

Denormalisation is the **deliberate reversal** of normalisation for performance reasons.

You take a normalised structure and intentionally introduce some redundancy to make queries faster.

> Think of it like a cheat sheet. Instead of going back to your textbook every time you need a formula, you write the most used formulas on a single piece of paper. The information exists in two places now — but you reach the answer much faster.

---

## Normalisation vs Denormalisation — When to Use Each

| Situation | Use | Why |
|---|---|---|
| You write data frequently | Normalisation | Fewer places to update means fewer errors |
| You read data frequently | Denormalisation | Pre-joined data means faster queries |
| Data accuracy is critical | Normalisation | One source of truth |
| Report speed is critical | Denormalisation | Pre-aggregated data responds instantly |
| Storage is a constraint | Normalisation | Less redundancy means less storage |
| Query simplicity matters | Denormalisation | Fewer joins means simpler queries |

---

## Side-by-Side Example

### The Scenario

An online store wants to show an order summary:
- Customer name
- Product name
- Quantity
- Price paid

---

### Normalised Version — Three Tables

**CUSTOMERS**
| customer_id | customer_name |
|---|---|
| C01 | Sarah |

**PRODUCTS**
| product_id | product_name | price |
|---|---|---|
| P01 | Notebook | 15.00 |

**ORDERS**
| order_id | customer_id | product_id | quantity | unit_price |
|---|---|---|---|---|
| 1001 | C01 | P01 | 2 | 15.00 |

**To show the order summary you need a JOIN:**
```sql
SELECT
  c.customer_name,
  p.product_name,
  o.quantity,
  o.unit_price
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products p ON o.product_id = p.product_id
WHERE o.order_id = 1001;
```

Clean. No redundancy. But requires joining three tables every time.

---

### Denormalised Version — One Table

**ORDER_SUMMARY**
| order_id | customer_name | product_name | quantity | unit_price |
|---|---|---|---|---|
| 1001 | Sarah | Notebook | 2 | 15.00 |

**The same query now:**
```sql
SELECT customer_name, product_name, quantity, unit_price
FROM order_summary
WHERE order_id = 1001;
```

One table. No joins. Instant.

**The trade-off:**
If Sarah changes her name, you update every row in ORDER_SUMMARY where she appears. In the normalised version, you update one row in CUSTOMERS and it reflects everywhere automatically.

---

## The Golden Rule

> **Normalise where data is written frequently.**
> **Denormalise where data is read frequently.**

These are not opposing philosophies. They are the right tool at the right layer.

A well-designed system normalises its operational data — where transactions happen — and denormalises its analytical data — where reports are generated.

---

## One Line to Remember Each

| Concept | One Line |
|---|---|
| 1NF | One value per cell — no lists |
| 2NF | Depend on the whole key — not half of it |
| 3NF | Depend only on the key — nothing else |
| Normalisation | Organise to reduce repetition |
| Denormalisation | Deliberately repeat for speed |



# Understanding Database Indexes
## A Visual and Simple Guide for Data Engineers

---

## What is an Index?

An index is a **separate data structure** that the database maintains
alongside your table to make searches faster.

Without an index, the database reads **every single row** to find
what you are looking for.

With an index, the database **jumps directly** to the relevant rows.

---

## The Phonebook Analogy

Imagine you want to find the phone number for **Ahmed Al-Omari**.

### Without an Index
```
Read page 1...   not Ahmed
Read page 2...   not Ahmed
Read page 3...   not Ahmed
...
Read page 847... FOUND Ahmed Al-Omari → +966501234567
```
You read 847 pages to find one person.
This is called a **Sequential Scan** — the worst thing you can see
in EXPLAIN ANALYZE on a large table.

### With an Index
```
Go to letter A
Go to Al-
Go to Al-Omari
FOUND Ahmed Al-Omari → page 847
Jump directly to page 847
```
You found the answer in seconds regardless of how many pages exist.

---

## What Happens Without an Index

```
TRANSACTION TABLE — 500 million rows

┌──────────┬────────────┬────────────┬────────────┐
│  txn_id  │ account_id │  txn_date  │ amount_sar │
├──────────┼────────────┼────────────┼────────────┤
│        1 │ ACC000001  │ 2025-01-01 │    1500.00 │  ← read
│        2 │ ACC000087  │ 2025-01-01 │    3200.00 │  ← read
│        3 │ ACC000001  │ 2025-01-02 │     450.00 │  ← read
│        4 │ ACC000234  │ 2025-01-02 │   15000.00 │  ← read
│      ... │    ...     │    ...     │        ... │  ← read
│500000000 │ ACC000001  │ 2025-12-31 │    3750.00 │  ← read
└──────────┴────────────┴────────────┴────────────┘

Query: SELECT * FROM transaction WHERE account_id = 'ACC000001'

Result: Database reads ALL 500 million rows
        Time: minutes
        EXPLAIN ANALYZE shows: Seq Scan
```

---

## What Happens With an Index

```
INDEX on account_id — sorted, separate structure

┌────────────┬─────────────────┐
│ account_id │  row locations  │
├────────────┼─────────────────┤
│ ACC000001  │ rows 1, 3, ...  │  ← jump here
│ ACC000087  │ row 2           │
│ ACC000234  │ row 4           │
│    ...     │    ...          │
└────────────┴─────────────────┘

Query: SELECT * FROM transaction WHERE account_id = 'ACC000001'

Result: Database looks up ACC000001 in the index
        Jumps directly to rows 1, 3, and relevant rows
        Time: milliseconds
        EXPLAIN ANALYZE shows: Index Scan
```

---

## How to Create an Index

```sql
-- Basic syntax
CREATE INDEX index_name
ON table_name (column_name);

-- Real example for Al-Noor Bank
CREATE INDEX idx_txn_account
ON retail.transaction (account_id);
```

---

## Types of Indexes — With Examples

---

### Type 1 — Single Column Index

The simplest index. Built on one column.

```sql
CREATE INDEX idx_customer_risk
ON retail.customer (risk_rating);
```

**Serves this query:**
```sql
-- Find all high-risk customers
SELECT customer_id, full_name_en
FROM retail.customer
WHERE risk_rating = 'H';
```

**Visual:**
```
CUSTOMER TABLE                    INDEX on risk_rating
┌─────────────┬─────────────┐     ┌─────────────┬───────────┐
│ customer_id │ risk_rating │     │ risk_rating │ row ptr   │
├─────────────┼─────────────┤     ├─────────────┼───────────┤
│ C000000001  │      L      │     │      H      │ rows 3, 7 │ ←
│ C000000002  │      M      │     │      L      │ rows 1, 5 │
│ C000000003  │      H      │     │      M      │ rows 2, 6 │
│ C000000004  │      L      │     └─────────────┴───────────┘
│ C000000005  │      M      │
│ C000000006  │      M      │     Query for H? Jump to rows 3 and 7.
│ C000000007  │      H      │     No need to read rows 1, 2, 4, 5, 6.
└─────────────┴─────────────┘
```

**Limitation:** Only helps when you filter on risk_rating alone.
If you also filter on a date, this index cannot help with the
date filter.

---

### Type 2 — Composite Index

Built on **two or more columns together**. Serves queries that
filter on multiple columns simultaneously.

```sql
CREATE INDEX idx_txn_account_date
ON retail.transaction (account_id, txn_date DESC);
```

**Serves this query:**
```sql
-- Account statement — most common banking query
SELECT txn_date, txn_type, amount_sar, direction
FROM retail.transaction
WHERE account_id = 'ACC0000000000001'
  AND txn_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY txn_date DESC;
```

**Visual:**
```
INDEX on (account_id, txn_date DESC)

┌────────────────┬────────────┬──────────┐
│   account_id   │  txn_date  │  row ptr │
├────────────────┼────────────┼──────────┤
│ ACC0000000001  │ 2025-03-10 │  row 847 │ ← start here
│ ACC0000000001  │ 2025-03-01 │  row 712 │ ← read this
│ ACC0000000001  │ 2025-02-15 │  row 634 │ ← read this
│ ACC0000000001  │ 2025-02-01 │  row 521 │ ← stop here
│ ACC0000000001  │ 2025-01-10 │  row 312 │ ← skip
│ ACC0000000002  │ 2025-03-15 │  row 901 │ ← skip: different account
│     ...        │    ...     │    ...   │
└────────────────┴────────────┴──────────┘

The database jumps to ACC0000000001 in the index,
scans forward in date order, stops when outside 30 days.
Never touches any other account's rows.
```

**The column order rule:**
The first column in a composite index is the most important.

```
Index on (account_id, txn_date)

✅ Works for:  WHERE account_id = 'X'
✅ Works for:  WHERE account_id = 'X' AND txn_date >= '2025-01-01'
❌ Does NOT:   WHERE txn_date >= '2025-01-01' (no account filter)
```

Think of it like a phone book sorted by surname then first name.
You can find all people named Al-Omari easily.
You cannot find all people named Ahmed easily — because Ahmed
is the second sort level.

---

### Type 3 — Partial Index

An index that only includes rows matching a specific condition.
Smaller, faster, and more targeted than a full index.

```sql
CREATE INDEX idx_txn_non_posted
ON retail.transaction (status, txn_date DESC)
WHERE status != 'POSTED';
```

**The problem it solves:**
```
TRANSACTION TABLE — 500 million rows

POSTED rows:     499,500,000   (99.9%)  ← AML team never needs these
PENDING rows:        400,000   (0.08%)  ← AML team needs these
FAILED rows:         100,000   (0.02%)  ← AML team needs these
```

A full index on status would include all 500 million rows.
The partial index includes only 500,000 rows.

```
FULL INDEX on status         PARTIAL INDEX on status
(all 500M rows)              (only non-POSTED rows)

Size: ~8 GB                  Size: ~8 MB
Query time: seconds          Query time: milliseconds
```

**Visual:**
```
PARTIAL INDEX — WHERE status != 'POSTED'

┌───────────┬────────────┬──────────┐
│  status   │  txn_date  │ row ptr  │
├───────────┼────────────┼──────────┤
│  FAILED   │ 2025-03-15 │ row 9821 │
│  FAILED   │ 2025-03-14 │ row 8734 │
│  PENDING  │ 2025-03-15 │ row 9654 │
│  PENDING  │ 2025-03-14 │ row 8901 │
│  REVERSED │ 2025-03-10 │ row 7234 │
└───────────┴────────────┴──────────┘

499.5 million POSTED rows are NOT in this index.
The index is tiny. Searches are instant.
```

**Serves this query:**
```sql
SELECT txn_id, account_id, amount_sar, status
FROM retail.transaction
WHERE status IN ('PENDING', 'FAILED', 'REVERSED')
  AND txn_date >= CURRENT_DATE - INTERVAL '7 days';
```

---

### Type 4 — Covering Index

An index that includes all the columns a query needs, so the
database never needs to touch the main table at all.

```sql
CREATE INDEX idx_txn_account_covering
ON retail.transaction (account_id, txn_date DESC)
INCLUDE (txn_type, amount_sar, direction, channel);
```

**Normal index lookup — two steps:**
```
Step 1: Look up account_id in the index
        Find row locations: rows 312, 521, 634, 712, 847

Step 2: Go to the main table
        Fetch txn_type, amount_sar, direction, channel
        from rows 312, 521, 634, 712, 847

Two trips. Two I/O operations.
```

**Covering index lookup — one step:**
```
Step 1: Look up account_id in the index
        Find row locations AND txn_type, amount_sar,
        direction, channel — all already in the index

Done. Never touched the main table.
One trip. One I/O operation.
```

**Visual:**
```
COVERING INDEX on (account_id, txn_date)
INCLUDE (txn_type, amount_sar, direction, channel)

┌────────────────┬────────────┬──────────┬────────────┬───────────┐
│   account_id   │  txn_date  │ txn_type │ amount_sar │  channel  │
├────────────────┼────────────┼──────────┼────────────┼───────────┤
│ ACC0000000001  │ 2025-03-10 │  CREDIT  │  15000.00  │  BRANCH   │
│ ACC0000000001  │ 2025-03-01 │  MRB_PMT │   3750.00  │  MOBILE   │
│ ACC0000000001  │ 2025-02-15 │ SADAD_PMT│    450.00  │  MOBILE   │
└────────────────┴────────────┴──────────┴────────────┴───────────┘

Everything the query needs is here.
Main table: never touched.
```

**Serves this query at maximum speed:**
```sql
SELECT txn_date, txn_type, amount_sar, direction, channel
FROM retail.transaction
WHERE account_id = 'ACC0000000000001'
  AND txn_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY txn_date DESC;
```

---

### Type 5 — Unique Index

Enforces that no two rows can have the same value in a column.
Automatically created when you define a PRIMARY KEY or UNIQUE
constraint — but you can create one manually too.

```sql
CREATE UNIQUE INDEX idx_customer_nid
ON retail.customer (national_id);
```

**What it prevents:**
```sql
-- First insert: succeeds
INSERT INTO retail.customer (customer_id, national_id, ...)
VALUES ('C000000001', '1234567890123', ...);

-- Second insert with same NID: FAILS
INSERT INTO retail.customer (customer_id, national_id, ...)
VALUES ('C000000099', '1234567890123', ...);

-- ERROR: duplicate key value violates unique constraint
-- DETAIL: Key (national_id)=(1234567890123) already exists.
```

**Why this matters in banking:**
Two customers with the same National ID is both a data quality
failure and a potential fraud signal. The unique index makes it
physically impossible at the database level — no application
code can accidentally insert a duplicate.

---

## The Write Speed Trade-off

Every index you add makes reads faster but writes slower.

```
INSERT INTO retail.transaction (...) VALUES (...);

Without indexes — database does:
┌──────────────────────────────────┐
│ 1. Write row to table       10ms │
│ Total: 10ms                      │
└──────────────────────────────────┘

With 5 indexes — database does:
┌──────────────────────────────────────────┐
│ 1. Write row to table               10ms │
│ 2. Update idx_txn_account_date      15ms │
│ 3. Update idx_txn_date              12ms │
│ 4. Update idx_txn_type_date         14ms │
│ 5. Update idx_txn_non_posted         3ms │
│ 6. Update idx_txn_account_covering  18ms │
│ Total: 72ms                              │
└──────────────────────────────────────────┘

7x slower per insert.
Across millions of daily transactions this adds up.
```

**The rule by architectural layer:**

| Layer | Approach | Why |
|---|---|---|
| CBS / Operational | Minimal indexes | High write volume — protect insert speed |
| ODS / Integration | Moderate indexes | Mix of reads and writes |
| DWH / Analytical | Comprehensive indexes | Data loads in batch — reads dominate |

---

## How to Know if You Need an Index

### Run EXPLAIN ANALYZE

```sql
EXPLAIN ANALYZE
SELECT txn_id, amount_sar
FROM retail.transaction
WHERE account_id = 'ACC0000000000001'
  AND txn_date >= '2025-01-01';
```

**Bad output — no index:**
```
Seq Scan on transaction
  (cost=0.00..98234.50 rows=6 width=16)
  (actual time=0.043..4823.221 rows=6 loops=1)
  Filter: (account_id = 'ACC0000000000001'
           AND txn_date >= '2025-01-01')
  Rows Removed by Filter: 4999994

Planning Time: 0.8 ms
Execution Time: 4823.4 ms    ← 4.8 seconds. Too slow.
```

**Good output — with index:**
```
Index Scan using idx_txn_account_date on transaction
  (cost=0.56..18.23 rows=6 width=16)
  (actual time=0.031..0.089 rows=6 loops=1)
  Index Cond: (account_id = 'ACC0000000000001'
               AND txn_date >= '2025-01-01')

Planning Time: 0.4 ms
Execution Time: 0.1 ms    ← 0.1 milliseconds. Perfect.
```

**4,823x faster with the index.**

---

## Reading EXPLAIN ANALYZE Output

```
Seq Scan on transaction        ← BAD: reading every row
Index Scan using idx_name      ← GOOD: using an index
Index Only Scan using idx_name ← BEST: covered by index,
                                        table not touched

cost=0.00..98234.50   ← estimated cost (higher = more work)
rows=6                ← estimated rows to return
actual time=0.04..4823 ← real start and end time in ms
rows=6 loops=1        ← actual rows returned

Rows Removed by Filter: 4999994
← how many rows were scanned and thrown away
   High number = you need an index
```

---

## The Five Al-Noor Bank Indexes — Complete Picture

```sql
-- 1. COMPOSITE — account statement queries
--    Serves: "Show all transactions for account X in date order"
--    Used by: Mobile app, teller screen, account statement
CREATE INDEX idx_txn_account_date
ON retail.transaction (account_id, txn_date DESC);

-- 2. SINGLE COLUMN — date range queries
--    Serves: "All transactions for yesterday" (SAMA daily report)
--    Used by: SAMA liquidity reporting, end-of-day reconciliation
CREATE INDEX idx_txn_date
ON retail.transaction (txn_date DESC);

-- 3. COMPOSITE — transaction type queries
--    Serves: "All Murabaha payments this month"
--    Used by: Islamic finance reporting, product performance
CREATE INDEX idx_txn_type_date
ON retail.transaction (txn_type, txn_date DESC);

-- 4. PARTIAL — non-posted transactions only
--    Serves: "All pending or failed transactions"
--    Used by: AML monitoring, operations team
--    Size: ~0.1% of a full index — tiny and fast
CREATE INDEX idx_txn_non_posted
ON retail.transaction (status, txn_date DESC)
WHERE status != 'POSTED';

-- 5. COVERING — dashboard queries with no heap access
--    Serves: Dashboard queries needing common columns
--    Used by: BI dashboards, reporting layer
--    Benefit: Never touches the main table
CREATE INDEX idx_txn_account_covering
ON retail.transaction (account_id, txn_date DESC)
INCLUDE (txn_type, amount_sar, direction, channel);
```

---

## Common Mistakes to Avoid

---

### Mistake 1 — Indexing the Wrong Column

```sql
-- You write this query all the time:
SELECT * FROM transaction
WHERE account_id = 'X' AND txn_date >= '2025-01-01';

-- You create this index:
CREATE INDEX idx_wrong ON transaction (txn_date);

-- Problem: txn_date alone does not help when account_id
-- is the primary filter. The database still has to check
-- millions of rows for the right account_id.

-- Fix: composite index with account_id first
CREATE INDEX idx_correct
ON transaction (account_id, txn_date DESC);
```

---

### Mistake 2 — Too Many Indexes on a Write-Heavy Table

```sql
-- A developer adds 20 indexes to the transaction table
-- thinking more indexes = better performance.

-- Result:
-- Each INSERT now updates 20 index structures
-- Insert throughput drops significantly
-- The settlement batch that ran in 2 hours now runs in 10 hours

-- Rule: Add only the indexes your actual query patterns need.
-- Profile first. Index second.
```

---

### Mistake 3 — Functions on Indexed Columns

```sql
-- Index exists on txn_date
CREATE INDEX idx_txn_date ON transaction (txn_date);

-- But this query wraps txn_date in a function:
SELECT * FROM transaction
WHERE DATE_TRUNC('month', txn_date) = '2025-01-01';

-- Problem: The database cannot use the index because it has
-- to compute DATE_TRUNC for every row first.
-- EXPLAIN ANALYZE will show: Seq Scan

-- Fix: rewrite using a range instead
SELECT * FROM transaction
WHERE txn_date >= '2025-01-01'
  AND txn_date <  '2025-02-01';
-- Now EXPLAIN ANALYZE shows: Index Scan
```

---

### Mistake 4 — Missing Index on a Foreign Key Column

```sql
-- You have a FK from transaction to account
CONSTRAINT fk_txn_account
  FOREIGN KEY (account_id) REFERENCES account(account_id)

-- But you forgot to index account_id in the transaction table

-- Result: Every time an account row is deleted or updated,
-- PostgreSQL must scan the entire transaction table to check
-- for existing references. On a billion-row table this causes
-- serious lock contention and slow deletes.

-- Fix: always index FK columns
CREATE INDEX idx_txn_account_id
ON transaction (account_id);
```

---

## Summary — Quick Reference Card

| Index Type | When to Use | Example Column(s) |
|---|---|---|
| Single Column | Filter on one column frequently | risk_rating, status |
| Composite | Filter on multiple columns together | account_id + txn_date |
| Partial | Most rows excluded by a condition | WHERE status != 'POSTED' |
| Covering | Query needs only a few specific columns | Dashboard read queries |
| Unique | Enforce no duplicates | national_id, account_number |

---

## The One Rule to Remember

> **An index is a trade-off.**
>
> It makes reads faster by making writes slower.
>
> Design for the dominant workload at each layer.
>
> Always verify with EXPLAIN ANALYZE before and after.