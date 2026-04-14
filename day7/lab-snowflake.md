# Day 7 — Snowflake Labs
## Lab 7A · 7B · 7C · 7D — Step-by-Step Guide for First-Time Snowflake Users

> **Before you begin.** These labs run on a Snowflake 30-day free trial account. You will need a valid email address to sign up. No credit card is required. All four labs build on each other — do them in order.
>
> **Time allocation:** Lab 7A: 45 min · Lab 7B: 30 min · Lab 7C: 30 min · Lab 7D: 60 min
>
> **Al-Noor context.** You are building the Enterprise Data Warehouse for Al-Noor Retail Bank. By the end of Lab 7D you will have a fully operational Snowflake EDW with RBAC, dimension tables, a loaded fact table, and Time Travel queries running against it.

---

## Pre-Lab: Setting Up Your Snowflake Free Trial

### Step 1 — Create Your Account

1. Open your browser and go to **https://signup.snowflake.com**
2. Fill in your name and email address. Use a real email — you will need to verify it.
3. On the next screen, choose:
   - **Snowflake Edition:** `Standard` (free tier covers this)
   - **Cloud Provider:** `Amazon Web Services`
   - **Region:** Select `Middle East (UAE) — me-central-1` if available. If not, choose `Europe (Frankfurt)` as the nearest alternative.
4. Click **Continue**. Check your email and click the verification link.
5. Set your username and password. Write these down — you will need them throughout the programme.
6. You will land on the **Snowflake Home** page. This is the new Snowsight UI.

> **What you are looking at:** Snowsight is Snowflake's browser-based interface. Everything in these labs runs here — you do not need to install anything locally.

---

### Step 2 — Understand the New Snowsight Interface

When you log in you will see the **Home** page. The layout has a narrow icon bar on the far left, and a main content area showing Quick Actions and Projects.

```
Far-left icon bar (top to bottom):
├── 🏠  Home             ← You are here now
├── +   Create           ← Opens the Create menu (SQL files, notebooks, etc.)
├── 🔍  Search           ← Global search
│
│   (further down)
├── 📊  Data             ← Browse databases, tables, schemas
├── 🛒  Marketplace      ← Snowflake data marketplace (not used today)
├── ⚡  Activity         ← Query history, task runs
└── ⚙️  Admin            ← Users, roles, warehouses, billing

Bottom-left:
└── Your name + ACCOUNTADMIN role indicator
    "$400 credits left — Trial ends in 29 days"
```

There is no longer a "Worksheets" item in the sidebar. SQL editing is now done through **SQL Files**, accessed via the **Create (`+`) menu**.

---

### Step 3 — Create Your First SQL File (the New "Worksheet")

In the new UI, what was previously called a Worksheet is now a **SQL File**. Here is how to create one:

1. Click the **`+` (Create) button** in the top-left icon bar — the one just below the Snowflake logo.
2. A dropdown menu appears with these options:
   ```
   SQL File              ← THIS IS WHAT YOU WANT
   Python Worksheet
   Notebook
   Streamlit App
   Git Repository
   Postgres Instance
   Container Service
   Dashboard
   Table
   Stage
   View
   Add Data
   Admin
   ```
3. Click **SQL File**.
4. A SQL editor opens in a new tab. At the top you will see a title like `SQL File 1` — click it and rename it to `Day 7 — Al-Noor DWH Setup`.
5. You now have a blank SQL editor. This is where you write and run all lab SQL.

> **Where are my old files?** If you created anything previously, your SQL files appear under **Projects → Files** on the Home page, or you can find them via the Search icon.

---

### Step 4 — The SQL Editor — Key Controls

Once your SQL File is open, you will see:

```
Top bar of the SQL editor:
┌─────────────────────────────────────────────────────────────────┐
│ [SQL File name]      [Database dropdown] [Schema dropdown]      │
│                                              [▶ Run] [▼ Run All]│
└─────────────────────────────────────────────────────────────────┘

Right panel (appears after a query runs):
├── Results tab    ← Query output rows
├── Query Details  ← Execution time, rows returned
└── Query Profile  ← Visual execution plan (used in Lab 7D)
```

**Running SQL:**
- To run a **single statement**: place your cursor anywhere inside it → press `Ctrl+Enter` (Windows) or `Cmd+Enter` (Mac).
- To run a **selected block**: highlight the SQL you want → press `Ctrl+Enter`.
- To run the **entire file**: click the **▶ Run** button at the top right of the editor.

> **Critical habit:** Run one statement at a time during setup. Never run the entire file at once — if one statement fails you need to see exactly which one and why.

**Setting database and schema from the UI (optional shortcut):**
In the editor toolbar you will see two dropdowns — one for database and one for schema. You can set these from the dropdowns instead of typing `USE DATABASE` and `USE SCHEMA` in SQL. Either method works; the SQL method is used in this lab so the steps are explicit and repeatable.

---

### Step 5 — Verify Your Starting State

In your new SQL File, type this and press `Ctrl+Enter`:

```sql
SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA();
```

The result panel appears at the bottom or right of the editor. You will likely see:
- `CURRENT_ROLE()` → `ACCOUNTADMIN` ✓
- `CURRENT_WAREHOUSE()` → blank (no warehouse yet — expected)
- `CURRENT_DATABASE()` → blank (expected)
- `CURRENT_SCHEMA()` → blank (expected)

This is the correct starting state. The labs build everything from here.

---

### Step 6 — Navigating to Your Databases and Tables (the Data Explorer)

After you create tables in the labs, you can browse them visually:

1. Click the **cylinder / database icon** in the far-left icon bar (it may also appear as a grid or the word **Data**).
2. You will see a panel listing databases. After Lab 7A, `al_noor_dwh` will appear here.
3. Expand it: `al_noor_dwh` → `analytics` → `Tables` to see your dimension and fact tables.
4. Click any table name to preview its columns and sample data.

---

### Step 7 — Understanding Free Tier Credits

Your bottom-left shows **$400 credits left** and **Trial ends in 29 days**. These labs use minimal credits. Key rules:

- **Always set `AUTO_SUSPEND = 60`** on any warehouse you create. An idle warehouse that is not suspended still burns credits.
- **Suspend manually when taking a break:** `ALTER WAREHOUSE al_noor_etl_wh SUSPEND;`
- **An XSMALL warehouse costs 1 credit per hour.** Completing all four labs in one session uses approximately 2–3 credits total.
- You can monitor credit consumption: left icon bar → **Admin** → **Cost Management**.

---

## Lab 7A — Build the DWH Schema

**Objective:** Create the `al_noor_dwh` database, schemas, warehouse, and all dimension tables. Populate `DIM_DATE` for 2025 and load master data for branches, products, channels, and customers.

**Duration:** 45 minutes

---

