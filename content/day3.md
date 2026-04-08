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


# Data Engineering — Intermediate
## Day 3 Complete Concepts Guide
### Simple Explanations · Syntax · Real-Life Examples

---

> **A personal note before you begin.**
>
> This guide has been written with you in mind.
> Every concept is explained in plain language first,
> then shown with syntax, then demonstrated with a
> real example you can run yourself.
>
> There are no assumptions here about what you already know.
> Whether a concept is new to you or a reminder of something
> familiar, we hope this guide serves you well.
>
> Take your time. Read every analogy. Run every example.
> Understanding comes from doing, not just reading.

---

## Table of Contents

1. Physical Database Creation
2. Data Types — Choosing the Right Container
3. Primary Keys — Three Strategies
4. Indexes — Making Searches Fast
5. Table Partitioning — Managing Large Data
6. CRUD Operations — Insert, Update, Delete
7. Views — Simplifying Complex Queries
8. Materialised Views — Pre-computed Results
9. Stored Procedures and Functions
10. Transaction Control and ACID
11. Savepoints — Partial Rollback
12. Query Optimisation — Three Patterns
13. EXPLAIN ANALYZE — Reading the Execution Plan

---

---

# 1. Physical Database Creation

---

## What It Is

Physical database creation is the process of turning your design
on paper into an actual working database on a real server.

Think of it like constructing a building.
The architect's drawing is your design.
The physical build — choosing the actual materials, laying the
foundations, separating the rooms — is your physical database.

---

## The Two Key Decisions

### Decision 1 — Encoding

Encoding tells the database which alphabet to use when storing text.

```
Without correct encoding:
"أحمد العمري" → stored as → "?????? ??????"

With UTF8 encoding:
"أحمد العمري" → stored as → "أحمد العمري"
```

**UTF8** supports every language in the world — Arabic, English,
Chinese, and everything in between. Always use it.

**Syntax:**

```sql
-- Always specify UTF8 when creating a database
-- that will store Arabic text or any non-Latin characters

CREATE DATABASE shopsmart
    ENCODING    'UTF8'
    LC_COLLATE  'en_US.UTF-8'
    LC_CTYPE    'en_US.UTF-8';
```

**What happens if you forget:**

```sql
-- If you create a database without specifying encoding,
-- the system default may be Latin-1.
-- Arabic characters either fail on insert or appear as
-- question marks. You cannot fix this later without
-- recreating the entire database.

-- Always specify UTF8. Always.
```

---

### Decision 2 — Schemas

A schema is a named container inside a database that holds
a group of related tables.

**Real-life analogy:**

```
Your database = An office building
Your schemas  = Separate rooms in that building

┌─────────────────────────────────────────────────┐
│                SHOPSMART DATABASE               │
│                                                 │
│  ┌───────────┐  ┌───────────┐  ┌─────────────┐ │
│  │  retail   │  │  finance  │  │  analytics  │ │
│  │           │  │           │  │             │ │
│  │ customers │  │ payments  │  │ reports     │ │
│  │ orders    │  │ invoices  │  │ dashboards  │ │
│  │ products  │  │           │  │             │ │
│  └───────────┘  └───────────┘  └─────────────┘ │
│                                                 │
│  Each room has its own lock.                    │
│  A person with access to retail                 │
│  cannot walk into finance.                      │
└─────────────────────────────────────────────────┘
```

**Syntax:**

```sql
-- Connect to your database first
\c shopsmart

-- Create separate schemas for different business areas
CREATE SCHEMA retail;      -- Customer-facing tables
CREATE SCHEMA finance;     -- Payment and invoice tables
CREATE SCHEMA analytics;   -- Reports and dashboards
CREATE SCHEMA staging;     -- Raw data landing zone

-- Set the default search path
-- PostgreSQL will look in these schemas when you
-- reference a table without specifying the schema name
SET search_path TO retail, finance;
```

**Real-life example:**

```sql
-- Without schema separation:
-- All tables in one place — anyone can see everything
SELECT * FROM customers;    -- Anyone can run this
SELECT * FROM payments;     -- Anyone can run this too

-- With schema separation:
-- Access is controlled per schema
GRANT SELECT ON ALL TABLES IN SCHEMA retail   TO sales_team;
GRANT SELECT ON ALL TABLES IN SCHEMA finance  TO finance_team;

-- Now the sales team can query retail tables
-- but cannot see finance tables at all
-- This is data protection by design
```

**Consequence of skipping schemas:**

```
Without schemas:
→ All tables visible to all users
→ Sensitive financial data exposed to everyone
→ No organisational structure as the database grows
→ Harder to apply security policies

With schemas:
→ Tables grouped logically by business area
→ Access controlled at the schema level
→ Clean, organised structure that scales well
→ Security applied precisely where needed
```

---

---

# 2. Data Types — Choosing the Right Container

---

## What It Is

A data type tells the database what kind of value a column can hold
and how to store it efficiently.

**Real-life analogy:**

```
Choosing a data type is like choosing the right container.

Water belongs in a bottle  — not a paper bag (it leaks)
Money belongs in NUMERIC   — not FLOAT (it rounds incorrectly)
Names belong in VARCHAR    — not CHAR (wastes space)
Dates belong in DATE       — not VARCHAR (cannot calculate with text)

Put the wrong thing in the wrong container
and problems appear later — sometimes much later.
```

---

## The Most Important Data Types

---

### NUMERIC — For Money, Always

```
THE MOST IMPORTANT RULE IN BANKING AND E-COMMERCE:

Never store money as FLOAT or DOUBLE PRECISION.
Always use NUMERIC.

Here is why:
```

```sql
-- The FLOAT problem
SELECT 0.1 + 0.2;
-- Result: 0.30000000000000004
-- Not 0.3 — but 0.30000000000000004
-- This is not a bug. This is how floating-point works.

-- Across 1 million transactions:
-- 1,000,000 × SAR 0.00000000000000004 = SAR 0.04
-- Small? Yes. But SAMA reconciliation will catch it.
-- And you will have no explanation.

-- The NUMERIC solution
-- NUMERIC stores exact decimal values
-- NUMERIC(10, 2) means:
--   up to 10 digits total
--   exactly 2 digits after the decimal point

CREATE TABLE orders (
    order_id     SERIAL         NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL  -- Always for money
);

-- SAR 3750.00 stored as NUMERIC = exactly SAR 3750.00
-- SAR 3750.00 stored as FLOAT   = SAR 3749.9999999999999...
```

**Visual:**

```
FLOAT storage of SAR 3750.00:
┌──────────────────────────────────┐
│ 3749.99999999999954525264911353  │  ← Not what you wanted
└──────────────────────────────────┘

NUMERIC(10,2) storage of SAR 3750.00:
┌──────────────────────────────────┐
│ 3750.00                          │  ← Exactly right
└──────────────────────────────────┘
```

---

### VARCHAR vs CHAR

```sql
-- CHAR(n)    — Fixed length. Always uses exactly n characters.
--              Pads with spaces if the value is shorter.
--              Use for values that are always the same length.

-- VARCHAR(n) — Variable length. Uses only as many characters
--              as the value needs.
--              Use for values that vary in length.
```

**Visual:**

```
Storing the word "SAR" in CHAR(10) vs VARCHAR(10):

CHAR(10):     │ S │ A │ R │   │   │   │   │   │   │   │
              └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
              Always 10 characters. 7 spaces wasted.

VARCHAR(10):  │ S │ A │ R │
              └───┴───┴───┘
              Only 3 characters used. No waste.
```

```sql
-- Use CHAR for values that are always a fixed length
CREATE TABLE products (
    currency     CHAR(3)       NOT NULL,  -- Always SAR, USD, EUR
    country_code CHAR(2)       NOT NULL,  -- Always SA, US, GB
    product_name VARCHAR(200)  NOT NULL,  -- Varies in length
    description  TEXT                     -- No length limit needed
);

-- Use VARCHAR for names, addresses, emails — anything variable
-- Use TEXT when you do not need a length limit at all
-- Use CHAR only for fixed-length codes
```

---

### DATE vs TIMESTAMP vs TIMESTAMPTZ

```sql
-- DATE         — Stores a date only. No time. No timezone.
--                Use for: date of birth, order date, expiry date

-- TIMESTAMP    — Stores date and time. No timezone awareness.
--                Dangerous if your servers are in different zones.

-- TIMESTAMPTZ  — Stores date, time, AND timezone.
--                PostgreSQL converts to UTC internally.
--                Always use this for event timestamps.
```

**Real-life example:**

