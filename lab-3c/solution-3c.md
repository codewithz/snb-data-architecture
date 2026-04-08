# SNB Data Engineering Programme
## Guided Lab 3C — Build Three Reporting Views

**Time: 30 minutes**
**Prerequisite: Labs 3A and 3B must be complete**

---

> **Welcome to Lab 3C.**
>
> In this lab you will build three reporting views for the
> Al-Noor Bank analytics schema. These views are the interface
> between the raw banking data and the people who need to
> make decisions from it every day.
>
> A compliance officer should not need to know how to write
> a twelve-table JOIN. A view gives them a simple, consistent,
> governed window into the data they need.
>
> Every view is fully explained before the SQL is shown.
> Read each explanation carefully — it tells you who uses
> the view, why it was designed this way, and what decisions
> were made in writing it.

---

## What You Will Build

```
View 1 → analytics.v_customer_risk_summary
         Who uses it:  Risk Management, SAMA reporting team
         What it shows: Customer counts, balances, and Murabaha
                        exposure grouped by risk rating and segment
         Key design:   No customer names — aggregated only

View 2 → analytics.v_murabaha_overdue
         Who uses it:  Collections team, SAMA NPF reporting
         What it shows: Every overdue Murabaha instalment with
                        the SAMA NPF 90-day flag
         Key design:   SAMA regulatory definition encoded directly

View 3 → analytics.v_daily_txn_volume
         Who uses it:  Operations team, SAMA periodic reporting
         What it shows: Transaction counts and volumes for last
                        30 days by type and channel
         Key design:   Candidate for materialised view at scale
```

---

## Before You Begin

Make sure you are connected to the **al_noor_bank** database
in pgAdmin. All three views are created in the **analytics** schema.

Run this to confirm the schema exists:

```sql
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name = 'analytics';
```

**Expected:** One row with schema_name = analytics.
If not found, run: `CREATE SCHEMA analytics;`

---

## View 1 — Customer Risk Summary

### Who Uses It
The Risk Management team and the SAMA regulatory reporting team.
Used as an input to capital adequacy calculations and portfolio
risk monitoring reports.

### Why No Customer Names?

This view contains no names, no national IDs, no personal
identifiers of any kind. It is a pure aggregation.

Under the PDPL data minimisation principle, this view can be
granted to a broader audience than a view containing personal data.
A risk analyst who needs to know how many PREMIUM HIGH-risk
customers exist does not need to know their names.

This is data protection by design — the view structure itself
controls what data can be accessed.

### How to Think About It

```
We need:
  risk_rating, customer_segment   → retail.customer
  balance data                    → retail.account (ACTIVE only)
  Murabaha exposure               → finance.murabaha_contract (ACTIVE only)

The JOIN path:
  customer → customer_account → account
  customer → murabaha_contract (LEFT JOIN — not all customers have one)

LEFT JOIN on murabaha_contract:
  Customers without a Murabaha contract still appear in the view.
  They show NULL for Murabaha columns, which SUM() converts to 0.
  Without LEFT JOIN, customers with no contracts disappear entirely.

GROUP BY risk_rating, customer_segment:
  One row per combination.
  Example rows: H/PREMIUM, H/STANDARD, M/PREMIUM, L/PREMIUM, L/STANDARD
```

### The View

