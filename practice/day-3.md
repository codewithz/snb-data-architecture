# SNB Data Engineering Programme
## Practice Lab — SQL Query Optimisation
### ShopSmart E-Commerce Database | snb_practice

---

> **A warm welcome to this practice lab.**
>
> This lab has been prepared especially for you to practise the
> concepts covered on Day 3 at your own pace, in your own time.
> There are no wrong answers here — only learning opportunities.
> Every exercise is designed to help you see the difference between
> a query that works and a query that works well.
>
> Please take your time with each section. Read the comments
> carefully. Run every query. Compare the results. The goal is
> not to finish quickly — it is to understand deeply.
>
> We are using a simple e-commerce domain called **ShopSmart**
> so that you can focus entirely on the SQL concepts without
> worrying about banking terminology.
>
> We hope you enjoy this lab. You have worked hard to get here
> and you deserve to see the results of that effort.

---

## How to Use This Lab

1. Open **pgAdmin** on your machine
2. Follow **Part 1** exactly — it creates everything you need
3. Work through **Parts 2 through 5** at your own pace
4. Each exercise shows you a BEFORE and AFTER
5. Read every comment — they explain the WHY, not just the HOW
6. The **Challenge Section** at the end is for you to try on your own

---

## PART 1 — Setting Up Your Practice Environment

*This section creates your database, tables, and sample data.*
*Please run these steps in order. Each step builds on the previous one.*

---

### Step 1.1 — Create the Practice Database

Open pgAdmin, connect to your PostgreSQL server, open the
Query Tool, and run this first:

```sql
-- ============================================================
-- Welcome! Let us create your practice database.
-- This database is called snb_practice and will be used
-- throughout this entire lab.
-- ============================================================

CREATE DATABASE snb_practice
    ENCODING 'UTF8';
```

After running the above, **disconnect and reconnect to snb_practice**
before continuing. In pgAdmin, right-click on snb_practice in the
left panel and select Query Tool.

---

### Step 1.2 — Create the Tables

```sql
-- ============================================================
-- ShopSmart E-Commerce Schema
-- Four simple tables: customers, products, orders, order_items
-- plus a payments table.
-- We have kept the structure simple so you can focus entirely
-- on the SQL optimisation concepts.
-- ============================================================


-- CUSTOMERS TABLE
-- Stores basic information about each customer.
-- Notice: no index yet on email or city — we will add those later
-- and you will see the difference yourself.

CREATE TABLE customers (
    customer_id   SERIAL        NOT NULL,
    full_name     VARCHAR(100)  NOT NULL,
    email         VARCHAR(150)  NOT NULL,
    city          VARCHAR(50)   NOT NULL,
    country       VARCHAR(50)   NOT NULL DEFAULT 'Saudi Arabia',
    membership    VARCHAR(20)   NOT NULL DEFAULT 'STANDARD'
                  CHECK (membership IN ('STANDARD','GOLD','PLATINUM')),
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    registered_at DATE          NOT NULL DEFAULT CURRENT_DATE,
    CONSTRAINT pk_customers PRIMARY KEY (customer_id)
);


-- PRODUCTS TABLE
-- Stores the products available in the ShopSmart store.

CREATE TABLE products (
    product_id    SERIAL        NOT NULL,
    product_name  VARCHAR(200)  NOT NULL,
    category      VARCHAR(50)   NOT NULL,
    price         NUMERIC(10,2) NOT NULL CHECK (price > 0),
    stock_qty     INTEGER       NOT NULL DEFAULT 0,
    is_available  BOOLEAN       NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_products PRIMARY KEY (product_id)
);


-- ORDERS TABLE
-- Every order placed by a customer.
-- order_status will have very skewed data — most orders are
-- DELIVERED. We will use this for a partial index exercise.

CREATE TABLE orders (
    order_id      SERIAL        NOT NULL,
    customer_id   INTEGER       NOT NULL,
    order_date    DATE          NOT NULL,
    order_status  VARCHAR(20)   NOT NULL DEFAULT 'PENDING'
                  CHECK (order_status IN (
                      'PENDING','PROCESSING','SHIPPED',
                      'DELIVERED','CANCELLED','REFUNDED')),
    total_amount  NUMERIC(10,2) NOT NULL CHECK (total_amount >= 0),
    channel       VARCHAR(20)   NOT NULL
                  CHECK (channel IN ('MOBILE','WEB','IN_STORE')),
    CONSTRAINT pk_orders PRIMARY KEY (order_id),
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);


-- ORDER_ITEMS TABLE
-- Each row is one product within one order.
-- This is typically the largest table in any e-commerce system.

CREATE TABLE order_items (
    item_id       SERIAL        NOT NULL,
    order_id      INTEGER       NOT NULL,
    product_id    INTEGER       NOT NULL,
    quantity      INTEGER       NOT NULL CHECK (quantity > 0),
    unit_price    NUMERIC(10,2) NOT NULL CHECK (unit_price > 0),
    line_total    NUMERIC(10,2) NOT NULL,
    CONSTRAINT pk_order_items PRIMARY KEY (item_id),
    CONSTRAINT fk_items_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
    CONSTRAINT fk_items_product
        FOREIGN KEY (product_id) REFERENCES products(product_id)
);


-- PAYMENTS TABLE
-- One payment record per order.
-- payment_status is skewed — most payments are COMPLETED.

CREATE TABLE payments (
    payment_id     SERIAL        NOT NULL,
    order_id       INTEGER       NOT NULL,
    payment_date   DATE          NOT NULL,
    payment_method VARCHAR(30)   NOT NULL
                   CHECK (payment_method IN (
                       'CREDIT_CARD','MADA','STC_PAY',
                       'APPLE_PAY','BANK_TRANSFER','COD')),
    payment_status VARCHAR(20)   NOT NULL DEFAULT 'COMPLETED'
                   CHECK (payment_status IN (
                       'PENDING','COMPLETED','FAILED','REFUNDED')),
    amount         NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    CONSTRAINT pk_payments PRIMARY KEY (payment_id),
    CONSTRAINT fk_payments_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
);
```