```sql
-- The timezone problem:
-- Your database server is in Riyadh (UTC+3)
-- A developer in London (UTC+0) runs a report
-- Using TIMESTAMP (no timezone):
--   An order placed at 10:00 AM Riyadh time
--   appears as 10:00 AM in London too — WRONG
--   It should appear as 07:00 AM London time

-- Using TIMESTAMPTZ:
--   PostgreSQL stores the moment in UTC
--   Converts to the correct local time for each viewer
--   10:00 AM Riyadh shows as 07:00 AM London — CORRECT

CREATE TABLE orders (
    order_id    SERIAL       NOT NULL,
    order_date  DATE         NOT NULL,  -- Just the date
    created_at  TIMESTAMPTZ  NOT NULL   -- Exact moment with timezone
                             DEFAULT CURRENT_TIMESTAMP
);
```

---

### BOOLEAN

```sql
-- Stores TRUE or FALSE only.
-- Use for yes/no flags.

CREATE TABLE customers (
    customer_id SERIAL   NOT NULL,
    is_active   BOOLEAN  NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN  NOT NULL DEFAULT FALSE
);

-- Querying boolean columns
SELECT * FROM customers WHERE is_active = TRUE;
SELECT * FROM customers WHERE is_active;        -- Same thing
SELECT * FROM customers WHERE NOT is_active;    -- Inactive customers
```

---

### Complete Data Type Reference Table

```
┌──────────────────┬─────────────────────────────────────────────────┐
│ Data Type        │ Use For                                         │
├──────────────────┼─────────────────────────────────────────────────┤
│ NUMERIC(18,2)    │ Money, prices, balances — exact decimal         │
│ INTEGER          │ Counts, quantities, IDs                         │
│ BIGINT           │ Very large counts — billions of rows            │
│ SERIAL           │ Auto-incrementing integer — surrogate keys      │
│ BIGSERIAL        │ Auto-incrementing BIGINT                        │
│ VARCHAR(n)       │ Variable-length text with a maximum length      │
│ CHAR(n)          │ Fixed-length codes — currency, country          │
│ TEXT             │ Unlimited length text                           │
│ DATE             │ Date only — birth dates, order dates            │
│ TIMESTAMPTZ      │ Date + time + timezone — all event timestamps   │
│ BOOLEAN          │ True/false flags                                │
│ UUID             │ Globally unique identifiers                     │
└──────────────────┴─────────────────────────────────────────────────┘
```

---

---

# 3. Primary Keys — Three Strategies

---

## What a Primary Key Is

A primary key is the unique identifier for every row in a table.
No two rows can have the same primary key value.
Every table must have exactly one primary key.

**Real-life analogy:**

```
A primary key is like a national ID number.

No two people share the same national ID.
It uniquely identifies one person — and only that person.
Even if two people have the same name, age, and city,
their national ID numbers are different.

In a database, the primary key is that unique identifier
for each row — ensuring no row is ever confused with another.
```

---

## Strategy 1 — Natural Key

A natural key uses a value that already exists in the real world
and naturally identifies the record.

```sql
-- The value has business meaning
-- It already exists in your source systems
-- It is stable — it does not change

CREATE TABLE customers (
    national_id  VARCHAR(15)  NOT NULL,  -- Real-world identifier
    full_name    VARCHAR(100) NOT NULL,
    email        VARCHAR(150) NOT NULL,
    CONSTRAINT pk_customers PRIMARY KEY (national_id)
);
```

**When to use:**
- When a real-world unique identifier already exists
- When other systems already use this identifier
- When the value is guaranteed stable and never changes

**When NOT to use:**
- When the value might change (email addresses change)
- When the value is controlled by another party
- When the value contains sensitive personal data

---

## Strategy 2 — Surrogate Key

A surrogate key is a system-generated number with no business meaning.
The database creates it automatically for each new row.

```sql
-- SERIAL = PostgreSQL auto-increments: 1, 2, 3, 4, 5...
-- The number means nothing in the real world
-- It just uniquely identifies the row in this table

CREATE TABLE orders (
    order_id     SERIAL        NOT NULL,  -- Auto-generated: 1, 2, 3...
    customer_id  INTEGER       NOT NULL,
    total_amount NUMERIC(10,2) NOT NULL,
    CONSTRAINT pk_orders PRIMARY KEY (order_id)
);

-- When you insert a new order:
INSERT INTO orders (customer_id, total_amount)
VALUES (1001, 299.00);
-- order_id is automatically set to the next number
-- You never need to specify it
```

**Visual:**

```
┌──────────┬─────────────┬──────────────┐
│ order_id │ customer_id │ total_amount │
├──────────┼─────────────┼──────────────┤
│        1 │        1001 │       299.00 │  ← auto-generated
│        2 │        1045 │       150.00 │  ← auto-generated
│        3 │        1001 │      1200.00 │  ← auto-generated
│        4 │        2003 │        89.99 │  ← auto-generated
└──────────┴─────────────┴──────────────┘
```

**When to use:**
- High-volume transactional tables (orders, transactions)
- When no natural identifier exists
- When speed and simplicity matter most

---

## Strategy 3 — UUID

UUID stands for Universally Unique Identifier.
It is a randomly generated 32-character string.

```
Example UUID: f47ac10b-58cc-4372-a567-0e02b2c3d479
```

```sql
-- UUID is unique across ALL systems everywhere in the world
-- Not just unique in your database — unique everywhere

CREATE TABLE payments (
    payment_id  UUID          NOT NULL DEFAULT gen_random_uuid(),
    order_id    INTEGER       NOT NULL,
    amount      NUMERIC(10,2) NOT NULL,
    CONSTRAINT pk_payments PRIMARY KEY (payment_id)
);

-- Every insert gets a globally unique ID automatically
INSERT INTO payments (order_id, amount)
VALUES (1001, 299.00);
-- payment_id = f47ac10b-58cc-4372-a567-0e02b2c3d479
-- This ID is unique across every database in the world
```

**When to use:**
- When records are created across multiple systems
- When you need to merge data from different databases
- When the ID must be globally unique (not just locally unique)

---

## Comparison Table

```
┌────────────────┬──────────────────┬────────────────────┬─────────────────┐
│ Strategy       │ Example          │ Best For           │ Avoid When      │
├────────────────┼──────────────────┼────────────────────┼─────────────────┤
│ Natural Key    │ national_id      │ Stable real-world  │ Values change   │
│                │ product_sku      │ identifiers        │ or are sensitive│
├────────────────┼──────────────────┼────────────────────┼─────────────────┤
│ Surrogate Key  │ SERIAL           │ High-volume tables │ Distributed     │
│                │ BIGSERIAL        │ Simple and fast    │ multi-system    │
├────────────────┼──────────────────┼────────────────────┼─────────────────┤
│ UUID           │ gen_random_uuid()│ Multi-system IDs   │ Joins with many │
│                │                  │ Distributed systems│ tables (larger) │
└────────────────┴──────────────────┴────────────────────┴─────────────────┘
```

---

---

# 4. Indexes — Making Searches Fast

---

## What an Index Is

An index is a separate data structure that the database maintains
alongside your table to make searches faster.

**Real-life analogy:**

```
An index works exactly like the index at the back of a book.

Without the book index:
→ You read every page looking for "Murabaha"
→ You read 400 pages to find what you need
→ Slow and exhausting

With the book index:
→ You look up "Murabaha" in the index
→ It says: pages 47, 112, 298
→ You go directly to those pages
→ Fast and efficient

A database index works identically.
Instead of reading every row, the database
jumps directly to the matching rows.
```

---

## Without an Index vs With an Index

```
TABLE: orders — 50,000 rows

Query: WHERE customer_id = 500

WITHOUT INDEX:
┌──────────────────────────────────────────────────────┐
│ Row 1:    customer_id = 1    → not 500, skip         │
│ Row 2:    customer_id = 847  → not 500, skip         │
│ Row 3:    customer_id = 500  → MATCH, keep           │
│ Row 4:    customer_id = 23   → not 500, skip         │
│ ...       reading all 50,000 rows ...                │
│ Row 50000:customer_id = 500  → MATCH, keep           │
└──────────────────────────────────────────────────────┘
Read: 50,000 rows
Time: slow

WITH INDEX on customer_id:
┌──────────────────────────────────────────────────────┐
│ INDEX:                                               │
│ customer_id 499 → rows [812, 9043]                   │
│ customer_id 500 → rows [3, 50000, 12847]  ← here    │
│ customer_id 501 → rows [445, 7821]                   │
└──────────────────────────────────────────────────────┘
Jump directly to rows 3, 50000, 12847
Read: 3 rows
Time: milliseconds
```

---

## Type 1 — Single Column Index

```sql
-- Syntax
CREATE INDEX index_name ON table_name (column_name);

-- ShopSmart example
CREATE INDEX idx_orders_customer
ON orders (customer_id);

-- This index helps queries that filter on customer_id
SELECT order_id, order_date, total_amount
FROM orders
WHERE customer_id = 500;
-- Without index: reads 50,000 rows
-- With index:    reads only matching rows
```

---

## Type 2 — Composite Index

An index on two or more columns together.