### Section 7A.1 — Create the Database and Schemas

Click the **`+` (Create) button** → **SQL File** → rename it to `Lab 7A — Schema Setup`.

If you are continuing from the Pre-Lab and still have your SQL file open, you can keep using the same file — just scroll to the bottom and continue.

Run each block below **one at a time**. Read the comment above each block before running it.

```sql
-- Switch to SYSADMIN — this role creates databases and warehouses
-- ACCOUNTADMIN can also do this, but it is good practice to use the minimum role needed
USE ROLE SYSADMIN;
```

```sql
-- Create the main DWH database
-- DATA_RETENTION_TIME_IN_DAYS = 1 because free tier only supports up to 1 day
-- In production this would be 90 days for SAMA audit compliance
CREATE DATABASE IF NOT EXISTS al_noor_dwh
    DATA_RETENTION_TIME_IN_DAYS = 1
    COMMENT = 'Al-Noor Bank Enterprise Data Warehouse';
```

```sql
-- Verify the database was created
SHOW DATABASES LIKE 'al_noor_dwh';
```

You should see one row with `al_noor_dwh` in the results. If you see zero rows, the `CREATE DATABASE` failed — check the error message in the Results panel.

```sql
-- Create three schemas inside the database
CREATE SCHEMA IF NOT EXISTS al_noor_dwh.staging
    COMMENT = 'Raw landing zone — data arrives here before transformation';

CREATE SCHEMA IF NOT EXISTS al_noor_dwh.analytics
    COMMENT = 'Fact and dimension tables — the EDW proper';

CREATE SCHEMA IF NOT EXISTS al_noor_dwh.compliance
    COMMENT = 'KYC audit trails, PDPL data inventory';
```

```sql
-- Verify all three schemas exist
SHOW SCHEMAS IN DATABASE al_noor_dwh;
```

You should see three schemas: `staging`, `analytics`, `compliance` plus the default `PUBLIC` and `INFORMATION_SCHEMA`.

---

### Section 7A.2 — Create the Virtual Warehouse

```sql
-- Create the ETL warehouse
-- XSMALL is the smallest and cheapest size — more than enough for our labs
-- AUTO_SUSPEND = 60 means it will suspend after 60 seconds of no queries
CREATE WAREHOUSE IF NOT EXISTS al_noor_etl_wh
    WAREHOUSE_SIZE    = 'XSMALL'
    AUTO_SUSPEND      = 60
    AUTO_RESUME       = TRUE
    COMMENT           = 'Lab warehouse — ETL and data loading';
```

```sql
-- Activate this warehouse for your session
USE WAREHOUSE al_noor_etl_wh;
```

```sql
-- Confirm your session context — all four values should now be set
SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA();
```

> **Checkpoint:** If `CURRENT_WAREHOUSE()` still shows blank, the `USE WAREHOUSE` statement did not work. Try running it again. If the warehouse does not exist, the `CREATE WAREHOUSE` failed — check the error.

---

### Section 7A.3 — Set Your Working Context

Rather than typing the full schema path (`al_noor_dwh.analytics.table_name`) in every statement, set the default database and schema for this session:

```sql
USE DATABASE al_noor_dwh;
USE SCHEMA analytics;
```

From this point, any `CREATE TABLE` statement without a schema prefix will create the table in `al_noor_dwh.analytics`. Confirm:

```sql
SELECT CURRENT_DATABASE(), CURRENT_SCHEMA();
-- Expected: al_noor_dwh | analytics
```

---

### Section 7A.4 — Create DIM_DATE

```sql
-- DIM_DATE stores one row per calendar day
-- date_id is an integer in YYYYMMDD format — e.g., 20250115 for 15 Jan 2025
-- This format joins faster than a DATE column and makes range filters intuitive

CREATE TABLE IF NOT EXISTS dim_date (
    date_id             INTEGER       NOT NULL,      -- YYYYMMDD
    full_date           DATE          NOT NULL,
    day_name_en         VARCHAR(10)   NOT NULL,      -- Monday, Tuesday, etc.
    month_number        SMALLINT      NOT NULL,
    month_name_en       VARCHAR(15)   NOT NULL,
    quarter             SMALLINT      NOT NULL,
    year                SMALLINT      NOT NULL,
    is_weekend          BOOLEAN       NOT NULL,      -- TRUE for Friday and Saturday
    is_public_holiday   BOOLEAN       NOT NULL  DEFAULT FALSE,
    holiday_name_ar     VARCHAR(100),
    hijri_month         SMALLINT,
    hijri_year          SMALLINT,
    hijri_month_name_ar VARCHAR(30),
    is_ramadan          BOOLEAN       NOT NULL  DEFAULT FALSE,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_id)
);
```

```sql
-- Verify the table was created with the right structure
DESCRIBE TABLE dim_date;
```

You should see all 13 columns listed. Now populate it:

```sql
-- Populate DIM_DATE for the full year 2025
-- Snowflake does not have GENERATE_SERIES like PostgreSQL
-- Instead we use TABLE(GENERATOR(ROWCOUNT => 365)) to produce 365 rows
-- and DATEADD to calculate each calendar date from the start date

INSERT INTO dim_date (
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
    DAYOFWEEK(d::DATE) IN (6, 7)               AS is_weekend
    -- IMPORTANT: In Snowflake, DAYOFWEEK returns 0=Sunday, 1=Mon, ..., 5=Fri, 6=Sat
    -- Friday = 6, Saturday = 7
    -- This is DIFFERENT from PostgreSQL where Friday=5, Saturday=6
FROM (
    SELECT
        DATEADD('day',
                ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1,
                '2025-01-01') AS d
    FROM TABLE(GENERATOR(ROWCOUNT => 365))
);
```

```sql
-- Verify: should return exactly 365 rows
SELECT COUNT(*) AS total_days FROM dim_date;
```

```sql
-- Verify Saudi weekend logic — should return Fridays and Saturdays only
SELECT date_id, full_date, day_name_en, is_weekend
FROM dim_date
WHERE is_weekend = TRUE
ORDER BY date_id
LIMIT 10;
```

You should see alternating Fridays and Saturdays. If you see any other days, the `DAYOFWEEK IN (6,7)` logic is wrong — re-check the insert.

```sql
-- Verify a specific known date — 1 Jan 2025 was a Wednesday
SELECT date_id, full_date, day_name_en, is_weekend, quarter
FROM dim_date
WHERE date_id = 20250101;
-- Expected: day_name_en = 'Wed', is_weekend = FALSE, quarter = 1
```

---

### Section 7A.5 — Create DIM_BRANCH