---

### Step 1.3 — Insert Sample Data

*Please be patient while this runs — it is inserting a large*
*amount of data so that you can see real performance differences.*

```sql
-- ============================================================
-- INSERTING SAMPLE DATA
-- We are inserting enough rows to make the performance
-- differences between indexed and non-indexed queries visible.
--
-- customers:   10,000 rows
-- products:       500 rows
-- orders:      50,000 rows
-- order_items: 150,000 rows
-- payments:    50,000 rows
--
-- This may take 30-60 seconds. Please wait for it to finish.
-- ============================================================


-- Insert 10,000 customers
INSERT INTO customers (full_name, email, city, membership, is_active, registered_at)
SELECT
    'Customer ' || gs                                AS full_name,
    'customer' || gs || '@shopsmart.sa'              AS email,
    CASE (gs % 5)
        WHEN 0 THEN 'Riyadh'
        WHEN 1 THEN 'Jeddah'
        WHEN 2 THEN 'Dammam'
        WHEN 3 THEN 'Mecca'
        ELSE        'Medina'
    END                                              AS city,
    CASE (gs % 10)
        WHEN 0 THEN 'PLATINUM'
        WHEN 1 THEN 'GOLD'
        ELSE        'STANDARD'
    END                                              AS membership,
    CASE WHEN gs % 20 = 0 THEN FALSE ELSE TRUE END   AS is_active,
    CURRENT_DATE - (gs % 730)                        AS registered_at
FROM generate_series(1, 10000) AS gs;


-- Insert 500 products
INSERT INTO products (product_name, category, price, stock_qty, is_available)
SELECT
    'Product ' || gs                                 AS product_name,
    CASE (gs % 6)
        WHEN 0 THEN 'Electronics'
        WHEN 1 THEN 'Clothing'
        WHEN 2 THEN 'Books'
        WHEN 3 THEN 'Home & Garden'
        WHEN 4 THEN 'Sports'
        ELSE        'Food & Beverages'
    END                                              AS category,
    ROUND((RANDOM() * 990 + 10)::NUMERIC, 2)        AS price,
    (RANDOM() * 1000)::INTEGER                       AS stock_qty,
    CASE WHEN gs % 15 = 0 THEN FALSE ELSE TRUE END   AS is_available
FROM generate_series(1, 500) AS gs;


-- Insert 50,000 orders
-- Notice: 85% are DELIVERED — this skew is intentional for
-- the partial index exercise later
INSERT INTO orders (customer_id, order_date, order_status, total_amount, channel)
SELECT
    (RANDOM() * 9999 + 1)::INTEGER                   AS customer_id,
    CURRENT_DATE - (RANDOM() * 365)::INTEGER         AS order_date,
    CASE (RANDOM() * 100)::INTEGER
        WHEN 0  THEN 'PENDING'
        WHEN 1  THEN 'PROCESSING'
        WHEN 2  THEN 'SHIPPED'
        WHEN 3  THEN 'CANCELLED'
        WHEN 4  THEN 'REFUNDED'
        ELSE        'DELIVERED'
    END                                              AS order_status,
    ROUND((RANDOM() * 4900 + 100)::NUMERIC, 2)       AS total_amount,
    CASE (gs % 3)
        WHEN 0 THEN 'MOBILE'
        WHEN 1 THEN 'WEB'
        ELSE        'IN_STORE'
    END                                              AS channel
FROM generate_series(1, 50000) AS gs;


-- Insert 150,000 order items (3 items per order on average)
INSERT INTO order_items (order_id, product_id, quantity, unit_price, line_total)
SELECT
    (RANDOM() * 49999 + 1)::INTEGER                  AS order_id,
    (RANDOM() * 499  + 1)::INTEGER                   AS product_id,
    (RANDOM() * 4    + 1)::INTEGER                   AS quantity,
    ROUND((RANDOM() * 490 + 10)::NUMERIC, 2)         AS unit_price,
    ROUND((RANDOM() * 490 + 10)::NUMERIC *
          (RANDOM() * 4 + 1)::INTEGER, 2)            AS line_total
FROM generate_series(1, 150000) AS gs;


-- Insert 50,000 payments (one per order)
-- Notice: 90% are COMPLETED — skew for partial index exercise
INSERT INTO payments (order_id, payment_date, payment_method,
                      payment_status, amount)
SELECT
    gs                                               AS order_id,
    CURRENT_DATE - (RANDOM() * 365)::INTEGER         AS payment_date,
    CASE (gs % 6)
        WHEN 0 THEN 'CREDIT_CARD'
        WHEN 1 THEN 'MADA'
        WHEN 2 THEN 'STC_PAY'
        WHEN 3 THEN 'APPLE_PAY'
        WHEN 4 THEN 'BANK_TRANSFER'
        ELSE        'COD'
    END                                              AS payment_method,
    CASE (RANDOM() * 100)::INTEGER
        WHEN 0 THEN 'PENDING'
        WHEN 1 THEN 'FAILED'
        WHEN 2 THEN 'REFUNDED'
        ELSE        'COMPLETED'
    END                                              AS payment_status,
    ROUND((RANDOM() * 4900 + 100)::NUMERIC, 2)       AS amount
FROM generate_series(1, 50000) AS gs;


-- Update statistics so PostgreSQL has accurate information
-- about our new data. Always run this after large inserts.
ANALYZE customers;
ANALYZE products;
ANALYZE orders;
ANALYZE order_items;
ANALYZE payments;
```

---