```sql
-- Syntax
CREATE INDEX index_name ON table_name (column1, column2);

-- ShopSmart example
-- Operations team runs this query constantly:
-- "Show orders for customer X in date order"

CREATE INDEX idx_orders_customer_date
ON orders (customer_id, order_date DESC);

-- This index serves queries that filter on BOTH columns
SELECT order_id, order_date, total_amount, order_status
FROM orders
WHERE customer_id = 500
  AND order_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY order_date DESC;
```

**The column order rule:**

```
Index on (customer_id, order_date)

┌──────────────────────────────────────────────────────┐
│ ✅ Helps:  WHERE customer_id = 500                   │
│ ✅ Helps:  WHERE customer_id = 500 AND order_date... │
│ ❌ Cannot: WHERE order_date >= '2025-01-01' alone    │
└──────────────────────────────────────────────────────┘

The first column is the main entry point.
Always put the column you filter on most often FIRST.

Think of a phone book sorted by surname then first name:
→ Finding "Al-Omari, Ahmed" is easy
→ Finding "Ahmed, ???" across all surnames is hard
```

---

## Type 3 — Partial Index

An index that only includes rows matching a condition.

```sql
-- Syntax
CREATE INDEX index_name ON table_name (column)
WHERE condition;

-- ShopSmart example
-- 85% of orders are DELIVERED
-- Operations team only queries PENDING and PROCESSING orders

-- Full index would include ALL 50,000 rows
CREATE INDEX idx_orders_status_full
ON orders (order_status, order_date DESC);
-- Size: ~100% of possible rows indexed

-- Partial index includes ONLY non-delivered orders (~15%)
CREATE INDEX idx_orders_active
ON orders (order_status, order_date DESC)
WHERE order_status NOT IN ('DELIVERED', 'CANCELLED');
-- Size: ~15% of rows indexed — much smaller and faster
```

**Visual comparison:**

```
FULL INDEX (all statuses):
┌─────────────────────────────────────────────────┐
│ CANCELLED   → 2,500 rows                        │
│ DELIVERED   → 42,500 rows  ← never needed       │
│ PENDING     → 1,250 rows                        │
│ PROCESSING  → 1,250 rows                        │
│ REFUNDED    → 1,250 rows                        │
│ SHIPPED     → 1,250 rows                        │
│ Total: 50,000 rows indexed                      │
└─────────────────────────────────────────────────┘

PARTIAL INDEX (active orders only):
┌─────────────────────────────────────────────────┐
│ PENDING     → 1,250 rows                        │
│ PROCESSING  → 1,250 rows                        │
│ SHIPPED     → 1,250 rows                        │
│ Total: 3,750 rows indexed — 13x smaller         │
└─────────────────────────────────────────────────┘

Smaller index = fits in memory = faster lookups
```

---

## Type 4 — Covering Index

An index that includes all the columns the query needs.
The database never needs to visit the main table at all.

```sql
-- Syntax
CREATE INDEX index_name ON table_name (column1, column2)
INCLUDE (column3, column4, column5);

-- ShopSmart example
-- Dashboard query needs: order_date, order_status,
--                        total_amount, channel

-- Regular index — two steps:
-- Step 1: Find matching rows in the index
-- Step 2: Go to the main table to get the other columns

-- Covering index — one step:
-- Step 1: Find matching rows AND get all needed columns
--         directly from the index — table never touched

CREATE INDEX idx_orders_customer_covering
ON orders (customer_id, order_date DESC)
INCLUDE (order_status, total_amount, channel);

-- Now this query never touches the main table:
SELECT order_date, order_status, total_amount, channel
FROM orders
WHERE customer_id = 500
ORDER BY order_date DESC;
-- EXPLAIN ANALYZE shows: "Index Only Scan" — the best possible
```

**Visual:**

```
Regular Index Lookup:
                                    ORDERS TABLE
INDEX               Step 2: fetch  ┌─────────────────────┐
┌──────────────┐    ← ← ← ← ← ← ← │ order_status        │
│ customer=500 │                   │ total_amount        │
│ rows: 3,7,12 │ → → → → → → → → → │ channel             │
└──────────────┘    Step 1: found  └─────────────────────┘
Two trips required

Covering Index Lookup:
┌────────────────────────────────────────────────┐
│ customer=500 │ order_date │ status │ total │ ch │
│ rows: 3,7,12 │ 2025-03-01 │ DELIV  │ 299   │ WEB│
└────────────────────────────────────────────────┘
Everything is here. Table never visited.
One trip — fastest possible.
```

---

## Type 5 — Unique Index

Prevents duplicate values in a column.

```sql
-- Syntax
CREATE UNIQUE INDEX index_name ON table_name (column);

-- ShopSmart example
-- Two customers cannot have the same email address

CREATE UNIQUE INDEX idx_customers_email
ON customers (email);

-- First insert: succeeds
INSERT INTO customers (full_name, email)
VALUES ('Ahmed Al-Omari', 'ahmed@shopsmart.sa');

-- Second insert with same email: FAILS immediately
INSERT INTO customers (full_name, email)
VALUES ('Ahmed Abdullah', 'ahmed@shopsmart.sa');
-- ERROR: duplicate key value violates unique constraint
-- This is the database protecting your data integrity
```

---

## The Write Speed Trade-off

```
Every index speeds up reads but slows down writes.

When you INSERT a new row, PostgreSQL must update
every index on that table.

                    INSERT one row
                         ↓
    ┌────────────────────────────────────┐
    │ Write the row to the table    10ms │
    │ Update index 1                 8ms │
    │ Update index 2                 7ms │
    │ Update index 3                 9ms │
    │ Update index 4                 6ms │
    │ Total                         40ms │
    └────────────────────────────────────┘

More indexes = slower inserts.

RULE:
→ Write-heavy tables (orders, transactions): minimal indexes
→ Read-heavy tables (reports, dashboards):   more indexes
→ Always add only the indexes your queries actually need
```

---

---

# 5. Table Partitioning — Managing Large Data

---

## What It Is

Partitioning splits one very large table into smaller physical pieces
called partitions. The database treats it as one table —
but internally stores the data in separate sections.

**Real-life analogy:**

```
Imagine a filing cabinet with 10 years of customer orders.

Without partitioning:
→ All 10 years of orders in one giant drawer
→ Finding last month's orders means searching through everything
→ Slow, difficult, and gets worse every year

With partitioning (one drawer per year):
┌────────────────────────────────────────────┐
│  Drawer 2016  │  Drawer 2017  │  Drawer 2018  │
│  Drawer 2019  │  Drawer 2020  │  Drawer 2021  │
│  Drawer 2022  │  Drawer 2023  │  Drawer 2024  │
│                    Drawer 2025               │
└────────────────────────────────────────────┘

Finding last month's orders?
→ Open the 2025 drawer only
→ Never touch the other 9 drawers
→ Fast, organised, and scales well
```

---

## Why It Matters

```
A large e-commerce platform processes 100,000 orders per day.

After 5 years:
100,000 × 365 × 5 = 182,500,000 rows

Without partitioning:
Query: "Show me this week's orders"
→ PostgreSQL must plan against 182 million rows
→ Even with indexes, performance degrades significantly

With partitioning by year:
Query: "Show me this week's orders"
→ PostgreSQL reads only the 2025 partition
→ The other 4 years of data are completely ignored
→ Much faster — and gets better with more data
```

---

## Syntax

```sql
-- Step 1: Create the parent table with PARTITION BY
CREATE TABLE orders (
    order_id     SERIAL        NOT NULL,
    customer_id  INTEGER       NOT NULL,
    order_date   DATE          NOT NULL,
    order_status VARCHAR(20)   NOT NULL,
    total_amount NUMERIC(10,2) NOT NULL,
    CONSTRAINT pk_orders PRIMARY KEY (order_id, order_date)
) PARTITION BY RANGE (order_date);
-- RANGE means: divide data based on ranges of order_date values


-- Step 2: Create the individual partitions (one per year)
CREATE TABLE orders_2023 PARTITION OF orders
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE orders_2024 PARTITION OF orders
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE orders_2025 PARTITION OF orders
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');


-- Step 3: Create indexes on the parent table
-- They automatically apply to ALL partitions
CREATE INDEX idx_orders_customer_date
ON orders (customer_id, order_date DESC);
```

---

## How PostgreSQL Uses Partitions

```sql
-- This query only reads the 2025 partition
-- The 2023 and 2024 partitions are completely ignored
-- PostgreSQL calls this "partition pruning"

SELECT order_id, customer_id, total_amount
FROM orders
WHERE order_date >= '2025-01-01'
  AND order_date <  '2026-01-01';
```

**Visual — partition pruning:**

```
Query: WHERE order_date >= '2025-01-01'

┌──────────────────────────────────────────────┐
│ orders_2023   SKIPPED  ✗  (wrong date range) │
│ orders_2024   SKIPPED  ✗  (wrong date range) │
│ orders_2025   READING  ✓  (matches!)          │
└──────────────────────────────────────────────┘

Without partitioning: all rows scanned
With partitioning:    only relevant partition scanned
```