```sql
CREATE TABLE IF NOT EXISTS dim_branch (
    dim_branch_sk   NUMBER AUTOINCREMENT PRIMARY KEY,
    branch_id       VARCHAR(10)  NOT NULL UNIQUE,
    branch_name_en  VARCHAR(100) NOT NULL,
    branch_name_ar  VARCHAR(100),
    city            VARCHAR(50)  NOT NULL,
    region          VARCHAR(50)  NOT NULL,
    branch_type     VARCHAR(20)  NOT NULL,  -- MAIN, REGIONAL, DIGITAL_ONLY
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);
```

```sql
-- Load Al-Noor branch master data
INSERT INTO dim_branch (branch_id, branch_name_en, branch_name_ar, city, region, branch_type)
VALUES
    ('RUH-01', 'Riyadh Main Branch',      'فرع الرياض الرئيسي',   'Riyadh',  'Central',  'MAIN'),
    ('RUH-02', 'Al Olaya Branch',          'فرع العليا',           'Riyadh',  'Central',  'REGIONAL'),
    ('RUH-03', 'Al Malaz Branch',          'فرع الملز',            'Riyadh',  'Central',  'REGIONAL'),
    ('JED-01', 'Jeddah Main Branch',       'فرع جدة الرئيسي',      'Jeddah',  'Western',  'MAIN'),
    ('JED-02', 'Al Hamra Branch',          'فرع الحمراء',          'Jeddah',  'Western',  'REGIONAL'),
    ('DMM-01', 'Dammam Main Branch',       'فرع الدمام الرئيسي',   'Dammam',  'Eastern',  'MAIN'),
    ('MED-01', 'Madinah Branch',           'فرع المدينة المنورة',  'Madinah', 'Western',  'REGIONAL'),
    ('DIG-01', 'Digital Banking Centre',   'مركز الخدمات الرقمية', 'Riyadh',  'Central',  'DIGITAL_ONLY');
```

```sql
-- Verify
SELECT * FROM dim_branch ORDER BY branch_id;
-- Expected: 8 rows
```

---

### Section 7A.6 — Create DIM_PRODUCT

```sql
CREATE TABLE IF NOT EXISTS dim_product (
    dim_product_sk      NUMBER AUTOINCREMENT PRIMARY KEY,
    product_id          VARCHAR(15)  NOT NULL UNIQUE,
    product_name_en     VARCHAR(200) NOT NULL,
    product_name_ar     VARCHAR(200),
    product_code        VARCHAR(20)  NOT NULL,
    category_name       VARCHAR(100) NOT NULL,
    is_sharia_compliant BOOLEAN      NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN      NOT NULL DEFAULT TRUE
);
```

```sql
-- Islamic and conventional products
INSERT INTO dim_product (product_id, product_name_en, product_name_ar, product_code, category_name, is_sharia_compliant)
VALUES
    ('PROD-001', 'Murabaha Home Finance',       'تمويل المرابحة العقاري',        'MRB-HOME',  'Islamic Finance',      TRUE),
    ('PROD-002', 'Tawarruq Personal Finance',   'التورق الشخصي',                 'TWR-PERS',  'Islamic Finance',      TRUE),
    ('PROD-003', 'Ijara Vehicle Finance',        'إجارة السيارات',               'IJR-VEH',   'Islamic Finance',      TRUE),
    ('PROD-004', 'Sukuk Investment',             'الصكوك الاستثمارية',           'SUK-INV',   'Islamic Finance',      TRUE),
    ('PROD-005', 'Current Account',             'الحساب الجاري',                 'ACC-CUR',   'Retail Banking',       FALSE),
    ('PROD-006', 'Savings Account',             'حساب التوفير',                  'ACC-SAV',   'Retail Banking',       FALSE),
    ('PROD-007', 'SARIE Wire Transfer',         'تحويل سريع - شبكة سريع',       'PAY-SARIE', 'Payments',             FALSE),
    ('PROD-008', 'SADAD Bill Payment',          'دفع الفواتير - سداد',           'PAY-SADAD', 'Payments',             FALSE),
    ('PROD-009', 'AANI Instant Payment',        'الدفع الفوري - آني',            'PAY-AANI',  'Payments',             FALSE),
    ('PROD-010', 'Corporate Current Account',   'الحساب الجاري للشركات',         'ACC-CORP',  'Corporate Banking',    FALSE);
```

```sql
-- Verify — check the Islamic vs conventional split
SELECT is_sharia_compliant, COUNT(*) AS product_count
FROM dim_product
GROUP BY is_sharia_compliant
ORDER BY is_sharia_compliant DESC;
-- Expected: TRUE=4, FALSE=6
```

---

### Section 7A.7 — Create DIM_CHANNEL

```sql
CREATE TABLE IF NOT EXISTS dim_channel (
    dim_channel_sk   NUMBER AUTOINCREMENT PRIMARY KEY,
    channel_id       VARCHAR(10)  NOT NULL UNIQUE,
    channel_name_en  VARCHAR(100) NOT NULL,
    channel_type     VARCHAR(30)  NOT NULL,   -- DIGITAL, PHYSICAL, CALL_CENTRE
    is_self_service  BOOLEAN      NOT NULL DEFAULT FALSE
);
```

```sql
INSERT INTO dim_channel (channel_id, channel_name_en, channel_type, is_self_service)
VALUES
    ('CHN-001', 'Mobile Banking App',    'DIGITAL',      TRUE),
    ('CHN-002', 'Internet Banking',      'DIGITAL',      TRUE),
    ('CHN-003', 'ATM',                   'DIGITAL',      TRUE),
    ('CHN-004', 'Branch Teller',         'PHYSICAL',     FALSE),
    ('CHN-005', 'Call Centre',           'CALL_CENTRE',  FALSE),
    ('CHN-006', 'API (Open Banking)',    'DIGITAL',      TRUE);
```

---

### Section 7A.8 — Create DIM_CUSTOMER (SCD Type 2)

This is the most important dimension table. It has three additional columns that enable SCD Type 2 history tracking: `effective_from`, `effective_to`, and `is_current`.

```sql
CREATE TABLE IF NOT EXISTS dim_customer (
    dim_customer_sk   NUMBER AUTOINCREMENT PRIMARY KEY,
    customer_id       VARCHAR(10)  NOT NULL,   -- Natural key from CBS
    full_name_en      VARCHAR(200),
    customer_segment  VARCHAR(30),             -- RETAIL, PREMIUM, PRIVATE, CORPORATE
    risk_rating       CHAR(1),                 -- A, B, C, D (SAMA capital adequacy)
    kyc_status        VARCHAR(20),             -- VERIFIED, PENDING, EXPIRED
    nationality       CHAR(3),                 -- ISO 3166-1 alpha-3 (SAU, EGY, IND, etc.)
    branch_id         VARCHAR(10),
    branch_name       VARCHAR(100),
    region            VARCHAR(50),

    -- SCD Type 2 tracking columns
    effective_from    DATE         NOT NULL,
    effective_to      DATE,                    -- NULL means this is the current active record
    is_current        BOOLEAN      NOT NULL DEFAULT TRUE,

    -- Clustering: most common query pattern is "find current record for customer X"
    CONSTRAINT pk_dim_customer PRIMARY KEY (dim_customer_sk)
) CLUSTER BY (customer_id, is_current);
```