### Step 1.4 — Verify Your Data

*Run these quick checks to confirm everything loaded correctly.*
*You should see row counts matching the expected numbers.*

```sql
-- Quick row count check
-- Expected: customers=10000, products=500,
--           orders=50000, order_items=150000, payments=50000

SELECT 'customers'   AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL
SELECT 'products',   COUNT(*) FROM products
UNION ALL
SELECT 'orders',     COUNT(*) FROM orders
UNION ALL
SELECT 'order_items',COUNT(*) FROM order_items
UNION ALL
SELECT 'payments',   COUNT(*) FROM payments;
```

If all counts look correct — congratulations, your environment
is ready. Let us begin the exercises.

---

## PART 2 — Understanding Sequential Scans and Index Scans

---

### Exercise 2.1 — Your First EXPLAIN ANALYZE

*Before we talk about indexes, let us first understand what*
*EXPLAIN ANALYZE tells us. This is the most important tool*
*for understanding query performance.*

```sql
-- ============================================================
-- WHAT IS EXPLAIN ANALYZE?
--
-- EXPLAIN ANALYZE runs your query and shows you:
-- 1. What strategy PostgreSQL chose to find the data
-- 2. How long each step actually took
-- 3. How many rows were processed vs how many were returned
--
-- Think of it like a GPS journey report — not just the route
-- but exactly how long each road took.
-- ============================================================


-- Run this query and study the output carefully
EXPLAIN ANALYZE
SELECT customer_id, full_name, email, city
FROM customers
WHERE city = 'Riyadh';
```

**What to look for in the output:**

```
-- You will see something like this:
--
-- Seq Scan on customers
--   (cost=0.00..236.00 rows=2000 width=45)
--   (actual time=0.015..3.842 rows=2000 loops=1)
--   Filter: ((city)::text = 'Riyadh')
--   Rows Removed by Filter: 8000
-- Planning Time: 0.3 ms
-- Execution Time: 4.1 ms
--
-- KEY THINGS TO READ:
--
-- "Seq Scan" → The database read EVERY row in the table
--              looking for Riyadh customers.
--              On a 10,000 row table this is acceptable.
--              On a 10 million row table this would be very slow.
--
-- "Rows Removed by Filter: 8000" → It read 10,000 rows,
--              found 2,000 matching, and threw away 8,000.
--              That is 80% wasted work.
--
-- "Execution Time: ~4ms" → Remember this number.
--              We will compare it after adding an index.
```

---

### Exercise 2.2 — Single Column Index

*Now let us add an index and see what changes.*

```sql
-- ============================================================
-- ADDING A SINGLE COLUMN INDEX
--
-- We are telling PostgreSQL: "Please keep a sorted list of
-- all city values and which rows they belong to."
-- This way, when someone asks for city = 'Riyadh',
-- PostgreSQL does not need to read all 10,000 rows.
-- It jumps directly to the Riyadh entries.
-- ============================================================

CREATE INDEX idx_customers_city
ON customers (city);


-- Now run the SAME query again with EXPLAIN ANALYZE
EXPLAIN ANALYZE
SELECT customer_id, full_name, email, city
FROM customers
WHERE city = 'Riyadh';
```

**What changed in the output:**

```
-- You should now see something like this:
--
-- Bitmap Heap Scan on customers
--   (actual time=0.312..1.124 rows=2000 loops=1)
--   Recheck Cond: ((city)::text = 'Riyadh')
--   -> Bitmap Index Scan on idx_customers_city
--      (actual time=0.287..0.287 rows=2000 loops=1)
--         Index Cond: ((city)::text = 'Riyadh')
-- Execution Time: 1.3 ms
--
-- WHAT CHANGED:
--
-- "Bitmap Index Scan" → PostgreSQL used the index.
--   It looked up 'Riyadh' in the index first,
--   got the list of matching row locations,
--   then fetched only those rows.
--
-- "Execution Time: ~1.3ms" vs the previous ~4ms
--   That is 3x faster — and this is only 10,000 rows.
--   On 10 million rows the difference would be
--   measured in seconds vs milliseconds.
--
-- No more "Rows Removed by Filter" — because PostgreSQL
-- only fetched the rows it needed.
```

---

### Exercise 2.3 — What Happens When city is NOT the First Filter

```sql
-- ============================================================
-- IMPORTANT LESSON: Indexes help only when the indexed
-- column is part of your WHERE clause.
--
-- This query filters on membership AND city.
-- We only have an index on city — not on membership.
-- Watch what happens.
-- ============================================================

EXPLAIN ANALYZE
SELECT customer_id, full_name, city, membership
FROM customers
WHERE membership = 'GOLD'
  AND city = 'Jeddah';

-- PostgreSQL will use the city index to find Jeddah customers,
-- then filter those results for GOLD membership.
-- This is still better than a full sequential scan —
-- but not as fast as having both columns indexed together.
-- We will fix this in Exercise 2.4.
```

---

### Exercise 2.4 — Composite Index (Two Columns Together)

```sql
-- ============================================================
-- COMPOSITE INDEX
--
-- When your queries regularly filter on TWO columns together,
-- a composite index is much more efficient than two
-- separate single-column indexes.
--
-- Think of it like a library organised first by subject,
-- then alphabetically by author within each subject.
-- You can find "Engineering books by authors starting with A"
-- instantly — without scanning all books.
-- ============================================================

CREATE INDEX idx_customers_membership_city
ON customers (membership, city);


-- Run the same query again
EXPLAIN ANALYZE
SELECT customer_id, full_name, city, membership
FROM customers
WHERE membership = 'GOLD'
  AND city = 'Jeddah';

-- You should now see an Index Scan using the composite index.
-- Both conditions are satisfied in one index lookup.


-- ============================================================
-- IMPORTANT: Column Order in a Composite Index
--
-- The index is on (membership, city) — membership is first.
-- This means:
--
-- ✅ Works well:  WHERE membership = 'GOLD'
-- ✅ Works well:  WHERE membership = 'GOLD' AND city = 'Jeddah'
-- ⚠️ Less ideal:  WHERE city = 'Jeddah' (only second column)
--
-- Always put the column you filter on most often FIRST.
-- ============================================================

-- Let us prove this — filter on city only (second column)
EXPLAIN ANALYZE
SELECT customer_id, full_name, city, membership
FROM customers
WHERE city = 'Jeddah';

-- PostgreSQL may use the idx_customers_city index we created
-- earlier, or it may use the composite index partially.
-- Either way — notice it does NOT get the full benefit of
-- the composite index when only the second column is used.
```