---

## Inserting Data — Automatic Routing

```sql
-- You insert into the parent table — orders
-- PostgreSQL automatically puts each row in the right partition
-- based on the order_date value

INSERT INTO orders (customer_id, order_date, order_status,
                    total_amount)
VALUES (1001, '2025-03-15', 'PENDING', 299.00);
-- This row automatically goes into orders_2025

INSERT INTO orders (customer_id, order_date, order_status,
                    total_amount)
VALUES (1002, '2024-11-20', 'DELIVERED', 150.00);
-- This row automatically goes into orders_2024
```

---

---

# 6. CRUD Operations — Insert, Update, Delete

---

## What CRUD Means

```
C → CREATE  → INSERT  (adding new data)
R → READ    → SELECT  (reading data)
U → UPDATE  → UPDATE  (changing existing data)
D → DELETE  → DELETE  (removing data)
```

---

## INSERT — Adding New Data

**The right way — always list your columns:**

```sql
-- BAD: implicit column order — fragile and dangerous
INSERT INTO orders VALUES (DEFAULT, 1001, CURRENT_DATE,
                          'PENDING', 299.00, 'MOBILE');
-- If anyone adds or reorders columns in the table,
-- this INSERT puts values in the wrong columns.
-- Errors may not appear immediately — just wrong data silently.

-- GOOD: explicit column list — safe and clear
INSERT INTO orders (customer_id, order_date, order_status,
                    total_amount, channel)
VALUES (1001, CURRENT_DATE, 'PENDING', 299.00, 'MOBILE');
-- Clear, safe, and works even if the table structure changes.
```

**Using RETURNING to confirm what was inserted:**

```sql
-- RETURNING gives you back the inserted row immediately
-- No need for a second SELECT query
-- One round trip instead of two

INSERT INTO orders (customer_id, order_date, order_status,
                    total_amount, channel)
VALUES (1001, CURRENT_DATE, 'PENDING', 299.00, 'MOBILE')
RETURNING order_id, order_date, total_amount, order_status;

-- Output:
-- order_id | order_date  | total_amount | order_status
-- ---------+-------------+--------------+-------------
--    50001 | 2025-03-15  |       299.00 | PENDING
--
-- You immediately know the new order_id without another query.
```

**Inserting multiple rows at once:**

```sql
-- More efficient than separate INSERT statements
INSERT INTO products (product_name, category, price, stock_qty)
VALUES
    ('Wireless Headphones', 'Electronics',  299.00, 50),
    ('Leather Wallet',      'Accessories',   89.00, 200),
    ('Running Shoes',       'Sports',        199.00, 75),
    ('Coffee Maker',        'Home & Garden', 349.00, 30);
-- Four rows inserted in one operation
```

---

## UPDATE — Changing Existing Data

**Basic syntax:**

```sql
-- Always use a WHERE clause with UPDATE
-- Without WHERE, you update EVERY row in the table

-- BAD: updates ALL customers — almost certainly a mistake
UPDATE customers
SET membership = 'GOLD';

-- GOOD: updates only the specific customer
UPDATE customers
SET membership = 'GOLD',
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 1001;
```

**Using RETURNING with UPDATE:**

```sql
-- See exactly what was changed
UPDATE orders
SET order_status = 'SHIPPED',
    updated_at   = CURRENT_TIMESTAMP
WHERE order_status = 'PROCESSING'
  AND order_date < CURRENT_DATE - INTERVAL '2 days'
RETURNING order_id, customer_id, order_date, order_status;

-- This shows you every order that was just updated
-- Useful for logging and audit trails
```

**Updating with a calculated value:**

```sql
-- Increase all Electronics prices by 10%
UPDATE products
SET price      = ROUND(price * 1.10, 2),
    updated_at = CURRENT_TIMESTAMP
WHERE category = 'Electronics'
  AND is_available = TRUE
RETURNING product_id, product_name, price;
-- RETURNING shows the NEW price after the update
```

---

## DELETE — Removing Data

**The most important rule in professional systems:**

```
In most production systems — especially in banking and e-commerce —
you almost never hard DELETE data.

You SOFT DELETE instead.

Hard Delete:  The row is gone forever.
              Cannot be recovered.
              Audit trail destroyed.
              Foreign key references break.

Soft Delete:  Add a flag column called is_deleted.
              Set is_deleted = TRUE instead of deleting.
              The row still exists but is hidden from normal queries.
              Audit trail preserved.
              Data can be recovered if needed.
```

**Setting up soft delete:**

```sql
-- Add soft delete columns to your table
ALTER TABLE customers
    ADD COLUMN is_deleted     BOOLEAN   NOT NULL DEFAULT FALSE,
    ADD COLUMN deleted_at     TIMESTAMP,
    ADD COLUMN deleted_reason VARCHAR(100);

-- "Deleting" a customer the safe way
UPDATE customers
SET
    is_deleted     = TRUE,
    deleted_at     = CURRENT_TIMESTAMP,
    deleted_reason = 'Customer requested account closure'
WHERE customer_id = 1001
  AND is_deleted = FALSE;  -- Safety: only if not already deleted

-- Normal queries exclude soft-deleted records
SELECT customer_id, full_name, email
FROM customers
WHERE is_deleted = FALSE;  -- Always add this filter
```

**When you absolutely must hard delete:**

```sql
-- Only delete when you are certain it is safe
-- Always use a WHERE clause
-- Always check what you are about to delete first

-- Step 1: Check before deleting
SELECT * FROM order_items
WHERE order_id = 999;

-- Step 2: If you are sure, then delete
DELETE FROM order_items
WHERE order_id = 999;

-- Never run DELETE without a WHERE clause
-- DELETE FROM order_items;  ← This deletes EVERYTHING
```

---

---

# 7. Views — Simplifying Complex Queries

---

## What a View Is

A view is a saved SQL query that looks and behaves like a table.
You query it the same way — but instead of stored data,
it runs the underlying SQL and returns the result.

**Real-life analogy:**

```
Think of a view like a personalised newspaper.

The full newspaper contains everything:
sports, politics, business, weather, classifieds.

A personalised newspaper shows only what you care about:
just the business section tailored to your interests.

The full newspaper still exists behind the scenes.
You just get a clean, relevant view of it.

In a database:
→ The underlying tables contain all the data
→ The view shows only what the user needs
→ Complex JOIN logic is hidden inside the view
→ The user just runs: SELECT * FROM my_view
```

---

## Why Views Are Valuable

```
Without a view — every analyst writes their own JOIN:

SELECT c.full_name, c.city, o.order_date,
       o.total_amount, o.order_status,
       p.payment_method, p.payment_status
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id = p.order_id
WHERE o.order_status = 'DELIVERED'
  AND p.payment_status = 'COMPLETED';

Problems:
→ Different analysts may join slightly differently
→ Results are inconsistent across reports
→ One mistake in one analyst's version → wrong report
→ Complex to write every time

With a view — one definition, everyone uses it:

SELECT * FROM v_completed_orders;

Benefits:
→ One definition maintained in one place
→ Consistent results for everyone
→ Easy to query — no JOIN knowledge required
→ Fix the view once → everyone benefits
```

---

## Syntax — Creating a View

```sql
-- Basic syntax
CREATE OR REPLACE VIEW view_name AS
SELECT ... your query here ...;

-- ShopSmart example: completed orders view
CREATE OR REPLACE VIEW v_completed_orders AS
SELECT
    c.customer_id,
    c.full_name,
    c.city,
    c.membership,
    o.order_id,
    o.order_date,
    o.total_amount,
    o.channel,
    p.payment_method,
    p.payment_date
FROM customers c
JOIN orders o   ON c.customer_id = o.customer_id
JOIN payments p ON o.order_id   = p.order_id
WHERE o.order_status   = 'DELIVERED'
  AND p.payment_status = 'COMPLETED';

-- Now anyone can query it simply:
SELECT * FROM v_completed_orders
WHERE city = 'Riyadh'
ORDER BY order_date DESC
LIMIT 20;
```

---

## Practical Uses of Views

**Use 1 — Hiding complexity:**

```sql
-- The sales team wants to see customer order summaries
-- They should not need to know how to write complex JOINs

CREATE OR REPLACE VIEW v_customer_summary AS
SELECT
    c.customer_id,
    c.full_name,
    c.city,
    c.membership,
    COUNT(o.order_id)   AS total_orders,
    SUM(o.total_amount) AS lifetime_spending,
    MAX(o.order_date)   AS last_order_date
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
                  AND o.order_status != 'CANCELLED'
GROUP BY c.customer_id, c.full_name, c.city, c.membership;

-- Sales team query — simple and clean
SELECT * FROM v_customer_summary
WHERE membership = 'PLATINUM'
ORDER BY lifetime_spending DESC;
```

**Use 2 — Controlling what data people see:**