```sql
-- Load initial customer data
-- All records start as current (is_current = TRUE, effective_to = NULL)
INSERT INTO dim_customer (
    customer_id, full_name_en, customer_segment, risk_rating,
    kyc_status, nationality, branch_id, branch_name, region,
    effective_from, effective_to, is_current
)
VALUES
    ('C000000001', 'Ahmed Mohammed Al-Omari',   'RETAIL',    'B', 'VERIFIED', 'SAU', 'RUH-01', 'Riyadh Main Branch', 'Central', '2023-01-15', NULL, TRUE),
    ('C000000002', 'Fatima Khalid Al-Rashidi',  'PREMIUM',   'A', 'VERIFIED', 'SAU', 'JED-01', 'Jeddah Main Branch', 'Western', '2022-06-01', NULL, TRUE),
    ('C000000003', 'Mohammed Ali Hassan',        'RETAIL',    'C', 'VERIFIED', 'EGY', 'RUH-02', 'Al Olaya Branch',    'Central', '2023-09-20', NULL, TRUE),
    ('C000000004', 'Nora Abdullah Al-Saud',      'PRIVATE',   'A', 'VERIFIED', 'SAU', 'JED-02', 'Al Hamra Branch',    'Western', '2021-03-10', NULL, TRUE),
    ('C000000005', 'Khalid Ibrahim Al-Zahrani',  'CORPORATE', 'B', 'VERIFIED', 'SAU', 'DMM-01', 'Dammam Main Branch', 'Eastern', '2020-11-05', NULL, TRUE);
```

```sql
-- Verify customer dimension
SELECT customer_id, full_name_en, customer_segment, risk_rating, is_current
FROM dim_customer
ORDER BY customer_id;
-- Expected: 5 rows, all is_current = TRUE
```

---

### Section 7A.9 — Create FACT_TRANSACTION

```sql
CREATE TABLE IF NOT EXISTS fact_transaction (
    fact_txn_sk       NUMBER AUTOINCREMENT PRIMARY KEY,
    date_id           INTEGER      NOT NULL,
    dim_customer_sk   NUMBER       NOT NULL,
    dim_product_sk    NUMBER       NOT NULL,
    dim_branch_sk     NUMBER       NOT NULL,
    dim_channel_sk    NUMBER       NOT NULL,
    txn_type          VARCHAR(30)  NOT NULL,
    direction         CHAR(1)      NOT NULL,   -- D=Debit, C=Credit
    status            VARCHAR(15)  NOT NULL,   -- POSTED, REVERSED
    source_txn_id     VARCHAR(50)  UNIQUE,     -- CBS reference for lineage
    amount_sar        NUMBER(18,2) NOT NULL,
    etl_load_ts       TIMESTAMP_TZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    etl_source_system VARCHAR(30)  NOT NULL DEFAULT 'CBS',
    FOREIGN KEY (date_id)         REFERENCES dim_date(date_id),
    FOREIGN KEY (dim_customer_sk) REFERENCES dim_customer(dim_customer_sk),
    FOREIGN KEY (dim_product_sk)  REFERENCES dim_product(dim_product_sk),
    FOREIGN KEY (dim_branch_sk)   REFERENCES dim_branch(dim_branch_sk),
    FOREIGN KEY (dim_channel_sk)  REFERENCES dim_channel(dim_channel_sk)
) CLUSTER BY (date_id, txn_type);
```

```sql
-- Confirm all tables exist in the analytics schema
SHOW TABLES IN SCHEMA al_noor_dwh.analytics;
```

You should see: `dim_date`, `dim_branch`, `dim_product`, `dim_channel`, `dim_customer`, `fact_transaction`.

**Lab 7A complete.** Before moving to Lab 7B, take 2 minutes to browse your tables in the Snowsight Data panel (left sidebar → Data → al_noor_dwh → analytics). Click on any table to see its columns and a preview of its data.

---

## Lab 7B — Load the Fact Table and Run Analytical Queries

**Objective:** Load 20 sample transactions into `FACT_TRANSACTION` using a dimension lookup pattern, then run three SAMA-style analytical queries.

**Duration:** 30 minutes

---

### Section 7B.1 — Confirm Your Session Context

```sql
USE ROLE SYSADMIN;
USE WAREHOUSE al_noor_etl_wh;
USE DATABASE al_noor_dwh;
USE SCHEMA analytics;
```

---

### Section 7B.2 — Load Sample Transactions

This `INSERT` uses subqueries to look up the correct surrogate keys from the dimension tables at load time. This is the ELT pattern — the fact table stores surrogate keys, never natural keys.

Read through the query before running it. Note how each dimension key is resolved:

