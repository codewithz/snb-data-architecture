# SNB Data Engineering Programme
## Guided Lab 3B — Write SQL Queries and Optimise Performance
### Day 3 | Al-Noor Bank Database

---

> **Welcome to Lab 3B.**
>
> In this lab you will write five SQL queries against the
> Al-Noor Bank database you built in Lab 3A.
>
> Each query answers a real business question that a Saudi
> bank needs every single day — compliance reporting, risk
> monitoring, AML detection, and performance optimisation.
>
> The full solution is shown for each query with a line-by-line
> explanation. Try writing the query yourself first, then
> compare your version with the solution.
> Your version does not need to be identical — there is often
> more than one correct way to write a query.
>
> Please read every comment. That is where the learning lives.

---

## Before You Begin

Make sure your al_noor_bank database from Lab 3A is open
in pgAdmin. All five queries run against that database.

---

## Query 1 — KYC Overdue Report

**The business question:**
*"Which high-risk customers have not had their KYC reviewed
in the last 12 months? Show their name, branch, and how
many days overdue they are."*

**Why this matters:**
SAMA requires high-risk customers (risk_rating = 'H') to undergo
KYC review every 12 months. An overdue customer cannot be offered
new products and may have their account frozen until review is
completed. The compliance team runs this report every morning.

---

```sql
-- ============================================================
-- HOW TO READ THIS QUERY:
--
-- FROM retail.customer c
--   Start with the customer table. 'c' is an alias —
--   a short name we use to reference the table later.
--
-- JOIN retail.branch b ON c.branch_id = b.branch_id
--   Connect each customer to their branch.
--   'b' is the alias for branch.
--
-- WHERE c.risk_rating = 'H'
--   Only high-risk customers — annual review required.
--
-- AND c.kyc_last_reviewed < CURRENT_DATE - INTERVAL '12 months'
--   Only customers whose last review was more than 12 months ago.
--   CURRENT_DATE is today's date. Subtracting 12 months gives
--   the cutoff date — anyone reviewed before that date is overdue.
--
-- AND c.is_deleted = FALSE
--   Exclude soft-deleted customers.
--   Always include this filter on customer queries or you will
--   accidentally include closed accounts in your results.
--
-- CURRENT_DATE - c.kyc_last_reviewed
--   PostgreSQL subtracts two dates and returns the result
--   in days as an integer. This gives us days since last review.
--
-- (...) - 365 AS days_overdue
--   Subtracting 365 tells us how many days OVERDUE they are.
--   A customer reviewed 400 days ago is 35 days overdue.
--
-- ORDER BY days_since_review DESC
--   Most overdue customers appear first.
-- ============================================================

SELECT
    c.customer_id,
    c.full_name_en,
    c.risk_rating,
    c.kyc_last_reviewed,
    CURRENT_DATE - c.kyc_last_reviewed        AS days_since_review,
    (CURRENT_DATE - c.kyc_last_reviewed) - 365 AS days_overdue,
    b.branch_name,
    b.city
FROM retail.customer c
JOIN retail.branch b
    ON c.branch_id = b.branch_id
WHERE c.risk_rating = 'H'
  AND c.kyc_last_reviewed < CURRENT_DATE - INTERVAL '12 months'
  AND c.is_deleted = FALSE
ORDER BY days_since_review DESC;
```

**Expected output:**
One row — Khalid Al-Qahtani.

```
 customer_id | full_name_en      | risk_rating | kyc_last_reviewed | days_since_review | days_overdue | branch_name        | city
-------------+-------------------+-------------+-------------------+-------------------+--------------+--------------------+-------
 C000000003  | Khalid Al-Qahtani | H           | 2022-11-15        | 850+              | 480+         | Riyadh Main Branch | Riyadh
```

The exact numbers depend on today's date — but Khalid's review was
in November 2022, so he is significantly overdue.

**Key lesson:**
The `is_deleted = FALSE` filter is not optional. Without it, the query
returns soft-deleted customers alongside active ones. In a bank with
millions of customers, this could mean thousands of closed accounts
appearing in a compliance report — wasted time and false alerts.