```sql
-- The marketing team needs customer data
-- but should NOT see email addresses or exact spending amounts

CREATE OR REPLACE VIEW v_marketing_customers AS
SELECT
    customer_id,
    full_name,
    city,
    membership,
    registered_at
    -- email is deliberately NOT included
    -- exact spending is NOT included
FROM customers
WHERE is_active = TRUE;

-- Grant access to the view — not the underlying table
GRANT SELECT ON v_marketing_customers TO marketing_team;

-- Marketing can see names and cities
-- They cannot see emails or financial data
```

---

## Updating and Dropping Views

```sql
-- Update a view (replaces the existing definition)
CREATE OR REPLACE VIEW v_completed_orders AS
SELECT ... new query ...;

-- Remove a view when no longer needed
DROP VIEW IF EXISTS v_completed_orders;

-- Views do not store data
-- Dropping a view does not delete any underlying data
-- It only removes the saved query definition
```

---

---

# 8. Materialised Views — Pre-computed Results

---

## The Difference from a Standard View

```
Standard View:
→ Runs the query fresh every time you query it
→ Always shows current data
→ Slow on large tables (re-runs the aggregation every time)

Materialised View:
→ Runs the query once and stores the result on disk
→ Shows data as of the last refresh
→ Fast — reads pre-computed results, not raw data

Think of it like this:

Standard View    = A chef cooking your meal fresh every time
                   Always fresh, takes time to prepare

Materialised View = A meal prepared last night and stored in the fridge
                   Ready instantly, not from this exact minute
                   But good enough when yesterday's data is acceptable
```

---

## When to Use Each

```
┌──────────────────────────────────────────────────────────┐
│ Use STANDARD VIEW when:                                  │
│ → Data must be current at all times                      │
│ → Operations team checking live order status             │
│ → Customer service checking today's deliveries           │
│ → AML team monitoring real-time alerts                   │
│                                                          │
│ Use MATERIALISED VIEW when:                              │
│ → Data does not need to be live (yesterday is fine)      │
│ → Monthly sales summaries by city                        │
│ → Product performance dashboards (refreshed nightly)     │
│ → Heavy aggregations over millions of rows               │
│ → Reports that must load in under 1 second               │
└──────────────────────────────────────────────────────────┘
```

---

## Syntax

```sql
-- Create a materialised view
CREATE MATERIALIZED VIEW mv_monthly_sales AS
SELECT
    DATE_TRUNC('month', o.order_date) AS order_month,
    c.city,
    COUNT(o.order_id)                 AS order_count,
    SUM(o.total_amount)               AS total_revenue,
    AVG(o.total_amount)               AS avg_order_value
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'DELIVERED'
GROUP BY DATE_TRUNC('month', o.order_date), c.city
ORDER BY order_month DESC, total_revenue DESC
WITH DATA;
-- WITH DATA means: run the query now and store the result
-- WITH NO DATA means: create the structure but leave it empty


-- Query it exactly like a regular table
SELECT * FROM mv_monthly_sales
WHERE order_month >= '2025-01-01'
ORDER BY total_revenue DESC;


-- Refresh it when you want updated data
-- This re-runs the underlying query and replaces the stored result
REFRESH MATERIALIZED VIEW mv_monthly_sales;


-- Refresh WITHOUT locking (users can still read while refreshing)
-- Requires a unique index first
CREATE UNIQUE INDEX idx_mv_monthly_sales
ON mv_monthly_sales (order_month, city);

REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_sales;
-- CONCURRENTLY = users can read old data while new data loads
-- This is the production-safe way to refresh


-- Remove a materialised view
DROP MATERIALIZED VIEW IF EXISTS mv_monthly_sales;
```

---

## Side-by-Side Comparison

```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│ Feature             │ Standard View       │ Materialised View   │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Storage             │ None — SQL only     │ Stored on disk      │
│ Data freshness      │ Always current      │ As of last refresh  │
│ Query speed         │ Slow on large data  │ Fast — pre-computed │
│ Refresh control     │ Automatic (always)  │ Manual or scheduled │
│ Use case            │ Live operations     │ Reporting, dashboards│
└─────────────────────┴─────────────────────┴─────────────────────┘
```

---

---

# 9. Stored Procedures and Functions

---

## What They Are

Stored procedures and functions are named, reusable blocks of SQL
and logic stored inside the database itself.

Instead of writing the same SQL over and over in different places,
you write it once, save it in the database, and call it by name.

**Real-life analogy:**

```
Think of a stored procedure like a recipe saved in a cookbook.

Without it:
→ Every cook writes their own version of the dish
→ Some add too much salt, some forget ingredients
→ The result is inconsistent every time

With a saved recipe:
→ Everyone follows the same exact steps
→ The dish is consistent every time
→ If you improve the recipe, everyone benefits immediately

In a database:
→ The "recipe" is your SQL logic
→ The "cookbook" is the database
→ Every application that calls the procedure
  gets the same consistent result
```

---

## Functions — Return a Value

A function takes inputs and returns a calculated result.
Like a calculator — you give it numbers, it gives you an answer.

```sql
-- Syntax for creating a function
CREATE OR REPLACE FUNCTION function_name(
    parameter_name data_type
) RETURNS return_type
LANGUAGE plpgsql AS $$
DECLARE
    variable_name data_type;
BEGIN
    -- Your logic here
    RETURN result;
END;
$$;
```

**ShopSmart example — calculate discount for a customer:**

```sql
-- This function calculates the discount percentage
-- based on the customer's membership level

CREATE OR REPLACE FUNCTION fn_get_discount(
    p_membership VARCHAR(20)
) RETURNS NUMERIC(5, 2)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN CASE p_membership
        WHEN 'PLATINUM' THEN 15.00
        WHEN 'GOLD'     THEN 10.00
        WHEN 'STANDARD' THEN  5.00
        ELSE                   0.00
    END;
END;
$$;


-- Using the function
SELECT
    customer_id,
    full_name,
    membership,
    fn_get_discount(membership) AS discount_percentage
FROM customers
WHERE city = 'Riyadh'
LIMIT 10;

-- Output:
-- customer_id | full_name    | membership | discount_percentage
-- ------------+--------------+------------+--------------------
--        1001 | Ahmed...     | GOLD       |               10.00
--        1002 | Fatima...    | PLATINUM   |               15.00
--        1003 | Khalid...    | STANDARD   |                5.00
```

**Another function — calculate order total after discount:**

```sql
CREATE OR REPLACE FUNCTION fn_discounted_total(
    p_original_amount NUMERIC(10, 2),
    p_membership      VARCHAR(20)
) RETURNS NUMERIC(10, 2)
LANGUAGE plpgsql AS $$
DECLARE
    v_discount NUMERIC(5, 2);
BEGIN
    v_discount := fn_get_discount(p_membership);
    RETURN ROUND(p_original_amount * (1 - v_discount / 100), 2);
END;
$$;

-- Using both functions together
SELECT
    o.order_id,
    c.full_name,
    c.membership,
    o.total_amount                                    AS original_amount,
    fn_get_discount(c.membership)                    AS discount_pct,
    fn_discounted_total(o.total_amount, c.membership) AS discounted_amount
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'PENDING'
LIMIT 5;
```

---

## Stored Procedures — Perform a Series of Actions

A stored procedure performs a sequence of actions — inserts,
updates, validations — as one complete unit.

```sql
-- Syntax for creating a stored procedure
CREATE OR REPLACE PROCEDURE procedure_name(
    parameter_name data_type
)
LANGUAGE plpgsql AS $$
DECLARE
    variable_name data_type;
BEGIN
    -- Your steps here
    -- Validation
    -- Insert
    -- Update
    -- More operations
END;
$$;
```

**ShopSmart example — place a new order safely:**

```sql
-- This procedure places an order, reduces stock,
-- and records the payment — all in one atomic operation

CREATE OR REPLACE PROCEDURE sp_place_order(
    p_customer_id   INTEGER,
    p_product_id    INTEGER,
    p_quantity      INTEGER,
    p_channel       VARCHAR(20),
    p_payment_method VARCHAR(30)
)
LANGUAGE plpgsql AS $$
DECLARE
    v_price       NUMERIC(10, 2);
    v_stock       INTEGER;
    v_total       NUMERIC(10, 2);
    v_order_id    INTEGER;
BEGIN
    -- Step 1: Check product exists and has enough stock
    SELECT price, stock_qty
    INTO   v_price, v_stock
    FROM   products
    WHERE  product_id   = p_product_id
      AND  is_available = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Product % not found or not available',
                        p_product_id;
    END IF;

    IF v_stock < p_quantity THEN
        RAISE EXCEPTION 'Insufficient stock. Available: %, Requested: %',
                        v_stock, p_quantity;
    END IF;

    -- Step 2: Calculate total
    v_total := v_price * p_quantity;

    -- Step 3: Insert the order
    INSERT INTO orders (customer_id, order_date, order_status,
                        total_amount, channel)
    VALUES (p_customer_id, CURRENT_DATE, 'PENDING',
            v_total, p_channel)
    RETURNING order_id INTO v_order_id;

    -- Step 4: Insert order item
    INSERT INTO order_items (order_id, product_id, quantity,
                             unit_price, line_total)
    VALUES (v_order_id, p_product_id, p_quantity,
            v_price, v_total);

    -- Step 5: Reduce stock
    UPDATE products
    SET stock_qty = stock_qty - p_quantity
    WHERE product_id = p_product_id;

    -- Step 6: Record payment
    INSERT INTO payments (order_id, payment_date, payment_method,
                          payment_status, amount)
    VALUES (v_order_id, CURRENT_DATE, p_payment_method,
            'COMPLETED', v_total);

    RAISE NOTICE 'Order % placed successfully for SAR %',
                 v_order_id, v_total;
END;
$$;


-- Calling the procedure
CALL sp_place_order(
    1001,           -- customer_id
    5,              -- product_id
    2,              -- quantity
    'MOBILE',       -- channel
    'STC_PAY'       -- payment_method
);
-- Output: NOTICE: Order 50001 placed successfully for SAR 598.00
```