```sql
-- Load 20 Al-Noor sample transactions into FACT_TRANSACTION
-- Each INSERT...SELECT resolves dimension surrogate keys at load time
INSERT INTO fact_transaction (
    date_id, dim_customer_sk, dim_product_sk,
    dim_branch_sk, dim_channel_sk,
    txn_type, direction, status, source_txn_id, amount_sar
)
SELECT
    dd.date_id,
    dc.dim_customer_sk,
    dp.dim_product_sk,
    db.dim_branch_sk,
    dch.dim_channel_sk,
    s.txn_type,
    s.direction,
    s.status,
    s.source_txn_id,
    s.amount_sar
FROM (
    -- Staging data: raw transaction details as they would arrive from CBS
    SELECT * FROM VALUES
        ('C000000001', 'PROD-001', 'RUH-01', 'CHN-004', 'MURABAHA_PAYMENT',  'D', 'POSTED', 'CBS-2025-0001', 15000.00, '2025-01-10'),
        ('C000000002', 'PROD-007', 'JED-01', 'CHN-001', 'SARIE_TRANSFER',    'D', 'POSTED', 'CBS-2025-0002', 50000.00, '2025-01-12'),
        ('C000000003', 'PROD-005', 'RUH-02', 'CHN-002', 'DEPOSIT',           'C', 'POSTED', 'CBS-2025-0003',  8200.00, '2025-01-14'),
        ('C000000004', 'PROD-004', 'JED-02', 'CHN-001', 'SUKUK_PURCHASE',    'D', 'POSTED', 'CBS-2025-0004',250000.00, '2025-01-15'),
        ('C000000005', 'PROD-010', 'DMM-01', 'CHN-004', 'CORPORATE_PAYMENT', 'D', 'POSTED', 'CBS-2025-0005',180000.00, '2025-01-15'),
        ('C000000001', 'PROD-008', 'RUH-01', 'CHN-001', 'SADAD_PAYMENT',     'D', 'POSTED', 'CBS-2025-0006',   450.00, '2025-01-20'),
        ('C000000002', 'PROD-002', 'JED-01', 'CHN-002', 'TAWARRUQ_DRAWDOWN', 'C', 'POSTED', 'CBS-2025-0007', 30000.00, '2025-01-22'),
        ('C000000003', 'PROD-009', 'RUH-02', 'CHN-001', 'AANI_TRANSFER',     'D', 'POSTED', 'CBS-2025-0008',  1500.00, '2025-01-25'),
        ('C000000004', 'PROD-003', 'JED-02', 'CHN-004', 'IJARA_PAYMENT',     'D', 'POSTED', 'CBS-2025-0009', 12500.00, '2025-02-01'),
        ('C000000001', 'PROD-007', 'RUH-01', 'CHN-002', 'SARIE_TRANSFER',    'D', 'POSTED', 'CBS-2025-0010', 75000.00, '2025-02-05'),
        ('C000000005', 'PROD-010', 'DMM-01', 'CHN-004', 'SALARY_CREDIT',     'C', 'POSTED', 'CBS-2025-0011',500000.00, '2025-02-07'),
        ('C000000002', 'PROD-001', 'JED-01', 'CHN-001', 'MURABAHA_PAYMENT',  'D', 'POSTED', 'CBS-2025-0012', 22000.00, '2025-02-10'),
        ('C000000003', 'PROD-006', 'RUH-02', 'CHN-001', 'PROFIT_CREDIT',     'C', 'POSTED', 'CBS-2025-0013',   320.00, '2025-02-14'),
        ('C000000004', 'PROD-004', 'JED-02', 'CHN-002', 'SUKUK_REDEMPTION',  'C', 'POSTED', 'CBS-2025-0014',260000.00, '2025-02-20'),
        ('C000000001', 'PROD-005', 'RUH-01', 'CHN-003', 'ATM_WITHDRAWAL',    'D', 'POSTED', 'CBS-2025-0015',  2000.00, '2025-02-22'),
        ('C000000002', 'PROD-009', 'JED-01', 'CHN-001', 'AANI_TRANSFER',     'D', 'POSTED', 'CBS-2025-0016',  5000.00, '2025-03-01'),
        ('C000000005', 'PROD-007', 'DMM-01', 'CHN-004', 'SARIE_TRANSFER',    'D', 'POSTED', 'CBS-2025-0017',750000.00, '2025-03-05'),
        ('C000000003', 'PROD-002', 'RUH-02', 'CHN-002', 'TAWARRUQ_PAYMENT',  'D', 'POSTED', 'CBS-2025-0018', 18000.00, '2025-03-10'),
        ('C000000001', 'PROD-008', 'RUH-01', 'CHN-001', 'SADAD_PAYMENT',     'D', 'POSTED', 'CBS-2025-0019',   680.00, '2025-03-12'),
        ('C000000004', 'PROD-003', 'JED-02', 'CHN-004', 'IJARA_PAYMENT',     'D', 'POSTED', 'CBS-2025-0020', 12500.00, '2025-03-15')
    AS v(customer_id, product_id, branch_id, channel_id, txn_type, direction, status, source_txn_id, amount_sar, txn_date)
) s
JOIN dim_date     dd  ON dd.full_date  = s.txn_date::DATE
JOIN dim_customer dc  ON dc.customer_id = s.customer_id AND dc.is_current = TRUE
JOIN dim_product  dp  ON dp.product_id  = s.product_id
JOIN dim_branch   db  ON db.branch_id   = s.branch_id
JOIN dim_channel  dch ON dch.channel_id = s.channel_id;
```

```sql
-- Validate: should return exactly 20 rows
SELECT COUNT(*) AS loaded_rows FROM fact_transaction;
```

If you see fewer than 20 rows, one or more joins failed to match. Run this diagnostic to find which transactions did not load:

```sql
-- Diagnostic: find which source records did not match dimension keys
SELECT s.source_txn_id, s.customer_id, s.product_id, s.branch_id, s.channel_id
FROM (
    SELECT 'CBS-2025-0001' AS source_txn_id, 'C000000001' AS customer_id, 'PROD-001' AS product_id, 'RUH-01' AS branch_id, 'CHN-004' AS channel_id
    UNION ALL SELECT 'CBS-2025-0002', 'C000000002', 'PROD-007', 'JED-01', 'CHN-001'
    -- Add more rows if needed...
) s
WHERE NOT EXISTS (
    SELECT 1 FROM fact_transaction ft WHERE ft.source_txn_id = s.source_txn_id
);
```

---

### Section 7B.3 — Analytical Queries

**Query 1 — Transaction volume by product (Islamic vs conventional)**

```sql
-- SAMA reporting often requires Islamic vs conventional split
-- This shows both total volume and the Sharia-compliant breakdown
SELECT
    dp.product_name_en,
    dp.is_sharia_compliant,
    COUNT(ft.fact_txn_sk)      AS txn_count,
    SUM(ft.amount_sar)         AS total_sar,
    ROUND(AVG(ft.amount_sar), 2) AS avg_transaction_sar
FROM fact_transaction ft
JOIN dim_product dp ON ft.dim_product_sk = dp.dim_product_sk
GROUP BY dp.product_name_en, dp.is_sharia_compliant
ORDER BY total_sar DESC;
```

Note which products generate the highest volume. Which Islamic finance product has the most activity?

**Query 2 — Channel mix with percentage of total**

```sql
-- Channel mix analysis — digital adoption vs physical branch
SELECT
    dch.channel_type,
    dch.channel_name_en,
    COUNT(*)                                            AS txn_count,
    SUM(ft.amount_sar)                                  AS total_sar,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)  AS pct_of_txn_count,
    ROUND(100.0 * SUM(ft.amount_sar) / SUM(SUM(ft.amount_sar)) OVER (), 1) AS pct_of_volume
FROM fact_transaction ft
JOIN dim_channel dch ON ft.dim_channel_sk = dch.dim_channel_sk
GROUP BY dch.channel_type, dch.channel_name_en
ORDER BY total_sar DESC;
```

Is the mobile app or internet banking generating more volume? Does the branch teller channel punch above its weight in SAR value despite lower transaction count?

**Query 3 — Monthly summary by region (SAMA-style)**