---

## Query 2 — Murabaha Exposure by Customer Segment

**The business question:**
*"How much outstanding Murabaha financing does each customer segment
hold? Show the number of active contracts and the total amount still
owed."*

**Why this matters:**
Risk management needs this to monitor Islamic finance exposure
per segment and ensure it stays within SAMA capital adequacy limits.

---

```sql
-- ============================================================
-- HOW TO READ THIS QUERY:
--
-- FROM finance.murabaha_contract mc
--   Start with the Murabaha contracts table. 'mc' is the alias.
--
-- JOIN retail.customer c ON mc.customer_id = c.customer_id
--   Connect each contract to its customer to get the segment.
--
-- LEFT JOIN (...) ms_pending
--   A LEFT JOIN includes ALL rows from the left table
--   even when there is no match on the right side.
--   Here: even contracts with no PENDING instalments still
--   appear in the result (with NULL for pending amount).
--   This is the correct choice — we want to see all contracts,
--   not just those with outstanding balances.
--
-- THE SUBQUERY (inside the LEFT JOIN):
--   SELECT contract_id, SUM(instalment_sar) AS pending_amount
--   FROM finance.murabaha_schedule
--   WHERE status = 'PENDING'
--   GROUP BY contract_id
--
--   This calculates the total amount still owed per contract.
--   It sums only PENDING instalments — PAID ones are excluded.
--
-- COALESCE(SUM(ms_pending.pending_amount), 0)
--   COALESCE returns the first non-NULL value.
--   If a contract has no PENDING instalments, the LEFT JOIN
--   returns NULL for pending_amount. COALESCE converts that
--   NULL to 0 so the total shows 0 instead of NULL.
--
-- WHERE mc.status = 'ACTIVE'
--   Only active contracts — settled ones are excluded.
-- ============================================================

SELECT
    c.customer_segment,
    COUNT(DISTINCT mc.contract_id)                AS active_contracts,
    SUM(mc.total_sale_price)                      AS total_portfolio_sar,
    COALESCE(SUM(ms_pending.pending_amount), 0)   AS total_outstanding_sar
FROM finance.murabaha_contract mc
JOIN retail.customer c
    ON mc.customer_id = c.customer_id
LEFT JOIN (
    SELECT
        contract_id,
        SUM(instalment_sar) AS pending_amount
    FROM finance.murabaha_schedule
    WHERE status = 'PENDING'
    GROUP BY contract_id
) ms_pending
    ON mc.contract_id = ms_pending.contract_id
WHERE mc.status = 'ACTIVE'
GROUP BY c.customer_segment
ORDER BY total_outstanding_sar DESC;
```

**Expected output:**
One row — PREMIUM segment — because Ahmed (PREMIUM) is the only
customer with an active Murabaha contract.

```
 customer_segment | active_contracts | total_portfolio_sar | total_outstanding_sar
------------------+------------------+---------------------+-----------------------
 PREMIUM          |                1 |            90000.00 |               3750.00
```

total_portfolio_sar = 90,000 (the full contract value)
total_outstanding_sar = 3,750 (only instalment 3 is PENDING)

---

## Query 3 — Top 10 Accounts by Transaction Volume (Last 30 Days)

**The business question:**
*"Which accounts had the highest transaction volume in the last
30 days? Show account type, customer name, and segment."*

**Why this matters:**
Operations management uses this to identify high-value accounts
for priority service and to detect unusual volume spikes that may
warrant AML investigation.

---