---

## PART 3 — Partial Indexes

*This is one of the most powerful and underused index types.*
*Please read this section carefully — it will surprise you.*

---

### Exercise 3.1 — The Problem with Skewed Data

```sql
-- ============================================================
-- THE SKEWED DATA PROBLEM
--
-- Look at our orders table. Most orders are DELIVERED.
-- Let us see the exact numbers.
-- ============================================================

SELECT order_status, COUNT(*) AS count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
FROM orders
GROUP BY order_status
ORDER BY count DESC;

-- You will see something like:
-- DELIVERED   ~42,500   85%
-- CANCELLED   ~  2,500   5%
-- PENDING     ~  1,250   2.5%
-- PROCESSING  ~  1,250   2.5%
-- SHIPPED     ~  1,250   2.5%
-- REFUNDED    ~  1,250   2.5%
--
-- 85% of orders are DELIVERED.
-- The operations team NEVER looks at delivered orders in their
-- daily work. They only care about PENDING, PROCESSING,
-- SHIPPED, CANCELLED, REFUNDED.
```

---

### Exercise 3.2 — Full Index vs Partial Index

```sql
-- ============================================================
-- STEP 1: Create a full index on order_status
-- This indexes ALL 50,000 rows
-- ============================================================

CREATE INDEX idx_orders_status_full
ON orders (order_status, order_date DESC);


-- Check the size of this full index
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_indexes
WHERE tablename = 'orders'
  AND indexname = 'idx_orders_status_full';

-- Note the size. We will compare it with the partial index.


-- ============================================================
-- STEP 2: Create a PARTIAL index
-- This indexes ONLY the rows the operations team cares about
-- We exclude DELIVERED orders entirely
-- ============================================================

CREATE INDEX idx_orders_status_partial
ON orders (order_status, order_date DESC)
WHERE order_status != 'DELIVERED';


-- Check the size of the partial index
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_indexes
WHERE tablename = 'orders'
  AND indexname IN (
      'idx_orders_status_full',
      'idx_orders_status_partial'
  );

-- ============================================================
-- The partial index should be roughly 15% the size of the
-- full index — because it only contains the 15% of rows
-- that are NOT DELIVERED.
--
-- A smaller index means:
-- → Less memory used (fits in RAM more easily)
-- → Faster lookups
-- → Faster updates when orders change status
-- ============================================================


-- STEP 3: Run the operations team query
EXPLAIN ANALYZE
SELECT order_id, customer_id, order_date, order_status, total_amount
FROM orders
WHERE order_status IN ('PENDING', 'PROCESSING', 'SHIPPED')
  AND order_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY order_date DESC;

-- PostgreSQL will use the partial index.
-- It reads only the relevant 15% of rows — completely
-- ignoring the 85% of DELIVERED orders.
```

---

## PART 4 — Covering Indexes

---

### Exercise 4.1 — The Two-Step Index Lookup Problem

```sql
-- ============================================================
-- NORMAL INDEX LOOKUP — TWO STEPS
--
-- When you use a regular index, PostgreSQL does TWO things:
-- Step 1: Look up the matching rows in the index
-- Step 2: Go to the main table to fetch the other columns
--
-- Step 2 is called a "Heap Fetch" — and on large tables
-- with many matching rows, it is the expensive part.
-- ============================================================

-- First, let us create a regular index on customer_id in orders
CREATE INDEX idx_orders_customer
ON orders (customer_id);


-- Run this query and look at the execution plan
EXPLAIN ANALYZE
SELECT order_id, order_date, order_status, total_amount, channel
FROM orders
WHERE customer_id = 500;

-- You will see:
-- Index Scan using idx_orders_customer on orders
--   Index Cond: (customer_id = 500)
--
-- The index found the right rows — but then PostgreSQL
-- had to visit the main table to get order_date,
-- order_status, total_amount, and channel.
-- That is the "Heap Fetch" happening behind the scenes.
```

---

### Exercise 4.2 — Add a Covering Index

```sql
-- ============================================================
-- COVERING INDEX — ONE STEP
--
-- A covering index includes all the columns the query needs
-- directly inside the index itself.
-- PostgreSQL never needs to visit the main table at all.
--
-- Think of it like a book index that not only tells you
-- the page number but also summarises what is on that page.
-- You never need to open the book.
-- ============================================================

-- Drop the regular index first
DROP INDEX idx_orders_customer;

-- Create the covering index
CREATE INDEX idx_orders_customer_covering
ON orders (customer_id, order_date DESC)
INCLUDE (order_status, total_amount, channel);


-- Run the SAME query again
EXPLAIN ANALYZE
SELECT order_id, order_date, order_status, total_amount, channel
FROM orders
WHERE customer_id = 500;

-- You should now see:
-- "Index Only Scan" instead of "Index Scan"
--
-- "Index Only Scan" means PostgreSQL answered the entire
-- query from the index alone — it never touched the main table.
-- This is the fastest possible execution.
--
-- The word "Only" is the key difference to look for.
```

---