---

## Functions vs Procedures — Key Differences

```
┌─────────────────┬──────────────────────┬──────────────────────┐
│ Feature         │ Function             │ Procedure            │
├─────────────────┼──────────────────────┼──────────────────────┤
│ Returns         │ A value              │ Nothing (or INOUT)   │
│ Used in SELECT  │ Yes                  │ No                   │
│ Called with     │ SELECT fn_name()     │ CALL sp_name()       │
│ Best for        │ Calculations         │ Multi-step operations│
│ Example         │ Calculate discount   │ Place an order       │
└─────────────────┴──────────────────────┴──────────────────────┘
```

---

---

# 10. Transaction Control and ACID

---

## What a Transaction Is

A transaction is a group of SQL statements that are treated as
one single unit. Either ALL of them succeed together,
or NONE of them are applied.

**Real-life analogy:**

```
Imagine transferring money between two bank accounts.

Step 1: Deduct SAR 500 from Account A
Step 2: Add SAR 500 to Account B

These two steps MUST happen together.

If Step 1 succeeds but the system crashes before Step 2:
→ SAR 500 has vanished from Account A
→ SAR 500 has NOT appeared in Account B
→ SAR 500 has effectively disappeared
→ This is a financial disaster

A transaction prevents this:
→ Both steps happen atomically
→ If Step 2 fails, Step 1 is automatically undone
→ The money is never lost
```

---

## ACID — The Four Guarantees

Every transaction in PostgreSQL satisfies four properties.
Together they are called ACID.

### A — Atomicity

All operations succeed or all are rolled back. No partial state.

```sql
BEGIN; -- Start the transaction

-- Step 1: Place the order
INSERT INTO orders (customer_id, order_date, order_status,
                    total_amount, channel)
VALUES (1001, CURRENT_DATE, 'PENDING', 299.00, 'MOBILE');

-- Step 2: Reduce stock
UPDATE products
SET stock_qty = stock_qty - 1
WHERE product_id = 5;

-- Step 3: Record payment
INSERT INTO payments (order_id, payment_date, payment_method,
                      payment_status, amount)
VALUES (LASTVAL(), CURRENT_DATE, 'MADA', 'COMPLETED', 299.00);

COMMIT; -- All three succeed together

-- If ANY step fails between BEGIN and COMMIT,
-- ALL steps are automatically rolled back.
-- The order does not exist. The stock is not reduced.
-- The payment is not recorded.
```

### C — Consistency

The database always moves from one valid state to another.
Rules and constraints are always enforced.

```sql
-- The stock_qty column has a constraint: CHECK (stock_qty >= 0)
-- This means the database will NEVER allow negative stock

UPDATE products
SET stock_qty = stock_qty - 100
WHERE product_id = 5
  AND stock_qty = 3;  -- Only 3 in stock, trying to remove 100

-- Result: the constraint fires
-- ERROR: new row for relation "products" violates check constraint
-- The update is rejected. The database remains in a valid state.
-- You cannot accidentally create impossible data.
```

### I — Isolation

Concurrent transactions do not interfere with each other.

```sql
-- User A and User B both try to buy the last item in stock

-- Without isolation:
-- User A reads stock = 1
-- User B reads stock = 1  (before User A has updated it)
-- User A reduces stock: 1 - 1 = 0, commits
-- User B reduces stock: 1 - 1 = 0, commits
-- Result: stock = 0 but TWO orders were placed for one item

-- With proper isolation (FOR UPDATE lock):
-- User A reads stock = 1 WITH LOCK
-- User B waits for the lock
-- User A reduces stock to 0, commits
-- Lock released
-- User B reads stock = 0
-- User B's order fails: insufficient stock
-- One item, one sale — correct

SELECT stock_qty FROM products
WHERE product_id = 5
FOR UPDATE;  -- This locks the row until the transaction commits
             -- Other transactions must wait
```

### D — Durability

Once committed, data survives system crashes.

```sql
-- After COMMIT, your data is permanently saved
-- Even if the power goes out one millisecond after COMMIT,
-- PostgreSQL's Write-Ahead Log (WAL) ensures the data
-- is restored when the server restarts

COMMIT;
-- From this moment, the data is permanent.
-- Server crash, power failure, network failure —
-- the committed data will always be there when the
-- system comes back online.
```

---

## Transaction Syntax

```sql
-- Start a transaction
BEGIN;

-- Your SQL statements here
INSERT INTO ...;
UPDATE ...;
DELETE ...;

-- Option 1: Save all changes permanently
COMMIT;

-- Option 2: Undo ALL changes since BEGIN
ROLLBACK;
```

**Practical example — safe UPDATE with verification:**

```sql
-- Always test UPDATEs inside a transaction before committing

BEGIN;

-- See what we are about to change
SELECT product_id, product_name, price
FROM products
WHERE category = 'Electronics';

-- Make the change
UPDATE products
SET price = ROUND(price * 0.90, 2)  -- 10% discount
WHERE category = 'Electronics';

-- Verify the result looks correct
SELECT product_id, product_name, price
FROM products
WHERE category = 'Electronics';

-- If the results look correct:
COMMIT;

-- If something looks wrong:
-- ROLLBACK;
-- This puts everything back exactly as it was

-- This is the safe way to test any destructive SQL statement
```

---

---

# 11. Savepoints — Partial Rollback

---

## What a Savepoint Is

A savepoint is a checkpoint inside a transaction.
If something goes wrong after a savepoint, you can roll back
only to that checkpoint — not to the very beginning.

**Real-life analogy:**

```
Imagine writing a long document and saving it regularly.

Page 1 complete → Save (Savepoint 1)
Page 2 complete → Save (Savepoint 2)
Page 3 complete → Save (Savepoint 3)
Page 4: you make a terrible mistake

You undo back to the Save after page 3.
Pages 1, 2, and 3 are preserved.
Only page 4 is lost.

Without savepoints:
A mistake on page 4 undoes everything — back to a blank document.

With savepoints:
A mistake on page 4 only loses page 4.
Everything else is safely preserved.
```

---

## Why Savepoints Matter in Batch Processing

```
Real scenario: Processing 1000 customer orders in a nightly batch.

Order 1   → valid, insert succeeds → SAVEPOINT
Order 2   → valid, insert succeeds → SAVEPOINT
Order 3   → valid, insert succeeds → SAVEPOINT
...
Order 547 → invalid (customer not found) → ERROR

WITHOUT SAVEPOINTS:
→ The error causes a ROLLBACK of the entire batch
→ Orders 1 through 546 are all undone
→ The team arrives in the morning to find nothing was processed
→ The entire batch must be rerun

WITH SAVEPOINTS:
→ The error only rolls back Order 547
→ Orders 1 through 546 remain committed
→ Order 547 is logged as an error for manual review
→ The batch continues from Order 548
```

---

## Syntax

```sql
BEGIN;

-- Process Order 1
SAVEPOINT before_order_1;
INSERT INTO orders (...) VALUES (...);
-- Success: continue

-- Process Order 2
SAVEPOINT before_order_2;
INSERT INTO orders (...) VALUES (...);
-- Success: continue

-- Process Order 3 (this one will fail)
SAVEPOINT before_order_3;
INSERT INTO orders (...) VALUES (...);
-- FAILURE: invalid data

-- Roll back ONLY to before Order 3
-- Orders 1 and 2 are still intact
ROLLBACK TO SAVEPOINT before_order_3;

-- Log the failure (optional)
INSERT INTO error_log (failed_at, reason)
VALUES (CURRENT_TIMESTAMP, 'Order 3 failed: invalid customer');

-- Process Order 4
SAVEPOINT before_order_4;
INSERT INTO orders (...) VALUES (...);
-- Success: continue

COMMIT;
-- Orders 1, 2, and 4 are committed
-- Order 3 was rolled back but logged
```