```sql
-- ============================================================
-- VIEW 1: CUSTOMER RISK SUMMARY
--
-- CREATE OR REPLACE VIEW means:
-- If the view already exists, replace its definition.
-- If it does not exist, create it.
-- The underlying data is not affected either way.
--
-- COUNT(DISTINCT c.customer_id)
-- → DISTINCT prevents counting the same customer twice.
--   Without DISTINCT, a customer with two active accounts
--   would be counted twice.
--
-- AVG(a.balance)
-- → Average balance across all active accounts in the group.
--   This is the metric risk managers use to assess segment health.
--
-- WHERE c.is_deleted = FALSE
-- → Always exclude soft-deleted customers.
--   They still exist in the table but must not appear
--   in any active customer reporting.
-- ============================================================

CREATE OR REPLACE VIEW analytics.v_customer_risk_summary AS
SELECT
    c.risk_rating,
    c.customer_segment,
    COUNT(DISTINCT c.customer_id)   AS customer_count,
    AVG(a.balance)                  AS avg_balance_sar,
    SUM(a.balance)                  AS total_deposits_sar,
    COUNT(DISTINCT mc.contract_id)  AS active_murabaha_contracts,
    SUM(mc.total_sale_price)        AS total_murabaha_exposure_sar
FROM retail.customer c
JOIN retail.customer_account ca
    ON c.customer_id = ca.customer_id
    AND ca.relationship = 'PRIMARY'
JOIN retail.account a
    ON ca.account_id = a.account_id
    AND a.status = 'ACTIVE'
LEFT JOIN finance.murabaha_contract mc
    ON c.customer_id = mc.customer_id
    AND mc.status = 'ACTIVE'
WHERE c.is_deleted = FALSE
GROUP BY c.risk_rating, c.customer_segment
ORDER BY c.risk_rating, total_deposits_sar DESC;
```

```sql
-- Test the view
SELECT * FROM analytics.v_customer_risk_summary;
```

### Expected Output

```
 risk_rating | customer_segment | customer_count | avg_balance_sar | total_deposits_sar | active_murabaha_contracts | total_murabaha_exposure_sar
-------------+------------------+----------------+-----------------+--------------------+---------------------------+-----------------------------
 H           | PREMIUM          |              1 |        8750.00  |           8750.00  |                         1 |                    90000.00
 L           | PREMIUM          |              1 |       54550.00  |          54550.00  |                      NULL |                        NULL
 L           | STANDARD         |              1 |       45000.00  |          45000.00  |                      NULL |                        NULL
 M           | STANDARD         |              1 |       22000.00  |          22000.00  |                      NULL |                        NULL
```

**Reading the output:**
- Row 1: Khalid (H/PREMIUM) — high risk, SAR 8,750 balance,
  1 active Murabaha contract worth SAR 90,000
- Row 2: Ahmed (L/PREMIUM) — low risk, SAR 54,550 balance,
  no Murabaha contracts (NULL shows as NULL — no contract)
- Row 3: Noura (L/STANDARD) — SAR 45,000 balance
- Row 4: Fatima (M/STANDARD) — SAR 22,000 balance

**Notice:** No customer names appear anywhere. The compliance
team can see the portfolio risk profile without seeing
any personally identifiable information.

---

## View 2 — Murabaha Overdue Instalments

### Who Uses It
The Collections team to manage overdue accounts. The SAMA regulatory
reporting team to calculate the NPF (Non-Performing Finance) ratio.

### The SAMA NPF Definition

SAMA defines Non-Performing Finance as any financing instalment
that has been overdue for more than 90 days.

When a bank's NPF ratio exceeds a SAMA threshold, the bank must
take corrective action and report to SAMA. The is_npf flag in this
view encodes that regulatory definition directly into the SQL —
not in a spreadsheet, not in a report template, but in the database
where it is consistent for every person who queries it.

### How to Think About It

```
We need:
  instalment details       → finance.murabaha_schedule
  contract details         → finance.murabaha_contract
  customer name            → retail.customer

We want rows where the instalment is overdue:
  Case 1: status = 'OVERDUE' (already flagged by the system)
  Case 2: status = 'PENDING' AND due_date < CURRENT_DATE
          (pending but past the due date — should have been caught)

For each overdue instalment we calculate:
  days_overdue = CURRENT_DATE - due_date
  is_npf = TRUE if days_overdue > 90 (SAMA definition)
```

### The View