## PART 5 — Writing Better Queries

*Indexes are only half the story. The way you write your query*
*also determines how fast it runs. This section covers three*
*patterns that every data engineer should know.*

---

### Exercise 5.1 — Never Use SELECT *

```sql
-- ============================================================
-- THE SELECT * PROBLEM
--
-- SELECT * fetches EVERY column — including large text columns,
-- columns you do not need, and in a real system, encrypted
-- columns containing sensitive data.
--
-- This matters for three reasons:
-- 1. More data to transfer = slower query
-- 2. Indexes cannot cover a SELECT * query
-- 3. You expose data the consumer does not need
-- ============================================================


-- BAD APPROACH — fetching everything
EXPLAIN ANALYZE
SELECT *
FROM order_items
WHERE order_id = 1000;

-- Note the "width" value in the cost estimate.
-- Width = average number of bytes per row being returned.
-- Larger width = more data being moved.


-- GOOD APPROACH — fetch only what you need
EXPLAIN ANALYZE
SELECT item_id, product_id, quantity, unit_price, line_total
FROM order_items
WHERE order_id = 1000;

-- Compare the "width" values between the two queries.
-- The specific columns query transfers less data per row.
--
-- On a query returning 10,000 rows across a network,
-- this difference becomes very significant.


-- ============================================================
-- PRACTICAL RULE:
-- Always write out the column names you need.
-- Never use SELECT * in production queries.
-- Your future colleagues — and your database server —
-- will thank you.
-- ============================================================
```

---

### Exercise 5.2 — EXISTS vs IN for Large Subqueries

```sql
-- ============================================================
-- EXISTS vs IN — When It Really Matters
--
-- Both EXISTS and IN can answer the question:
-- "Find customers who have placed at least one order."
--
-- But they work very differently internally:
--
-- IN    → Builds a complete list of all matching values
--          then checks each customer against that list.
--          Must process ALL matching rows.
--
-- EXISTS → Stops the moment it finds ONE matching row.
--          Does not need to process everything.
--
-- For large tables, EXISTS is almost always faster.
-- ============================================================


-- APPROACH 1: Using IN
-- This builds a list of ALL customer_ids from orders
-- then checks each customer against that list

EXPLAIN ANALYZE
SELECT customer_id, full_name, city, membership
FROM customers
WHERE customer_id IN (
    SELECT DISTINCT customer_id
    FROM orders
    WHERE order_status = 'PENDING'
);


-- APPROACH 2: Using EXISTS
-- This checks for the EXISTENCE of at least one matching row
-- Stops as soon as it finds the first match per customer

EXPLAIN ANALYZE
SELECT customer_id, full_name, city, membership
FROM customers c
WHERE EXISTS (
    SELECT 1
    FROM orders o
    WHERE o.customer_id = c.customer_id
      AND o.order_status = 'PENDING'
);

-- Compare the execution times between the two approaches.
-- On our 50,000 order dataset you may see a small difference.
-- On a dataset with millions of orders the difference
-- becomes very significant.
--
-- Note: SELECT 1 inside EXISTS is a convention.
-- We do not care WHAT is returned — only WHETHER
-- a matching row exists. Writing SELECT 1 makes
-- that intention clear to anyone reading the code.
```

---

### Exercise 5.3 — Window Functions vs Self-Joins

```sql
-- ============================================================
-- RUNNING TOTALS — The Right Way and the Wrong Way
--
-- A running total shows the cumulative sum up to each row.
-- For example: a customer's spending total after each order.
--
-- The WRONG WAY: join the table to itself
-- The RIGHT WAY: use a window function
-- ============================================================


-- WRONG WAY — Self-Join
-- For every order, sum all orders placed before it
-- This joins the orders table to itself — very expensive

EXPLAIN ANALYZE
SELECT
    o1.order_id,
    o1.order_date,
    o1.total_amount,
    SUM(o2.total_amount) AS running_total
FROM orders o1
JOIN orders o2
    ON o2.customer_id = o1.customer_id
    AND o2.order_date <= o1.order_date
WHERE o1.customer_id = 500
GROUP BY o1.order_id, o1.order_date, o1.total_amount
ORDER BY o1.order_date;

-- Note the execution time. This is the self-join approach.
-- For each order row, it scans all previous orders.
-- Very slow at scale.


-- RIGHT WAY — Window Function
-- One pass through the data, computing the running total
-- as it goes. No self-join needed.

EXPLAIN ANALYZE
SELECT
    order_id,
    order_date,
    total_amount,
    SUM(total_amount) OVER (
        PARTITION BY customer_id
        ORDER BY order_date
    ) AS running_total
FROM orders
WHERE customer_id = 500
ORDER BY order_date;

-- ============================================================
-- The window function approach:
-- → Makes ONE pass through the relevant rows
-- → Computes the cumulative sum as it goes
-- → No join required
-- → Same result, dramatically less work
--
-- Window functions follow this pattern:
-- FUNCTION() OVER (PARTITION BY column ORDER BY column)
--
-- PARTITION BY  = "reset the calculation for each group"
--                 (here: reset per customer)
-- ORDER BY      = "accumulate in this order"
--                 (here: chronologically by date)
-- ============================================================
```

---

### Exercise 5.4 — Running Total Across All Customers

```sql
-- ============================================================
-- Let us try a more interesting window function example.
-- We want to rank customers by their total spending
-- and see each customer's rank within their city.
-- ============================================================

SELECT
    c.customer_id,
    c.full_name,
    c.city,
    c.membership,
    SUM(o.total_amount)        AS total_spending,
    RANK() OVER (
        PARTITION BY c.city
        ORDER BY SUM(o.total_amount) DESC
    )                          AS rank_in_city,
    RANK() OVER (
        ORDER BY SUM(o.total_amount) DESC
    )                          AS overall_rank
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_status = 'DELIVERED'
GROUP BY c.customer_id, c.full_name, c.city, c.membership
ORDER BY c.city, rank_in_city
LIMIT 30;

-- ============================================================
-- This query uses TWO window functions simultaneously.
-- rank_in_city  → ranks customers within their own city
-- overall_rank  → ranks customers across all cities
--
-- Window functions are computed AFTER the GROUP BY and
-- WHERE clauses — so they work on the already-aggregated data.
-- ============================================================
```