```sql
-- ============================================================
-- HOW TO READ THIS QUERY:
--
-- We join 4 tables in a chain:
-- account → customer_account → customer → transaction
--
-- JOIN retail.customer_account ca
--     ON a.account_id = ca.account_id
--     AND ca.relationship = 'PRIMARY'
--   The AND condition filters to PRIMARY account holders only.
--   Without this, a joint account with 2 customers would count
--   the same transactions twice — one for each customer.
--   We only want the PRIMARY holder's branch counted.
--
-- WHERE t.txn_date >= CURRENT_DATE - INTERVAL '30 days'
--   Only transactions from the last 30 days.
--
-- WHERE t.status = 'POSTED'
--   Only confirmed, settled transactions.
--   PENDING and FAILED transactions are excluded because
--   they have not actually moved money yet.
--
-- GROUP BY all non-aggregated columns
--   We must list every column in SELECT that is NOT inside
--   a COUNT() or SUM() function here in GROUP BY.
--
-- ORDER BY total_volume_sar DESC
--   Highest volume accounts appear first.
--
-- LIMIT 10
--   Return only the top 10 results.
-- ============================================================

SELECT
    a.account_id,
    a.account_number,
    a.account_type,
    c.full_name_en,
    c.customer_segment,
    COUNT(t.txn_id)    AS transaction_count,
    SUM(t.amount_sar)  AS total_volume_sar
FROM retail.account a
JOIN retail.customer_account ca
    ON a.account_id = ca.account_id
    AND ca.relationship = 'PRIMARY'
JOIN retail.customer c
    ON ca.customer_id = c.customer_id
JOIN retail.transaction t
    ON a.account_id = t.account_id
WHERE t.txn_date >= CURRENT_DATE - INTERVAL '30 days'
  AND t.status = 'POSTED'
GROUP BY
    a.account_id, a.account_number, a.account_type,
    c.full_name_en, c.customer_segment
ORDER BY total_volume_sar DESC
LIMIT 10;
```