---

## Releasing a Savepoint

```sql
-- Once you no longer need a savepoint, release it
-- This frees the memory used to track it

SAVEPOINT my_point;
INSERT INTO orders (...) VALUES (...);
-- Success — we no longer need to roll back to here

RELEASE SAVEPOINT my_point;
-- The savepoint is removed
-- The insert is still part of the transaction
-- and will commit or rollback with the whole transaction
```

---

---

# 12. Query Optimisation — Three Patterns

---

## Why Query Optimisation Matters

```
A query that returns the same result can take:
→ 0.001 seconds with good writing and proper indexes
→ 47 seconds with poor writing and no indexes

On a system with 1000 users running queries simultaneously,
the difference between these two is the difference between
a system that works and a system that is unusable.

Three patterns make the biggest difference in practice.
```

---

## Pattern 1 — Never Use SELECT *

**What SELECT * does:**

```sql
-- SELECT * fetches EVERY column in the table
-- Including columns you do not need
-- Including large text columns
-- Including sensitive data

SELECT * FROM customers WHERE city = 'Riyadh';

-- This fetches:
-- customer_id, full_name, email, city, country,
-- membership, is_active, registered_at, is_deleted,
-- deleted_at, deleted_reason, updated_at
-- ALL of these — even if you only need the name and email
```

**Why this is a problem:**

```
┌──────────────────────────────────────────────────────────┐
│ Problem 1 — Performance                                  │
│ More data transferred = slower query                     │
│ On 10,000 rows, the extra columns add up                 │
│                                                          │
│ Problem 2 — Security                                     │
│ You expose sensitive columns to users who should not     │
│ see them — email addresses, deletion reasons, etc.       │
│                                                          │
│ Problem 3 — Covering indexes cannot help                 │
│ A covering index works by including specific columns.    │
│ SELECT * bypasses this — it forces a table access        │
│ to get ALL columns, undoing the covering index benefit.  │
└──────────────────────────────────────────────────────────┘
```

**The fix:**

```sql
-- BAD: fetches everything including what you do not need
SELECT * FROM customers WHERE city = 'Riyadh';

-- GOOD: fetch only exactly what the consumer needs
SELECT customer_id, full_name, email, membership
FROM customers
WHERE city = 'Riyadh';

-- Rule: Always write out the column names you need.
-- If you are not sure which columns you need,
-- that is a sign to think more carefully about the query.
```

---

## Pattern 2 — Use EXISTS Instead of IN for Large Subqueries

**The problem with IN:**

```sql
-- This query finds customers who have a pending order
-- Using IN:

SELECT customer_id, full_name
FROM customers
WHERE customer_id IN (
    SELECT DISTINCT customer_id
    FROM orders
    WHERE order_status = 'PENDING'
);

-- What IN does internally:
-- Step 1: Run the subquery → build a list of ALL matching IDs
--         [1001, 1045, 1103, 2004, 2891, ... thousands more]
-- Step 2: For each customer, check if their ID is in the list
-- Must process ALL matching rows before returning any results
```

**The EXISTS alternative:**

```sql
-- The same result — using EXISTS:

SELECT customer_id, full_name
FROM customers c
WHERE EXISTS (
    SELECT 1  -- We do not care WHAT is returned
    FROM orders o  -- We only care IF a row exists
    WHERE o.customer_id = c.customer_id
      AND o.order_status = 'PENDING'
);

-- What EXISTS does internally:
-- For each customer, check if even ONE matching order exists
-- As soon as it finds ONE → stop looking, return TRUE
-- Does NOT need to process all matching rows
-- "Is there at least one? Yes? Stop. Move on."
```

**Visual comparison:**

```
IN:                              EXISTS:
┌─────────────────────────┐      ┌─────────────────────────┐
│ Build complete list:    │      │ For customer 1001:       │
│ [1001,1045,1103,2004...]│      │ → Check order 1: PENDING │
│ All 5000 matching rows  │      │ → Found! Stop. Return YES│
│ must be processed first │      │                          │
│ Then check each customer│      │ For customer 1002:       │
│ against the full list   │      │ → Check order 1: DELIVERED│
└─────────────────────────┘      │ → Check order 2: CANCELLED│
Much more work                   │ → No PENDING found. No.  │
                                 └─────────────────────────┘
                                 Only checks until it finds one
                                 Less work overall
```

**When does it matter most:**

```sql
-- On a small table (100 rows): barely noticeable difference
-- On a large table (10 million rows): EXISTS can be
-- many times faster than IN

-- Use EXISTS when:
-- → The subquery table has many rows
-- → You are checking for existence (not collecting values)
-- → Performance of the query matters
```

---

## Pattern 3 — Window Functions Instead of Self-Joins

**The problem — self-join for running totals:**

```sql
-- We want to see each customer's running total spending
-- across their orders — how much have they spent so far
-- up to and including each order

-- SLOW WAY: Self-join
-- For every order, sum all orders placed before it
-- The orders table is joined to itself

SELECT
    o1.order_id,
    o1.order_date,
    o1.total_amount,
    SUM(o2.total_amount) AS running_total
FROM orders o1
JOIN orders o2
    ON  o2.customer_id = o1.customer_id
    AND o2.order_date <= o1.order_date
WHERE o1.customer_id = 500
GROUP BY o1.order_id, o1.order_date, o1.total_amount
ORDER BY o1.order_date;

-- What this does:
-- For Order 1 (Jan): sum Jan = SAR 299
-- For Order 2 (Feb): re-read Jan + Feb = SAR 598
-- For Order 3 (Mar): re-read Jan + Feb + Mar = SAR 897
-- It keeps going back to the beginning for every row.
-- Extremely inefficient at scale.
```

**The solution — window function:**

```sql
-- FAST WAY: Window function
-- Makes ONE pass through the data
-- Computes the running total as it goes

SELECT
    order_id,
    order_date,
    total_amount,
    SUM(total_amount) OVER (
        PARTITION BY customer_id   -- Reset per customer
        ORDER BY order_date        -- Accumulate in date order
    ) AS running_total
FROM orders
WHERE customer_id = 500
ORDER BY order_date;

-- What this does:
-- Makes one pass through orders for customer 500
-- Adds each order's amount to a running sum as it goes
-- Jan: 299 → running total = 299
-- Feb: 299 → running total = 598
-- Mar: 299 → running total = 897
-- One pass. Much faster.
```

**Understanding the window function syntax:**

```sql
SUM(total_amount) OVER (
    PARTITION BY customer_id  -- "Reset the sum for each customer"
    ORDER BY order_date       -- "Add up in date order"
)

-- OVER        → "this is a window function, not a regular aggregate"
-- PARTITION BY → "treat each group independently"
--               like GROUP BY but without collapsing rows
-- ORDER BY    → "define the order of accumulation"

-- Other useful window functions:
-- ROW_NUMBER() OVER (...) → sequential number within each group
-- RANK()       OVER (...) → rank with gaps for ties
-- LAG()        OVER (...) → value from the previous row
-- LEAD()       OVER (...) → value from the next row
-- MAX()        OVER (...) → running maximum
-- MIN()        OVER (...) → running minimum
```

**Practical ShopSmart example:**

```sql
-- Show each customer's orders with their rank and running total
SELECT
    c.full_name,
    c.membership,
    o.order_id,
    o.order_date,
    o.total_amount,
    ROW_NUMBER() OVER (
        PARTITION BY o.customer_id
        ORDER BY o.order_date
    )                               AS order_number,
    SUM(o.total_amount) OVER (
        PARTITION BY o.customer_id
        ORDER BY o.order_date
    )                               AS cumulative_spending,
    RANK() OVER (
        PARTITION BY o.customer_id
        ORDER BY o.total_amount DESC
    )                               AS largest_order_rank
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.customer_id IN (1, 2, 3)
  AND o.order_status = 'DELIVERED'
ORDER BY o.customer_id, o.order_date;
```

---

---

# 13. EXPLAIN ANALYZE — Reading the Execution Plan

---

## What EXPLAIN ANALYZE Does

EXPLAIN ANALYZE runs your query and shows you the complete
execution plan — exactly what strategy PostgreSQL chose,
how long each step took, and how many rows were processed.

**Real-life analogy:**

```
Think of EXPLAIN ANALYZE like a GPS journey report.

Not just the route — but:
→ Which roads you took
→ How fast you travelled on each road
→ Where you got stuck in traffic
→ Which junction cost the most time
→ What your actual arrival time was vs the estimated time

EXPLAIN ANALYZE gives you the same level of detail
about your SQL query execution.
```

---

## How to Use It

```sql
-- Simply add EXPLAIN ANALYZE before any SELECT query
-- It runs the query and shows the execution plan

EXPLAIN ANALYZE
SELECT customer_id, full_name, city
FROM customers
WHERE membership = 'GOLD'
  AND is_active = TRUE;
```

---

## Reading the Output — Line by Line