```sql
-- Monthly transaction summary by region — the kind of table that feeds a SAMA submission
SELECT
    dd.year,
    dd.month_number,
    dd.month_name_en,
    db.region,
    COUNT(ft.fact_txn_sk)  AS txn_count,
    SUM(ft.amount_sar)     AS total_volume_sar,
    COUNT(DISTINCT ft.dim_customer_sk) AS unique_customers
FROM fact_transaction ft
JOIN dim_date   dd ON ft.date_id         = dd.date_id
JOIN dim_branch db ON ft.dim_branch_sk   = db.dim_branch_sk
GROUP BY dd.year, dd.month_number, dd.month_name_en, db.region
ORDER BY dd.year, dd.month_number, db.region;
```

**Lab 7B complete.** You have a loaded fact table and can run dimensional queries across it. Move on to Lab 7C.

---

## Lab 7C — SCD Type 2 Simulation

**Objective:** Simulate a real business event — customer C000000001 is upgraded from RETAIL to PREMIUM segment — and verify that historical transactions continue to report the correct segment.

**Duration:** 30 minutes

**Why this matters for SAMA:** A capital adequacy report submitted in February 2025 used C000000001's RETAIL risk weight. When re-examined in June 2025, the customer is PREMIUM. The report must still return RETAIL for January and February transactions. This is what SCD Type 2 guarantees.

---

### Section 7C.1 — Verify Current State Before the Change

```sql
-- Show the current state of C000000001 before any changes
SELECT dim_customer_sk, customer_id, full_name_en,
       customer_segment, effective_from, effective_to, is_current
FROM dim_customer
WHERE customer_id = 'C000000001';
```

Note the `dim_customer_sk` value. This is the surrogate key that was stamped onto all January and February fact rows when they were loaded. Write it down — you will check it again after the SCD operation.

```sql
-- Show the fact rows currently linked to C000000001
-- All of them reference the same dim_customer_sk
SELECT ft.source_txn_id, dd.full_date, dc.customer_segment,
       ft.amount_sar, ft.txn_type
FROM fact_transaction ft
JOIN dim_customer dc ON ft.dim_customer_sk = dc.dim_customer_sk
JOIN dim_date     dd ON ft.date_id         = dd.date_id
WHERE dc.customer_id = 'C000000001'
ORDER BY dd.full_date;
-- Expected: all 4 rows show RETAIL segment
```

---

### Section 7C.2 — Apply the SCD Type 2 Change

The segment upgrade takes effect on 16 March 2025. The process is always two steps: expire the old record, insert the new record.

```sql
-- STEP 1: Expire the current RETAIL record
-- Set effective_to to the day BEFORE the change takes effect
-- Set is_current to FALSE — this row is now historical
UPDATE dim_customer
SET    effective_to = '2025-03-15',
       is_current   = FALSE
WHERE  customer_id  = 'C000000001'
AND    is_current   = TRUE;
```

```sql
-- Verify Step 1: the RETAIL row should now have effective_to set and is_current = FALSE
SELECT dim_customer_sk, customer_segment, effective_from, effective_to, is_current
FROM dim_customer
WHERE customer_id = 'C000000001';
-- Expected: 1 row, is_current = FALSE, effective_to = 2025-03-15
```

```sql
-- STEP 2: Insert the new PREMIUM record
-- This gets a NEW surrogate key (AUTOINCREMENT generates it)
-- effective_from = the date the change takes effect
-- effective_to = NULL (no end date — currently active)
-- is_current = TRUE
INSERT INTO dim_customer (
    customer_id, full_name_en, customer_segment, risk_rating,
    kyc_status, nationality, branch_id, branch_name, region,
    effective_from, effective_to, is_current
)
SELECT
    customer_id,
    full_name_en,
    'PREMIUM',          -- new segment
    'A',                -- risk rating also upgraded
    kyc_status,
    nationality,
    branch_id,
    branch_name,
    region,
    '2025-03-16',       -- effective from the change date
    NULL,               -- no end date — this is the current active record
    TRUE
FROM dim_customer
WHERE customer_id  = 'C000000001'
AND   effective_to = '2025-03-15';  -- pull other attributes from the just-expired row
```

```sql
-- Verify Step 2: there should now be TWO rows for C000000001
SELECT dim_customer_sk, customer_segment, effective_from, effective_to, is_current
FROM dim_customer
WHERE customer_id = 'C000000001'
ORDER BY effective_from;
-- Expected:
-- Row 1: RETAIL, 2023-01-15 → 2025-03-15, is_current = FALSE
-- Row 2: PREMIUM, 2025-03-16 → NULL, is_current = TRUE
```

---

### Section 7C.3 — Insert a Post-Change Transaction

Load a new fact row for C000000001 dated 20 March 2025 — after the upgrade. This row should link to the PREMIUM surrogate key.

```sql
-- Load one post-upgrade transaction for C000000001
-- The dim lookup joins on is_current = TRUE → picks up the PREMIUM row
INSERT INTO fact_transaction (
    date_id, dim_customer_sk, dim_product_sk,
    dim_branch_sk, dim_channel_sk,
    txn_type, direction, status, source_txn_id, amount_sar
)
SELECT
    dd.date_id,
    dc.dim_customer_sk,    -- This will be the PREMIUM row's surrogate key
    dp.dim_product_sk,
    db.dim_branch_sk,
    dch.dim_channel_sk,
    'MURABAHA_PAYMENT', 'D', 'POSTED', 'CBS-2025-0021', 22000.00
FROM dim_date     dd  ON dd.full_date   = '2025-03-20'
JOIN dim_customer dc  ON dc.customer_id = 'C000000001' AND dc.is_current = TRUE
JOIN dim_product  dp  ON dp.product_id  = 'PROD-001'
JOIN dim_branch   db  ON db.branch_id   = 'RUH-01'
JOIN dim_channel  dch ON dch.channel_id = 'CHN-001';
```

> **Note:** The above uses an unusual `FROM ... ON` syntax for clarity. If Snowflake rejects it, use the standard `FROM ... JOIN` form below:

```sql
-- Alternative standard syntax
INSERT INTO fact_transaction (
    date_id, dim_customer_sk, dim_product_sk,
    dim_branch_sk, dim_channel_sk,
    txn_type, direction, status, source_txn_id, amount_sar
)
SELECT
    dd.date_id,
    dc.dim_customer_sk,
    dp.dim_product_sk,
    db.dim_branch_sk,
    dch.dim_channel_sk,
    'MURABAHA_PAYMENT', 'D', 'POSTED', 'CBS-2025-0021', 22000.00
FROM dim_date     dd
JOIN dim_customer dc  ON dc.customer_id = 'C000000001' AND dc.is_current = TRUE
JOIN dim_product  dp  ON dp.product_id  = 'PROD-001'
JOIN dim_branch   db  ON db.branch_id   = 'RUH-01'
JOIN dim_channel  dch ON dch.channel_id = 'CHN-001'
WHERE dd.full_date = '2025-03-20';
```

---