```sql
-- ============================================================
-- VIEW 2: MURABAHA OVERDUE INSTALMENTS
--
-- CURRENT_DATE - ms.due_date
-- → Subtracting two DATE values gives an INTEGER (number of days).
--   Positive number = the instalment is this many days late.
--   If due_date is in the future, this would be negative —
--   but our WHERE clause only shows past-due rows.
--
-- THE CASE EXPRESSION for is_npf:
-- SAMA defines NPF as > 90 days overdue.
-- This encodes the regulatory definition directly in SQL.
-- When SAMA asks for the NPF ratio:
--   Numerator   = SUM of is_npf = TRUE from this view
--   Denominator = SUM of total portfolio from View 1
-- Both views must use the same definition — which is guaranteed
-- because the definition lives in one place: this view.
--
-- THE WHERE CLAUSE catches two cases:
-- 1. status = 'OVERDUE'
--    Already flagged as overdue by an automated nightly job.
-- 2. status = 'PENDING' AND ms.due_date < CURRENT_DATE
--    Past due date but not yet updated to OVERDUE status.
--    This catches cases where the nightly job has not yet run.
-- ============================================================

CREATE OR REPLACE VIEW analytics.v_murabaha_overdue AS
SELECT
    ms.schedule_id,
    ms.contract_id,
    mc.customer_id,
    c.full_name_en,
    c.risk_rating,
    ms.instalment_no,
    ms.due_date,
    CURRENT_DATE - ms.due_date     AS days_overdue,
    ms.instalment_sar,
    ms.principal_portion,
    ms.profit_portion,
    CASE
        WHEN CURRENT_DATE - ms.due_date > 90 THEN TRUE
        ELSE FALSE
    END                            AS is_npf
FROM finance.murabaha_schedule ms
JOIN finance.murabaha_contract mc
    ON ms.contract_id = mc.contract_id
JOIN retail.customer c
    ON mc.customer_id = c.customer_id
WHERE ms.status = 'OVERDUE'
   OR (ms.status = 'PENDING' AND ms.due_date < CURRENT_DATE)
ORDER BY days_overdue DESC;
```

```sql
-- Test the view
SELECT * FROM analytics.v_murabaha_overdue;
```

### Expected Output

This view returns rows only when there are overdue instalments.

**If no rows appear:** Instalment 3 has a due_date of 2025-04-01.
If today is before that date, it is not yet overdue — which is
correct behaviour. The view is working as designed.

**To test the view with a past-due instalment:**

```sql
-- Temporarily change instalment 3's due date to be in the past
UPDATE finance.murabaha_schedule
SET due_date = '2024-12-01'
WHERE schedule_id = 3
  AND contract_id = 'MRB0000000000001';

-- Re-run the view
SELECT * FROM analytics.v_murabaha_overdue;
```

**Expected output after the update:**

```
 schedule_id | contract_id      | customer_id | full_name_en  | risk_rating | instalment_no | due_date   | days_overdue | instalment_sar | is_npf
-------------+------------------+-------------+---------------+-------------+---------------+------------+--------------+----------------+--------
           3 | MRB0000000000001 | C000000001  | Ahmed Al-Omari|      L      |             3 | 2024-12-01 |    130 (est) |       3750.00  | true
```

`is_npf = true` because more than 90 days have passed since
December 1 2024. This instalment would appear in the SAMA NPF
calculation immediately.

---

## View 3 — Daily Transaction Volume

### Who Uses It
The Operations team for daily SLA monitoring — checking whether
transaction processing volumes are within normal ranges. The SAMA
regulatory reporting team for periodic transaction volume reports.

### The Standard View vs Materialised View Decision

This view re-runs its aggregation every time it is queried.
With our 6 sample transactions, this is instant.

At production scale — 500,000 transactions per day over 30 days
= 15 million rows — this aggregation takes several seconds every
time the Operations dashboard refreshes.

At that point, this view becomes a **materialised view** candidate:
the result is computed once nightly and stored on disk. Dashboard
reads are instant. The bonus section at the end of this lab shows
exactly how to make that conversion.

### How to Think About It

```
We need:
  All columns from retail.transaction
  Grouped by: txn_date, txn_type, channel

We want:
  COUNT → how many transactions in each group
  SUM   → total SAR value
  AVG   → average transaction size
  MIN   → smallest transaction
  MAX   → largest transaction

We filter:
  Last 30 days only (operational window)
  POSTED status only (confirmed transactions)

No JOIN needed:
  All the information we need is already in the transaction table.
  This is the simplest view to write — but one of the most used.
```