---

## PART 6 — Transaction Control

*This section demonstrates how to keep your data safe*
*when multiple operations must succeed or fail together.*

---

### Exercise 6.1 — Basic Transaction

```sql
-- ============================================================
-- WHAT IS A TRANSACTION?
--
-- A transaction groups multiple SQL statements into one
-- atomic unit. Either ALL succeed or ALL are rolled back.
--
-- Imagine a customer places an order:
-- Step 1: Insert the order record
-- Step 2: Reduce the product stock
-- Step 3: Insert the payment record
--
-- If Step 2 fails (product out of stock), we must undo
-- Step 1 as well. We cannot have an order without stock
-- being deducted.
--
-- This is what transactions protect against.
-- ============================================================


-- EXAMPLE: Place a new order with stock update

BEGIN; -- Start the transaction

-- Step 1: Insert the order
INSERT INTO orders (customer_id, order_date, order_status,
                    total_amount, channel)
VALUES (1, CURRENT_DATE, 'PENDING', 299.00, 'MOBILE')
RETURNING order_id; -- Show us the new order_id

-- Step 2: Reduce stock for the product being ordered
UPDATE products
SET stock_qty = stock_qty - 1
WHERE product_id = 1
  AND stock_qty > 0; -- Safety check: only if stock exists

-- Step 3: Insert payment
INSERT INTO payments (order_id, payment_date, payment_method,
                      payment_status, amount)
VALUES (
    (SELECT MAX(order_id) FROM orders WHERE customer_id = 1),
    CURRENT_DATE,
    'MADA',
    'COMPLETED',
    299.00
);

COMMIT; -- Everything succeeded — make it permanent

-- ============================================================
-- If anything between BEGIN and COMMIT had failed,
-- PostgreSQL would have automatically undone ALL changes.
-- The customer's order would not exist. The stock would
-- not have been reduced. The payment would not have been recorded.
-- This is ATOMICITY in action.
-- ============================================================
```

---

### Exercise 6.2 — Rollback When Something Goes Wrong

```sql
-- ============================================================
-- ROLLBACK — Undoing a Transaction
--
-- Sometimes you want to test something without committing it.
-- Or an error occurs and you need to undo your changes.
-- ============================================================

BEGIN;

-- Make some changes
UPDATE products
SET price = price * 1.10  -- Increase all prices by 10%
WHERE category = 'Electronics';

-- Check what the new prices look like
SELECT product_id, product_name, price
FROM products
WHERE category = 'Electronics'
LIMIT 5;

-- Hmm — actually we made a mistake. We did not mean to do this.
-- Let us undo everything since BEGIN.

ROLLBACK;

-- Verify the prices are back to their original values
SELECT product_id, product_name, price
FROM products
WHERE category = 'Electronics'
LIMIT 5;

-- ============================================================
-- The prices are back to exactly what they were before.
-- ROLLBACK completely undoes everything since BEGIN.
-- This is very powerful — use it whenever you are testing
-- UPDATE or DELETE statements on important data.
-- ============================================================
```

---

### Exercise 6.3 — Savepoints for Batch Processing

```sql
-- ============================================================
-- SAVEPOINTS — Partial Rollback
--
-- Imagine you are processing a batch of 5 new orders.
-- Order 3 has an invalid customer_id.
-- Without savepoints: one bad order rolls back ALL 5.
-- With savepoints: only order 3 fails — the rest succeed.
-- ============================================================

BEGIN;

-- Order 1: Valid — will succeed
SAVEPOINT before_order_1;
INSERT INTO orders (customer_id, order_date, order_status,
                    total_amount, channel)
VALUES (1, CURRENT_DATE, 'PENDING', 150.00, 'WEB');
-- Success — keep going

-- Order 2: Valid — will succeed
SAVEPOINT before_order_2;
INSERT INTO orders (customer_id, order_date, order_status,
                    total_amount, channel)
VALUES (2, CURRENT_DATE, 'PENDING', 320.00, 'MOBILE');
-- Success — keep going

-- Order 3: INVALID customer_id — will fail
SAVEPOINT before_order_3;

-- We simulate an error check here
-- In a real system this would be a FK violation
-- Let us manually detect and handle it

DO $$
DECLARE
    v_customer_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM customers WHERE customer_id = 99999999
    ) INTO v_customer_exists;

    IF NOT v_customer_exists THEN
        RAISE EXCEPTION 'Customer 99999999 does not exist';
    END IF;
END $$;

-- If the above raises an exception, we rollback ONLY to
-- before_order_3 — saving orders 1 and 2

ROLLBACK TO SAVEPOINT before_order_3;
-- Order 3 is rolled back. Orders 1 and 2 are still intact.

-- Order 4: Valid — continues normally
SAVEPOINT before_order_4;
INSERT INTO orders (customer_id, order_date, order_status,
                    total_amount, channel)
VALUES (3, CURRENT_DATE, 'PENDING', 89.00, 'IN_STORE');

-- Order 5: Valid — continues normally
SAVEPOINT before_order_5;
INSERT INTO orders (customer_id, order_date, order_status,
                    total_amount, channel)
VALUES (4, CURRENT_DATE, 'PENDING', 445.00, 'WEB');

COMMIT;
-- Orders 1, 2, 4, and 5 are committed.
-- Order 3 was rolled back.
-- The batch completed with one failure logged for review.

-- ============================================================
-- This is the production pattern for batch processing:
-- Each record gets its own savepoint.
-- Failures are isolated.
-- Successes are preserved.
-- Failed records go to an error log for manual review.
-- ============================================================
```