### Section 7C.4 — Verify Historical Accuracy

```sql
-- THE KEY VERIFICATION QUERY
-- This is what a SAMA auditor would run: show all transactions for C000000001
-- with the segment that was active at the time of each transaction
SELECT
    ft.source_txn_id,
    dd.full_date,
    dd.month_name_en,
    dc.customer_segment,    -- RETAIL for Jan/Feb rows, PREMIUM for Mar row
    dc.effective_from       AS segment_valid_from,
    ft.amount_sar,
    ft.txn_type
FROM fact_transaction ft
JOIN dim_date     dd ON ft.date_id         = dd.date_id
JOIN dim_customer dc ON ft.dim_customer_sk = dc.dim_customer_sk
WHERE dc.customer_id = 'C000000001'
ORDER BY dd.full_date;
```

**Expected result:**

| source_txn_id | full_date | customer_segment | amount_sar |
|---|---|---|---|
| CBS-2025-0001 | 2025-01-10 | RETAIL | 15,000.00 |
| CBS-2025-0006 | 2025-01-20 | RETAIL | 450.00 |
| CBS-2025-0010 | 2025-02-05 | RETAIL | 75,000.00 |
| CBS-2025-0019 | 2025-03-12 | RETAIL | 680.00 |
| CBS-2025-0021 | 2025-03-20 | PREMIUM | 22,000.00 |

The first four transactions permanently show RETAIL — because `dim_customer_sk` was stamped at load time with the surrogate key of the RETAIL row. The March 20 transaction shows PREMIUM because it was loaded after the upgrade and the `is_current = TRUE` lookup resolved to the PREMIUM row.

**This is SCD Type 2 working correctly.** No query-time date range logic was needed — the surrogate key join handles everything automatically.

```sql
-- Cross-check: confirm two different dim_customer_sk values are in fact_transaction
SELECT DISTINCT ft.dim_customer_sk, dc.customer_segment, dc.effective_from
FROM fact_transaction ft
JOIN dim_customer dc ON ft.dim_customer_sk = dc.dim_customer_sk
WHERE dc.customer_id = 'C000000001'
ORDER BY dc.effective_from;
-- Expected: 2 rows with different dim_customer_sk values
```

**Lab 7C complete.** You have proven SCD Type 2 behaviour. Move to Lab 7D.

---

## Lab 7D — Time Travel and Query Profile

**Objective:** Explore Snowflake's Time Travel feature using the data you have built, run a SAMA-style audit query at a historical timestamp, use `LAST_QUERY_ID()` for statement-based time travel, and read a Query Profile.

**Duration:** 30 minutes

> **Free tier note:** The free trial gives you **1 day** of Time Travel retention (not 90 days). This means you can query your tables as they existed at any point within the past 24 hours. For the purposes of this lab, we will create scenarios within the current session to demonstrate the feature.

---

### Section 7D.1 — Time Travel Basics

```sql
USE ROLE SYSADMIN;
USE WAREHOUSE al_noor_etl_wh;
USE DATABASE al_noor_dwh;
USE SCHEMA analytics;
```

First, capture the current timestamp — this will be your "before" point for the Time Travel queries.

```sql
-- Record the current timestamp
SELECT CURRENT_TIMESTAMP() AS snapshot_before_changes;
```

**Copy the timestamp value from the result.** You will use it in the Time Travel query below. It looks like: `2025-01-15 14:32:00.000 +0000`

---

### Section 7D.2 — Make a Change to Travel Back From

Insert two additional rows so you have a "before" and "after" state to query:

```sql
-- Insert 2 more transactions
INSERT INTO fact_transaction (
    date_id, dim_customer_sk, dim_product_sk,
    dim_branch_sk, dim_channel_sk,
    txn_type, direction, status, source_txn_id, amount_sar
)
SELECT
    dd.date_id,
    dc.dim_customer_sk,
    dp.dim_product_sk,
    db.dim_branch_sk,
    dch.dim_channel_sk,
    'AANI_TRANSFER', 'D', 'POSTED', 'CBS-2025-0022', 3500.00
FROM dim_date dd
JOIN dim_customer dc  ON dc.customer_id = 'C000000002' AND dc.is_current = TRUE
JOIN dim_product  dp  ON dp.product_id  = 'PROD-009'
JOIN dim_branch   db  ON db.branch_id   = 'JED-01'
JOIN dim_channel  dch ON dch.channel_id = 'CHN-001'
WHERE dd.full_date = '2025-03-20';
```

```sql
-- Current row count after the new insert
SELECT COUNT(*) AS current_count FROM fact_transaction;
-- Should be: 22 (21 from previous labs + 1 new)
```

---

### Section 7D.3 — Query the Table at a Past Timestamp

Replace `YOUR_TIMESTAMP_HERE` with the timestamp you copied in Section 7D.1:

```sql
-- Time Travel: how many rows were in fact_transaction BEFORE your last insert?
SELECT COUNT(*) AS count_before_insert
FROM fact_transaction
AT (TIMESTAMP => 'YOUR_TIMESTAMP_HERE'::TIMESTAMP_TZ);
-- Expected: 21 rows (before CBS-2025-0022 was inserted)
```

This is the same query a SAMA auditor would run: "show me the transaction counts as they existed at the time the January report was generated."

---

### Section 7D.4 — Statement-Based Time Travel

This is more precise than timestamp-based travel. You reference a specific SQL statement ID.

```sql
-- Delete a row to simulate an accidental deletion
DELETE FROM fact_transaction
WHERE source_txn_id = 'CBS-2025-0001';

-- Capture the ID of the DELETE statement
SELECT LAST_QUERY_ID() AS delete_statement_id;
```

Copy the query ID from the result. It looks like: `019c3b5d-0504-ba6e-0001-23d200010012`

```sql
-- Verify the deletion happened
SELECT COUNT(*) FROM fact_transaction WHERE source_txn_id = 'CBS-2025-0001';
-- Expected: 0 rows
```

```sql
-- Time Travel: see the table state BEFORE the DELETE ran
-- Replace YOUR_QUERY_ID_HERE with the ID you copied above
SELECT source_txn_id, amount_sar, txn_type
FROM fact_transaction
BEFORE (STATEMENT => 'YOUR_QUERY_ID_HERE')
WHERE source_txn_id = 'CBS-2025-0001';
-- Expected: 1 row — the record that was deleted
```

```sql
-- Recover the deleted row using Time Travel as the source
-- This is how you restore accidentally deleted data without any backup files
INSERT INTO fact_transaction
SELECT *
FROM fact_transaction
BEFORE (STATEMENT => 'YOUR_QUERY_ID_HERE')
WHERE source_txn_id = 'CBS-2025-0001';
```