### The View

```sql
-- ============================================================
-- VIEW 3: DAILY TRANSACTION VOLUME
--
-- GROUP BY txn_date, txn_type, channel
-- → One row per combination per day.
-- → Example: "MOBILE MRB_PMT on 2025-02-01" is one row.
--            "ATM DEBIT on 2025-01-10" is another row.
--
-- This granularity lets Operations ask questions like:
--   "How many mobile Murabaha payments happened yesterday?"
--   "What was the total ATM withdrawal volume this week?"
--   "Is SARIE_IN volume higher or lower than last Monday?"
--
-- COUNT(t.txn_id) → number of individual transactions
-- SUM(t.amount_sar) → total value of all transactions in the group
-- AVG, MIN, MAX → distribution metrics for anomaly detection
-- ============================================================

CREATE OR REPLACE VIEW analytics.v_daily_txn_volume AS
SELECT
    t.txn_date,
    t.txn_type,
    t.channel,
    COUNT(t.txn_id)    AS transaction_count,
    SUM(t.amount_sar)  AS total_volume_sar,
    AVG(t.amount_sar)  AS avg_amount_sar,
    MIN(t.amount_sar)  AS min_amount_sar,
    MAX(t.amount_sar)  AS max_amount_sar
FROM retail.transaction t
WHERE t.txn_date >= CURRENT_DATE - INTERVAL '30 days'
  AND t.status = 'POSTED'
GROUP BY t.txn_date, t.txn_type, t.channel
ORDER BY t.txn_date DESC, total_volume_sar DESC;
```

```sql
-- Test the view
SELECT * FROM analytics.v_daily_txn_volume;
```

### Expected Output

One row per transaction type and channel combination within
the last 30 days. Each row shows the count and total volume
for that group on that date.

**If no rows appear:** Our sample transactions have 2025 dates.
If they fall outside the 30-day window, temporarily expand the filter
to see results:

```sql
-- See all transactions regardless of date
SELECT txn_date, txn_type, channel,
       COUNT(*) AS txn_count, SUM(amount_sar) AS total_sar
FROM retail.transaction
WHERE status = 'POSTED'
GROUP BY txn_date, txn_type, channel
ORDER BY txn_date DESC;
```

---

## Step: Verify All Three Views

```sql
-- ============================================================
-- FINAL CHECK
-- Confirm all three views exist and return data.
-- ============================================================

-- Check all three views exist
SELECT table_name AS view_name
FROM information_schema.views
WHERE table_schema = 'analytics'
ORDER BY table_name;

-- Expected:
-- v_customer_risk_summary
-- v_daily_txn_volume
-- v_murabaha_overdue
```

```sql
-- Check row counts for each view
SELECT 'v_customer_risk_summary' AS view_name,
        COUNT(*)                 AS row_count
FROM analytics.v_customer_risk_summary
UNION ALL
SELECT 'v_murabaha_overdue',
        COUNT(*)
FROM analytics.v_murabaha_overdue
UNION ALL
SELECT 'v_daily_txn_volume',
        COUNT(*)
FROM analytics.v_daily_txn_volume;
```

---

## Bonus — Convert View 3 to a Materialised View

This bonus section shows you how to convert v_daily_txn_volume
into a materialised view — the step you would take in production
when the standard view becomes too slow for the dashboard.