---

## PART 7 — Reading EXPLAIN ANALYZE Like a Professional

*This section brings everything together.*
*By the end of this section you will be able to look at any*
*EXPLAIN ANALYZE output and know exactly what to do.*

---

### Exercise 7.1 — A Complex Query Before Optimisation

```sql
-- ============================================================
-- Let us run a realistic business query without any
-- optimisation and read the EXPLAIN ANALYZE output carefully.
--
-- Business question:
-- "Find the top 10 customers by total spending in the
--  last 90 days, showing their city and membership level."
-- ============================================================

-- First — drop all custom indexes so we start fresh
DROP INDEX IF EXISTS idx_customers_city;
DROP INDEX IF EXISTS idx_customers_membership_city;
DROP INDEX IF EXISTS idx_orders_status_full;
DROP INDEX IF EXISTS idx_orders_status_partial;
DROP INDEX IF EXISTS idx_orders_customer_covering;

-- Now run the query with EXPLAIN ANALYZE
EXPLAIN ANALYZE
SELECT
    c.customer_id,
    c.full_name,
    c.city,
    c.membership,
    COUNT(o.order_id)        AS order_count,
    SUM(o.total_amount)      AS total_spending
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= CURRENT_DATE - INTERVAL '90 days'
  AND o.order_status = 'DELIVERED'
GROUP BY c.customer_id, c.full_name, c.city, c.membership
ORDER BY total_spending DESC
LIMIT 10;

-- ============================================================
-- READ THE OUTPUT:
--
-- Look for "Seq Scan" — this means full table reads
-- Look at "actual time" for each node
-- Look at "Rows Removed by Filter" — wasted work
-- Note the total "Execution Time" at the bottom
-- Write down this execution time — we will compare it next
-- ============================================================
```

---

### Exercise 7.2 — The Same Query After Optimisation

```sql
-- ============================================================
-- Now let us add the right indexes and run the same query.
-- ============================================================

-- Index 1: Support the order_date filter and order_status filter
CREATE INDEX idx_orders_date_status
ON orders (order_date DESC, order_status)
WHERE order_status = 'DELIVERED';

-- Index 2: Support the JOIN from orders to customers
CREATE INDEX idx_orders_customer_id
ON orders (customer_id);

-- Update statistics after index creation
ANALYZE orders;

-- Run the SAME query again
EXPLAIN ANALYZE
SELECT
    c.customer_id,
    c.full_name,
    c.city,
    c.membership,
    COUNT(o.order_id)        AS order_count,
    SUM(o.total_amount)      AS total_spending
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= CURRENT_DATE - INTERVAL '90 days'
  AND o.order_status = 'DELIVERED'
GROUP BY c.customer_id, c.full_name, c.city, c.membership
ORDER BY total_spending DESC
LIMIT 10;

-- ============================================================
-- COMPARE THE OUTPUT:
--
-- Before: Seq Scan on orders  → After: Index Scan
-- Before: high Execution Time → After: lower Execution Time
-- Before: "Rows Removed by Filter" is high
--         → After: much lower or zero
--
-- The query result is IDENTICAL.
-- The performance is dramatically better.
-- This is the entire point of query optimisation.
-- ============================================================
```

---

### Exercise 7.3 — EXPLAIN ANALYZE Cheat Sheet

```sql
-- ============================================================
-- QUICK REFERENCE: What Each Line Means
-- ============================================================

-- Run this query and use the cheat sheet below to read it
EXPLAIN ANALYZE
SELECT c.city, COUNT(*) AS customer_count
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_status = 'PENDING'
GROUP BY c.city
ORDER BY customer_count DESC;


-- CHEAT SHEET:
--
-- NODE TYPES (what strategy PostgreSQL chose):
-- ┌─────────────────────┬────────────────────────────────────┐
-- │ Seq Scan            │ Reading every row — no index used  │
-- │ Index Scan          │ Using an index, fetching from table│
-- │ Index Only Scan     │ Using covering index — table skip  │
-- │ Bitmap Heap Scan    │ Using index for many matching rows │
-- │ Hash Join           │ Joining large tables efficiently   │
-- │ Nested Loop         │ Joining small result sets          │
-- │ Merge Join          │ Joining pre-sorted data            │
-- └─────────────────────┴────────────────────────────────────┘
--
-- NUMBERS TO READ:
-- ┌──────────────────────────┬─────────────────────────────┐
-- │ cost=0.00..98234.50      │ Estimated work (relative)   │
-- │ rows=6                   │ Estimated rows returned      │
-- │ actual time=0.04..4823   │ Real milliseconds: start..end│
-- │ rows=2000 loops=1        │ Actual rows, actual repeats  │
-- │ Rows Removed by Filter   │ Wasted work — add an index   │
-- │ Execution Time           │ Total real time — the truth  │
-- └──────────────────────────┴─────────────────────────────┘
--
-- WHAT TO DO WITH IT:
-- Seq Scan on large table  → Add an index
-- Large "Rows Removed"     → Your WHERE clause needs an index
-- High actual time         → Look at the most expensive node
-- Estimated ≠ Actual rows  → Run ANALYZE table_name
```

---

## PART 8 — Challenge Section

*Well done for making it this far. You have covered a great deal*
*of material and you should feel proud of your progress.*
*
*The following five challenges are for you to attempt on your own.*
*There are no solutions provided here — this is intentional.*
*The goal is to apply what you have learned and develop your*
*own diagnostic reasoning.*
*
*Please take your time. Discuss with your colleagues.*
*There is more than one correct answer for most of these.*