```sql
-- Verify the recovery
SELECT COUNT(*) FROM fact_transaction WHERE source_txn_id = 'CBS-2025-0001';
-- Expected: 1 row — successfully recovered
```

---

### Section 7D.5 — Run a Complex Analytical Query and Read the Query Profile

Run this multi-join SAMA-style query:

```sql
-- SAMA-style quarterly summary: Islamic vs conventional by region
SELECT
    dd.quarter,
    db.region,
    CASE dp.is_sharia_compliant
        WHEN TRUE  THEN 'Islamic'
        ELSE            'Conventional'
    END                             AS finance_type,
    COUNT(ft.fact_txn_sk)           AS txn_count,
    SUM(ft.amount_sar)              AS total_volume_sar,
    ROUND(AVG(ft.amount_sar), 2)    AS avg_txn_sar,
    COUNT(DISTINCT ft.dim_customer_sk) AS unique_customers
FROM fact_transaction ft
JOIN dim_date    dd  ON ft.date_id        = dd.date_id
JOIN dim_branch  db  ON ft.dim_branch_sk  = db.dim_branch_sk
JOIN dim_product dp  ON ft.dim_product_sk = dp.dim_product_sk
GROUP BY dd.quarter, db.region, dp.is_sharia_compliant
ORDER BY dd.quarter, db.region, finance_type;
```

After the query finishes, look at the **right panel** of the SQL editor. You will see tabs:

```
Results  |  Query Details  |  Query Profile
```

Click **Query Profile**. If you do not see it as a tab, click the **Query Details** tab first — there will be a link inside it that says "View Query Profile". Clicking that opens the full profile view.

**What to look at in the Query Profile:**

1. **The execution plan graph** — each node is an operation (TableScan, Join, Aggregate). The flow goes from bottom (data sources) to top (output).

2. **Bytes scanned** — how much data was read from storage. With 22 rows, this will be tiny. On a real billion-row table, this is where you measure the effectiveness of micro-partition pruning.

3. **Partitions scanned / Partitions total** — if this shows `1 / 1` for each table, all data fits in one micro-partition (expected at our lab scale). At production scale you want to see a small fraction of total partitions scanned.

4. **Time breakdown** — hover over any node to see how long that operation took. On a complex query, this tells you whether your bottleneck is I/O (TableScan), memory (Join or Aggregate), or network.

5. **Most expensive node** — the query profiler highlights the slowest node in orange or red. In a well-tuned query this should be the final aggregation, not a join or scan.

---

### Section 7D.6 — Zero-Copy Clone

```sql
-- Clone the entire analytics schema — instant, no storage cost on free tier
-- This is useful for creating a dev/test copy without duplicating data
CREATE SCHEMA al_noor_dwh.analytics_backup
CLONE al_noor_dwh.analytics;
```

```sql
-- Verify the clone contains all tables
SHOW TABLES IN SCHEMA al_noor_dwh.analytics_backup;
-- Expected: same tables as analytics schema
```

```sql
-- Query the cloned fact table — it has exactly the same data
SELECT COUNT(*) FROM al_noor_dwh.analytics_backup.fact_transaction;
```

Modify data in the original schema — the clone is unaffected (copy-on-write semantics). This is the safe way to run destructive transformations in development.

---

### Section 7D.7 — Clean Up

When you have finished all four labs, suspend the warehouse to stop consuming free trial credits:

```sql
-- Suspend the warehouse immediately (do not wait for auto-suspend)
ALTER WAREHOUSE al_noor_etl_wh SUSPEND;
```

```sql
-- Confirm it is suspended
SHOW WAREHOUSES LIKE 'al_noor_etl_wh';
-- Check the STATE column — should show SUSPENDED
```

You can also verify visually: left icon bar → **Admin** → **Warehouses** → look for `al_noor_etl_wh` — its status dot should be grey (suspended), not green (running).

---

## Lab Summary — What You Built

| Lab | What was built | Key concept demonstrated |
|---|---|---|
| 7A | Database, schemas, warehouse, 5 dimension tables, DIM_DATE populated | Snowflake object hierarchy, GENERATOR syntax, Saudi weekend DOW numbering |
| 7B | 20 fact rows loaded via dimension lookup JOIN, 3 analytical queries | Star schema join pattern, window functions for % of total |
| 7C | SCD Type 2 applied to C000000001, historical accuracy verified | Surrogate key stamping, dual-row SCD2 pattern, SAMA retroactive audit |
| 7D | Time Travel at timestamp, statement-based recovery, Query Profile read | Snowflake Time Travel, LAST_QUERY_ID(), partition pruning metrics |

---

## Common Errors and How to Fix Them

| Error | Cause | Fix |
|---|---|---|
| `No active warehouse selected` | `USE WAREHOUSE` not run | Run `USE WAREHOUSE al_noor_etl_wh;` |
| `Object does not exist` on a table | Wrong schema context | Run `USE SCHEMA al_noor_dwh.analytics;` |
| `INSERT has 0 rows` | A JOIN in the INSERT found no match | Run the dimension tables separately to check the natural keys match |
| Time Travel query returns no rows | Timestamp is beyond 1-day free tier retention | Use `OFFSET` instead: `AT (OFFSET => -3600)` for 1 hour ago |
| `DAYOFWEEK` returning unexpected values | DOW numbering differs from PostgreSQL | In Snowflake: Sunday=0, Friday=5, Saturday=6. Use `IN (5, 6)` not `IN (6, 7)` |
| Warehouse keeps resuming and billing | `AUTO_SUSPEND` not set | `ALTER WAREHOUSE al_noor_etl_wh SET AUTO_SUSPEND = 60;` |
| `Insufficient privileges` | Wrong role active | `USE ROLE SYSADMIN;` for object creation; `ACCOUNTADMIN` only for billing |
| Cannot find "Worksheets" in the sidebar | New Snowsight UI — Worksheets renamed | Click `+` (Create) → **SQL File** — this is the new worksheet |
| Cannot find Query Profile tab | Results panel not fully expanded | Click the chevron `›` on the right edge of the results panel to expand it; look for **Query Profile** tab |
| Database/schema dropdowns in editor show wrong values | UI dropdowns and `USE` statements can get out of sync | Always confirm with `SELECT CURRENT_DATABASE(), CURRENT_SCHEMA();` |
| Cannot find query history | Looking in wrong place | Left icon bar → **Activity** (clock icon) → **Query History** |
| Cannot see tables after creating them | Data explorer not refreshed | Left icon bar → **Data** icon → click the refresh icon next to `al_noor_dwh` |

> **Day 8 preparation.** Keep your Snowflake trial account active. The `al_noor_dwh` database and all schemas from these labs must be intact. Day 8 extends the EDW with a compliance mart table (`FACT_OB_API_CALL`) and the Open Banking consent domain — built directly on top of what you created today.