```
When you run EXPLAIN ANALYZE you will see output like this:

Seq Scan on customers
  (cost=0.00..236.00 rows=900 width=42)
  (actual time=0.021..4.123 rows=913 loops=1)
  Filter: ((membership = 'GOLD') AND (is_active = TRUE))
  Rows Removed by Filter: 9087
Planning Time: 0.8 ms
Execution Time: 4.4 ms

Let us understand each part:
```

**Node type — what strategy was used:**

```
Seq Scan on customers
↑
This tells you HOW the database found the data.

Seq Scan         = Sequential Scan
                   Read every row in the table one by one
                   BAD for large tables
                   GOOD only for very small tables

Index Scan       = The database used an index
                   Jumped directly to matching rows
                   GOOD

Index Only Scan  = Used a covering index
                   Never even touched the main table
                   BEST

Bitmap Heap Scan = Used an index for many matching rows
                   Good for queries returning many results
```

**Cost estimate:**

```
(cost=0.00..236.00 rows=900 width=42)
       ↑      ↑       ↑        ↑
  start  end  estimated  bytes per
  cost   cost   rows      row

cost = PostgreSQL's internal estimate of work required
       Higher cost = more work = potentially slower
       These are relative numbers, not milliseconds

rows = How many rows PostgreSQL thinks it will return
       Compare this to "actual rows" below

width = Average bytes per returned row
        Larger = more data to transfer
        SELECT * has much higher width than specific columns
```

**Actual results:**

```
(actual time=0.021..4.123 rows=913 loops=1)
              ↑       ↑      ↑       ↑
         time to   time to  rows   how many
         first row last row found  times run

actual time = Real milliseconds taken
              0.021 = time to return first row
              4.123 = time to return all rows

rows = How many rows were actually found
       Compare to estimated rows above

loops = How many times this step was repeated
        loops=1 means it ran once
        loops=50000 means it ran 50,000 times (nested loop join)
```

**The most important line:**

```
Rows Removed by Filter: 9087

This tells you how much wasted work happened.
The database read 9,087 rows that did not match your WHERE clause.
It read 10,000 rows total, found 913 matches, threw away 9,087.

If this number is large → you need an index on the filter column.
If this number is small → your query is efficient.
```

**The bottom line:**

```
Planning Time: 0.8 ms   ← Time to decide the execution plan
Execution Time: 4.4 ms  ← Time to actually run the query

Total time your user waited: ~5.2 ms

This is the number you want to minimise.
Always note this before and after adding an index.
```

---

## The Complete Cheat Sheet

```
┌─────────────────────────────────────────────────────────────────┐
│ NODE TYPES — What strategy PostgreSQL chose                     │
├─────────────────────────┬───────────────────────────────────────┤
│ Seq Scan                │ Reading every row — add an index      │
│ Index Scan              │ Using an index — good                 │
│ Index Only Scan         │ Covering index — best possible        │
│ Bitmap Heap Scan        │ Index + many rows — acceptable        │
│ Hash Join               │ Joining large tables — normal         │
│ Nested Loop             │ Joining small result sets — fast      │
│ Merge Join              │ Joining pre-sorted data — efficient   │
└─────────────────────────┴───────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ NUMBERS — What to look for                                      │
├─────────────────────────┬───────────────────────────────────────┤
│ Execution Time          │ Total time — the number that matters  │
│ Rows Removed by Filter  │ High = you need an index              │
│ Estimated ≠ Actual rows │ Big gap = stale statistics            │
│                         │ Fix: ANALYZE table_name               │
│ loops = large number    │ Nested loop on big table = slow       │
└─────────────────────────┴───────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ WHAT TO DO — Your action guide                                  │
├─────────────────────────┬───────────────────────────────────────┤
│ See Seq Scan on a large │ Add an index on the WHERE column      │
│ table                   │                                       │
│ High Rows Removed by    │ Create an index to avoid the scan     │
│ Filter                  │                                       │
│ Estimated far from      │ Run: ANALYZE table_name               │
│ Actual rows             │ Then run EXPLAIN ANALYZE again        │
│ Long execution time on  │ Look for the most expensive node,     │
│ a join query            │ add index on the join column          │
│ Index Scan but still    │ Try a covering index with INCLUDE      │
│ slow                    │ to avoid heap fetches                 │
└─────────────────────────┴───────────────────────────────────────┘
```

---

## A Complete Before and After Example

```sql
-- BEFORE: No indexes — find top spending customers last 30 days

EXPLAIN ANALYZE
SELECT
    c.full_name,
    c.city,
    c.membership,
    COUNT(o.order_id)   AS order_count,
    SUM(o.total_amount) AS total_spending
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date   >= CURRENT_DATE - INTERVAL '30 days'
  AND o.order_status  = 'DELIVERED'
GROUP BY c.customer_id, c.full_name, c.city, c.membership
ORDER BY total_spending DESC
LIMIT 10;

-- You will see:
-- Seq Scan on orders        ← Reading all 50,000 orders
-- Rows Removed by Filter: many thousands
-- Execution Time: several milliseconds to seconds


-- ADD THE RIGHT INDEXES:
CREATE INDEX idx_orders_date_status
ON orders (order_date DESC, order_status)
WHERE order_status = 'DELIVERED';

CREATE INDEX idx_orders_customer_fk
ON orders (customer_id);

ANALYZE orders;


-- AFTER: Same query with indexes

EXPLAIN ANALYZE
SELECT
    c.full_name,
    c.city,
    c.membership,
    COUNT(o.order_id)   AS order_count,
    SUM(o.total_amount) AS total_spending
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date   >= CURRENT_DATE - INTERVAL '30 days'
  AND o.order_status  = 'DELIVERED'
GROUP BY c.customer_id, c.full_name, c.city, c.membership
ORDER BY total_spending DESC
LIMIT 10;

-- You will now see:
-- Index Scan using idx_orders_date_status  ← Using the index
-- Rows Removed by Filter: zero or very few
-- Execution Time: much lower than before

-- The query result is IDENTICAL.
-- The performance is dramatically better.
-- This is the entire purpose of query optimisation.
```

---

---

## Final Summary — All Topics at a Glance

```
┌──────────────────────┬────────────────────────────────────────┐
│ Topic                │ The One Thing to Remember              │
├──────────────────────┼────────────────────────────────────────┤
│ Database Creation    │ Always use UTF8 encoding               │
│ Schemas              │ Separate rooms = separate access       │
│ Data Types           │ NUMERIC for money. Never FLOAT.        │
│ VARCHAR vs CHAR      │ Fixed-length codes → CHAR.  Rest → VARCHAR│
│ TIMESTAMPTZ          │ Always for event timestamps            │
│ Natural Key          │ Real-world stable identifier           │
│ Surrogate Key        │ Auto-generated number — fast and simple│
│ UUID                 │ Globally unique — for distributed systems│
│ Single Index         │ One column → one index                 │
│ Composite Index      │ Multiple columns → first column matters│
│ Partial Index        │ Exclude rows you never query           │
│ Covering Index       │ All needed columns → no table visit    │
│ Unique Index         │ Prevent duplicate values               │
│ Partitioning         │ Split by date → query one year, not all│
│ INSERT               │ Always list your columns explicitly    │
│ RETURNING            │ Get the inserted row back immediately  │
│ UPDATE               │ Always use WHERE — or update everything│
│ Soft Delete          │ Set is_deleted = TRUE, never hard delete│
│ Views                │ Save a query — query it like a table   │
│ Materialised Views   │ Store the result — refresh on schedule │
│ Functions            │ Calculation that returns a value       │
│ Stored Procedures    │ Multi-step operation called by name    │
│ Atomicity            │ All succeed or all fail                │
│ Consistency          │ Rules always enforced                  │
│ Isolation            │ Concurrent changes do not interfere    │
│ Durability           │ Committed data survives crashes        │
│ BEGIN / COMMIT       │ Wrap related operations together       │
│ ROLLBACK             │ Undo everything since BEGIN            │
│ Savepoints           │ Undo part of a transaction             │
│ Never SELECT *       │ Always specify column names            │
│ EXISTS over IN       │ Stops at first match — faster          │
│ Window Functions     │ One pass — no self-join needed         │
│ EXPLAIN ANALYZE      │ Run before deploying any query         │
│ Seq Scan             │ BAD on large tables — add an index     │
│ Index Only Scan      │ BEST — covering index working perfectly│
└──────────────────────┴────────────────────────────────────────┘
```

---

> **You have reached the end of this guide.**
>
> Every concept in this document connects directly to real work
> that data engineers do every day. The difference between a
> system that struggles and one that performs beautifully often
> comes down to exactly these decisions — the right data type,
> the right index, the right query pattern.
>
> We hope this guide has made these concepts clear and accessible.
> Please keep it with you as a reference throughout the programme
> and beyond.
>
> You are doing excellent work. Keep going.

---

*SNB Data Management Capability Programme*
*Delivered by Fitch Learning*