**Expected output:**
ACC0000000000001 (Ahmed's account) — it has the most transactions
within the last 30 days.

```
    account_id     | account_type | full_name_en  | customer_segment | transaction_count | total_volume_sar
-------------------+--------------+---------------+------------------+-------------------+------------------
 ACC0000000000001  | CURRENT      | Ahmed Al-Omari| PREMIUM          |                 4 |         22950.00
```

(Only transactions within the last 30 days are counted.
The exact count depends on today's date.)

---

## Query 4 — Structuring Detection (AML Pattern)

**The business question:**
*"Find accounts with 3 or more transactions on the same day,
each between SAR 10,000 and SAR 59,999. This pattern suggests
the customer is deliberately splitting a large transfer to
stay below the SAR 60,000 SAMA reporting threshold."*

**Why this matters:**
Structuring (also called smurfing) is a financial crime in Saudi
Arabia. SAR 60,000 is the threshold above which banks must report
to SAMA. Splitting one SAR 80,000 transfer into four SAR 20,000
transfers to avoid the report is illegal — and detectable with SQL.

---

```sql
-- ============================================================
-- HOW TO READ THIS QUERY:
--
-- STEP 1: The CTE (WITH daily_activity AS ...)
-- A CTE is a named temporary result that we define once
-- and reference in the main query below.
-- Think of it as giving a name to a subquery.
--
-- Inside the CTE:
-- GROUP BY t.account_id, t.txn_date
--   We group by account and day — we want to see all
--   transactions for the same account on the same day together.
--
-- WHERE t.amount_sar BETWEEN 10000 AND 59999
--   The lower bound: large enough to be suspicious.
--   The upper bound: just below the SAR 60,000 reporting
--   threshold. This is the structuring range.
--
-- AND t.direction = 'D'
--   Debit only — money going OUT of the account.
--   Structuring is about moving money out while avoiding reports.
--
-- HAVING COUNT(*) >= 3
--   HAVING filters on the result of GROUP BY.
--   We only want account-day combinations with 3 or more
--   transactions in the suspicious range.
--   (WHERE filters before grouping. HAVING filters after.)
--
-- STEP 2: The main SELECT
-- Joins the CTE results to get account and customer details.
-- We join customer_account with relationship = 'PRIMARY'
-- to avoid counting joint holders twice.
-- ============================================================

WITH daily_activity AS (
    SELECT
        t.account_id,
        t.txn_date,
        COUNT(*)          AS txn_count,
        SUM(t.amount_sar) AS daily_total_sar,
        MIN(t.amount_sar) AS min_txn_sar,
        MAX(t.amount_sar) AS max_txn_sar
    FROM retail.transaction t
    WHERE t.amount_sar BETWEEN 10000 AND 59999
      AND t.direction = 'D'
      AND t.status    = 'POSTED'
    GROUP BY t.account_id, t.txn_date
    HAVING COUNT(*) >= 3
)
SELECT
    da.account_id,
    a.account_number,
    c.full_name_en,
    c.risk_rating,
    da.txn_date,
    da.txn_count,
    da.daily_total_sar,
    da.min_txn_sar,
    da.max_txn_sar
FROM daily_activity da
JOIN retail.account a
    ON da.account_id = a.account_id
JOIN retail.customer_account ca
    ON a.account_id = ca.account_id
    AND ca.relationship = 'PRIMARY'
JOIN retail.customer c
    ON ca.customer_id = c.customer_id
ORDER BY da.daily_total_sar DESC;
```

**Expected output with current data:** No rows.
Our sample data does not have 3+ large debits on the same day.
This is correct — the query is working as designed.

**To see the query detect a real pattern, insert test data:**

```sql
-- Add 3 large debits on the same day for Khalid's account
-- This simulates a structuring pattern:
-- 3 transactions of ~SAR 19,000-20,000 on the same day
-- totalling SAR 58,500 — just below SAR 60,000

INSERT INTO retail.transaction
    (account_id, txn_date, txn_type, amount_sar,
     direction, balance_after, channel, narrative, status)
VALUES
    ('ACC0000000000003','2025-03-15','DEBIT',
     19000.00,'D',5750.00,'BRANCH','Cash withdrawal','POSTED'),

    ('ACC0000000000003','2025-03-15','DEBIT',
     19500.00,'D',5750.00,'ATM','ATM withdrawal','POSTED'),

    ('ACC0000000000003','2025-03-15','DEBIT',
     20000.00,'D',5750.00,'MOBILE','Transfer out','POSTED');
```

Now re-run the structuring detection query above.

**Expected output after test data:**

```
    account_id     | full_name_en      | risk_rating | txn_date   | txn_count | daily_total_sar
-------------------+-------------------+-------------+------------+-----------+----------------
 ACC0000000000003  | Khalid Al-Qahtani | H           | 2025-03-15 |         3 |       58500.00
```

Khalid already has an open AML alert (from Lab 3A).
Three large transactions on the same day confirms the pattern.
In a live system, this would trigger an automatic escalation.

---

## Query 5 — EXPLAIN ANALYZE: Before and After an Index

**The business question:**
*"Is our structuring detection query fast enough for production?
Let us measure it and then make it faster."*

**Why this matters:**
A query that runs in milliseconds on our 9-row test database
could take minutes on a production database with hundreds of
millions of transactions. EXPLAIN ANALYZE shows the difference
between a fast and slow execution plan — before you deploy.

---

### Step A — Run EXPLAIN ANALYZE Before Adding an Index

```sql
-- ============================================================
-- EXPLAIN ANALYZE runs your query AND shows the execution plan.
-- It is the GPS journey report for your SQL.
--
-- KEY THINGS TO LOOK FOR:
--
-- "Seq Scan" → Sequential Scan
--   The database is reading EVERY row in the table.
--   On 9 rows this is fine. On 500 million rows it is very slow.
--
-- "Rows Removed by Filter: N"
--   How many rows were read but thrown away because they
--   did not match the WHERE clause. High number = wasted work.
--
-- "Execution Time: X ms"
--   The total time the query took to run.
--   Write this number down. We will compare it after the index.
-- ============================================================

EXPLAIN ANALYZE
WITH daily_activity AS (
    SELECT
        t.account_id,
        t.txn_date,
        COUNT(*)          AS txn_count,
        SUM(t.amount_sar) AS daily_total_sar
    FROM retail.transaction t
    WHERE t.amount_sar BETWEEN 10000 AND 59999
      AND t.direction = 'D'
      AND t.status    = 'POSTED'
    GROUP BY t.account_id, t.txn_date
    HAVING COUNT(*) >= 3
)
SELECT da.* FROM daily_activity da;
```

**What you will see:**

```
Seq Scan on transaction_2025
  Filter: ((amount_sar BETWEEN 10000 AND 59999)
           AND (direction = 'D')
           AND (status = 'POSTED'))
  Rows Removed by Filter: [most rows]

Execution Time: [X] ms
```

The database read every row and filtered most of them out.
Every row removed by filter is wasted work.

---

### Step B — Create the Index

```sql
-- ============================================================
-- CREATING A PARTIAL INDEX FOR STRUCTURING DETECTION
--
-- WHY PARTIAL (WHERE status = 'POSTED')?
-- 99.9% of all transactions are POSTED.
-- A full index would include all rows including PENDING,
-- REVERSED, and FAILED — which the query never needs.
-- The partial index contains ONLY POSTED rows.
-- Much smaller. Much faster.
--
-- WHY THESE COLUMNS?
-- The query filters on:
--   amount_sar BETWEEN 10000 AND 59999
--   direction = 'D'
--   status = 'POSTED' (handled by the partial index condition)
-- And groups by:
--   account_id, txn_date
-- Including all of these lets PostgreSQL potentially answer
-- the query entirely from the index — never reading the table.
-- ============================================================

CREATE INDEX idx_txn_structuring
    ON retail.transaction (account_id, txn_date, amount_sar, direction)
    WHERE status = 'POSTED';

-- Always run ANALYZE after creating an index on a table
-- that already has data. This updates the statistics so
-- PostgreSQL knows the index exists and uses it.
ANALYZE retail.transaction;
```

---

### Step C — Run EXPLAIN ANALYZE After the Index

```sql
-- Run the exact same query again
-- and compare the output to Step A

EXPLAIN ANALYZE
WITH daily_activity AS (
    SELECT
        t.account_id,
        t.txn_date,
        COUNT(*)          AS txn_count,
        SUM(t.amount_sar) AS daily_total_sar
    FROM retail.transaction t
    WHERE t.amount_sar BETWEEN 10000 AND 59999
      AND t.direction = 'D'
      AND t.status    = 'POSTED'
    GROUP BY t.account_id, t.txn_date
    HAVING COUNT(*) >= 3
)
SELECT da.* FROM daily_activity da;
```

**What changed in the output:**

```
-- BEFORE (no index):
-- Seq Scan on transaction_2025
-- Execution Time: X ms

-- AFTER (with index):
-- Index Scan using idx_txn_structuring on transaction_2025
-- Execution Time: much lower
```

On our small dataset the difference may appear small — PostgreSQL
is smart enough to use a sequential scan on tiny tables where it
is actually faster. The real benefit appears at production scale.

**The key lesson:**
The partial index (WHERE status = 'POSTED') is a fraction of the
size of a full index on the same columns. It excludes all the rows
the query never needs. Smaller index = fits in memory = faster search.

---

### EXPLAIN ANALYZE Quick Reference

```
What you see               What it means           What to do
───────────────────────────────────────────────────────────────
Seq Scan on large table    Reading every row        Add an index
Index Scan using idx_name  Index being used         Good
Index Only Scan            Covering index used      Best possible
Rows Removed by Filter: N  Wasted work              Add an index
Actual ≠ Estimated rows    Stale statistics         Run ANALYZE
High Execution Time        Query is slow            Check the plan
```

---

## Lab 3B Complete

```
✅ Query 1: KYC overdue report → Khalid Al-Qahtani surfaced
✅ Query 2: Murabaha exposure by segment → PREMIUM portfolio
✅ Query 3: Top accounts by volume → Ahmed's account
✅ Query 4: Structuring detection → AML pattern in SQL
✅ Query 5: EXPLAIN ANALYZE → before and after index creation
```

> You have written five production-grade SQL queries that real
> banking teams run every day. Well done.
> Lab 3C builds the reporting views on top of these results.

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*