---

### Challenge 1 — Find the Right Index

```sql
-- ============================================================
-- CHALLENGE 1
--
-- The operations team runs this query every morning:
--
-- "Show all orders from the last 7 days that are still
--  PENDING or PROCESSING, sorted by order date."
--
-- Step 1: Run this query with EXPLAIN ANALYZE
--         and note the execution plan.
--
-- Step 2: Design and create an index that makes this
--         query as fast as possible.
--
-- Step 3: Run the query again with EXPLAIN ANALYZE
--         and confirm the improvement.
--
-- Hint: Think about what columns are in the WHERE clause
--       and whether a partial index would help here.
-- ============================================================

EXPLAIN ANALYZE
SELECT order_id, customer_id, order_date,
       order_status, total_amount, channel
FROM orders
WHERE order_status IN ('PENDING', 'PROCESSING')
  AND order_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY order_date DESC;
```

---

### Challenge 2 — Rewrite the Query

```sql
-- ============================================================
-- CHALLENGE 2
--
-- This query works but is written inefficiently.
-- Identify what is wrong and rewrite it better.
--
-- The query finds customers who have a FAILED payment
-- on any of their orders.
-- ============================================================

-- Current version — can you spot the problem?
SELECT *
FROM customers
WHERE customer_id IN (
    SELECT customer_id
    FROM orders
    WHERE order_id IN (
        SELECT order_id
        FROM payments
        WHERE payment_status = 'FAILED'
    )
);

-- Your task:
-- 1. Identify why this is inefficient
-- 2. Rewrite it using EXISTS
-- 3. Run EXPLAIN ANALYZE on both versions
-- 4. Compare the execution plans and times
```

---

### Challenge 3 — Window Function Practice

```sql
-- ============================================================
-- CHALLENGE 3
--
-- Write a query that shows, for each order:
-- - The order details
-- - The customer's running total spending up to that order
-- - The customer's order number (1st order, 2nd order, etc.)
-- - The customer's largest single order amount so far
--
-- Filter to show only customers from Riyadh.
-- Order the results by customer_id then order_date.
--
-- Hint: You will need three different window functions.
-- SUM() OVER, ROW_NUMBER() OVER, and MAX() OVER
-- ============================================================
```

---

### Challenge 4 — Transaction Practice

```sql
-- ============================================================
-- CHALLENGE 4
--
-- Write a transaction that does the following atomically:
--
-- 1. A customer (use customer_id = 10) places a new order
--    for SAR 750, via MOBILE
--
-- 2. The order starts as PENDING
--
-- 3. A payment of SAR 750 is recorded as COMPLETED
--    using STC_PAY
--
-- 4. If the customer does not exist, the entire transaction
--    must be rolled back
--
-- 5. Use RETURNING to confirm what was inserted
--
-- Make sure all three inserts are inside one transaction.
-- Test it with a valid customer_id and then with an
-- invalid customer_id (e.g. 99999) to see the difference.
-- ============================================================
```

---

### Challenge 5 — Design Your Own Index

```sql
-- ============================================================
-- CHALLENGE 5
--
-- The analytics team runs this report every Monday morning.
-- It currently takes too long to run.
--
-- Your task:
-- 1. Run it with EXPLAIN ANALYZE and read the plan
-- 2. Identify the most expensive step
-- 3. Design ONE index that makes the biggest difference
-- 4. Create the index and run EXPLAIN ANALYZE again
-- 5. Explain in one sentence WHY your index helps this query
-- ============================================================

EXPLAIN ANALYZE
SELECT
    p.category,
    c.city,
    DATE_TRUNC('month', o.order_date) AS order_month,
    COUNT(DISTINCT o.order_id)        AS order_count,
    SUM(oi.line_total)                AS revenue
FROM order_items oi
JOIN orders o       ON oi.order_id   = o.order_id
JOIN products p     ON oi.product_id = p.product_id
JOIN customers c    ON o.customer_id = c.customer_id
WHERE o.order_date >= CURRENT_DATE - INTERVAL '6 months'
  AND o.order_status = 'DELIVERED'
GROUP BY p.category, c.city, DATE_TRUNC('month', o.order_date)
ORDER BY order_month DESC, revenue DESC;
```

---

## Summary — What You Have Practiced Today

| Concept | What You Learned |
|---|---|
| Sequential Scan | Database reads every row — slow on large tables |
| Index Scan | Database jumps to matching rows — fast |
| Single Column Index | Helps queries filtering on one column |
| Composite Index | Helps queries filtering on multiple columns |
| Partial Index | Indexes only the rows you actually need |
| Covering Index | All query columns inside the index — no table visit |
| SELECT * | Always specify columns — never use star in production |
| EXISTS vs IN | EXISTS stops at first match — faster on large data |
| Window Functions | One pass through data — no self-join needed |
| BEGIN / COMMIT | All operations succeed together or none do |
| ROLLBACK | Undo all changes since BEGIN |
| SAVEPOINTS | Undo part of a transaction — keep the rest |
| EXPLAIN ANALYZE | Your tool for understanding and improving performance |

---

> **Thank you for completing this practice lab.**
>
> Every concept you have practised here directly applies to
> the work you do every day. Query optimisation is not just
> a technical skill — it is a way of respecting the systems
> and the people who depend on them.
>
> A query that runs in 1 second instead of 1 minute is not
> just faster. It means a compliance officer gets their
> report on time. It means a dashboard loads before a
> meeting starts. It means a settlement batch completes
> before the trading day begins.
>
> You have done excellent work. Keep practising and do not
> hesitate to revisit any section that was unclear.
>
> We look forward to seeing you apply these skills in the
> sessions ahead.

---

*SNB Data Management Capability Programme*
*Delivered by Fitch Learning*