```sql
-- ============================================================
-- WHY CONVERT TO A MATERIALISED VIEW?
--
-- Standard view:
--   → Re-runs the aggregation every time it is queried
--   → Always shows current data
--   → Slow when aggregating millions of rows
--
-- Materialised view:
--   → Stores the aggregated result on disk
--   → Reads the pre-computed result — very fast
--   → Data is as fresh as the last REFRESH
--   → Refreshed nightly via an automated process (Airflow DAG)
--
-- For an Operations dashboard showing yesterday's data,
-- nightly freshness is perfectly acceptable.
-- ============================================================

-- Step 1: Remove the standard view
DROP VIEW IF EXISTS analytics.v_daily_txn_volume;


-- Step 2: Create as a materialised view
-- WITH DATA means: run the query now and store the result
CREATE MATERIALIZED VIEW analytics.mv_daily_txn_volume AS
SELECT
    t.txn_date,
    t.txn_type,
    t.channel,
    COUNT(t.txn_id)    AS transaction_count,
    SUM(t.amount_sar)  AS total_volume_sar,
    AVG(t.amount_sar)  AS avg_amount_sar,
    MIN(t.amount_sar)  AS min_amount_sar,
    MAX(t.amount_sar)  AS max_amount_sar
FROM retail.transaction t
WHERE t.txn_date >= CURRENT_DATE - INTERVAL '30 days'
  AND t.status = 'POSTED'
GROUP BY t.txn_date, t.txn_type, t.channel
ORDER BY t.txn_date DESC, total_volume_sar DESC
WITH DATA;
```

```sql
-- Step 3: Create a unique index
-- This is REQUIRED before you can use CONCURRENTLY refresh.
-- The unique index identifies each row in the materialised view
-- so PostgreSQL can update it without replacing everything at once.
CREATE UNIQUE INDEX idx_mv_daily_vol
    ON analytics.mv_daily_txn_volume (txn_date, txn_type, channel);
```

```sql
-- Step 4: Query it — reads pre-computed result, always fast
SELECT * FROM analytics.mv_daily_txn_volume;
```

```sql
-- Step 5: Refresh it when you want updated data
--
-- CONCURRENTLY = refresh without locking the view
-- Users can still read old data while the new data loads in.
-- Without CONCURRENTLY, an exclusive lock blocks all reads
-- during the refresh — causing visible downtime on dashboards.
-- Always use CONCURRENTLY in a live production environment.
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_daily_txn_volume;
```

### Standard View vs Materialised View — When to Use Each

```
┌─────────────────────────────┬────────────────────────────────────┐
│ Use STANDARD VIEW when:     │ Use MATERIALISED VIEW when:        │
├─────────────────────────────┼────────────────────────────────────┤
│ Data must be live           │ Yesterday's data is good enough    │
│ Live KYC status             │ Monthly branch performance report  │
│ Real-time AML alerts        │ SAMA capital adequacy dashboard    │
│ Customer service queries    │ Heavy aggregations (15M+ rows)     │
│ Small tables (fast anyway)  │ Reports needing sub-second load    │
└─────────────────────────────┴────────────────────────────────────┘
```

---

## Complete Lab 3C Summary

```
✅ View 1 created: analytics.v_customer_risk_summary
   → No PII — aggregated by risk_rating and customer_segment
   → Used by Risk Management for portfolio monitoring
   → Grants data access without exposing personal data

✅ View 2 created: analytics.v_murabaha_overdue
   → SAMA NPF definition encoded as is_npf BOOLEAN
   → Catches both OVERDUE and PENDING-past-due instalments
   → Used by Collections and SAMA NPF reporting

✅ View 3 created: analytics.v_daily_txn_volume
   → Aggregated by date, type, and channel
   → Used by Operations for SLA monitoring
   → Identified as materialised view candidate at scale

✅ Bonus: mv_daily_txn_volume (materialised version)
   → Pre-computed result stored on disk
   → CONCURRENTLY refresh — no dashboard downtime
   → Production-ready pattern for SAMA reporting dashboards
```

---

> **Lab 3C is complete.**
>
> You have built three reporting views that real banking teams
> depend on every day — a risk summary without PII, an overdue
> financing report with the SAMA NPF definition built in, and
> a daily volume dashboard with a clear path to materialisation
> when the data grows.
>
> The design decisions in these views — no customer names
> in aggregated reports, regulatory definitions in SQL not
> spreadsheets, CONCURRENTLY refresh for live dashboards —
> are the decisions that distinguish a professional data
> architecture from an ad hoc collection of queries.
>
> You have now completed all three Day 3 labs.
> Keep the al_noor_bank database running — Day 4 and Day 5
> build directly on everything you have created today.
>
> Excellent work.

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*