# Row Level Security (RLS) in PostgreSQL

## What is RLS?

RLS lets you control **which rows a user can see or modify** in a table, based on policies you define. It's like adding an invisible `WHERE` clause to every query — automatically.

> 💡 **Analogy:** Think of it like a **security checkpoint at a government ministry**. Every employee enters the same building (the table), but their access badge (role or session) determines which offices and files (rows) they are permitted to see. The checkpoint enforces this automatically — no one needs to remember to ask.

---

## Enable RLS on a Table

```sql
-- First, enable RLS on the table
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;

-- By default, once enabled, NO rows are visible (deny all)
-- You must create policies to grant access
```

---

## Create Policies

### 1. Simple SELECT Policy (User-Level Isolation)

```sql
-- Bank staff can only see accounts they are assigned to manage
CREATE POLICY staff_accounts_policy
ON accounts
FOR SELECT
USING (relationship_manager_id = current_user_id());
```

### 2. Using `current_setting()` (Session-Level Context)

```sql
-- Staff can only see customers from their branch
CREATE POLICY branch_data_policy
ON customers
FOR SELECT
USING (branch_code = current_setting('app.current_branch'));
```

### 3. Multi-operation Policy

```sql
-- Loan officers can only view, create, and update their own loan applications
CREATE POLICY loan_officer_policy
ON loan_applications
FOR ALL
USING (officer_id = current_user)
WITH CHECK (officer_id = current_user);
```

| Clause | Purpose |
|---|---|
| `USING` | Filters rows on **read** — controls what the user can see |
| `WITH CHECK` | Validates rows on **write** — controls what the user can insert or update |

---

## Real-World Pattern: Multi-Branch Banking (SAMA Context)

A bank operating across multiple regions must ensure that **branch staff only access their own branch data** — a core requirement under SAMA data governance guidelines.

```sql
-- 1. Add branch_id to your table
ALTER TABLE transactions ADD COLUMN branch_id UUID;

-- 2. Enable RLS
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- 3. Set branch context per session (set by your application after login)
SET app.branch_id = 'a3f8c210-4d92-11ee-be56-0242ac120002';

-- 4. Create policy using session variable
CREATE POLICY branch_isolation
ON transactions
FOR ALL
USING (branch_id = current_setting('app.branch_id')::UUID)
WITH CHECK (branch_id = current_setting('app.branch_id')::UUID);
```

> ✅ Your application sets `app.branch_id` immediately after the user logs in. From that point forward, PostgreSQL enforces branch-level isolation on every query — automatically, with no additional application logic required.

---

## PDPL Alignment

Under **Saudi Arabia's Personal Data Protection Law (PDPL)**, organisations must ensure that personal data is accessed only by authorised personnel. RLS provides a **technical enforcement layer** that directly supports this obligation.

| PDPL Requirement | RLS Mechanism |
|---|---|
| Access limited to authorised users | `USING` policy tied to session role |
| Data minimisation | Users see only rows they own or are assigned |
| Auditability | Policies are stored in `pg_policies` and can be audited |
| Separation of duties | Different policies per role (teller, manager, auditor) |

---

## Bypass RLS (Superuser / Table Owner)

```sql
-- Table owners bypass RLS by default
-- To force RLS even on owners (recommended for compliance):
ALTER TABLE transactions FORCE ROW LEVEL SECURITY;

-- Superusers always bypass RLS
-- Grant bypass only to designated DBA roles:
ALTER ROLE dba_admin BYPASSRLS;
```

> ⚠️ In regulated environments like banking, apply `FORCE ROW LEVEL SECURITY` on all sensitive tables and restrict `BYPASSRLS` to a minimum number of authorised DBA accounts.

---

## Useful Commands

```sql
-- View all policies on a table
SELECT * FROM pg_policies WHERE tablename = 'transactions';

-- Drop a policy
DROP POLICY branch_isolation ON transactions;

-- Disable RLS (all rows become visible again — use with caution)
ALTER TABLE transactions DISABLE ROW LEVEL SECURITY;
```

---

## Key Gotchas

| Gotcha | Detail |
|---|---|
| **Table owner bypasses RLS** | Use `FORCE ROW LEVEL SECURITY` to override |
| **Superusers always bypass** | Restrict `BYPASSRLS` to named DBA roles only |
| **No policy = no rows** | Once RLS is enabled, you must define at least one policy |
| **Performance** | Always index the column used in `USING` (e.g., `branch_id`) |
| **`current_setting()` must be set** | If missing, PostgreSQL throws an error — use the safe default below |

---

## Safe Default Pattern

```sql
-- Returns NULL instead of throwing an error if the setting is not found
USING (branch_id = current_setting('app.branch_id', true)::UUID)
```

> The second argument `true` in `current_setting()` instructs PostgreSQL to return `NULL` gracefully instead of raising an exception when the session variable has not been set.

---

## Role-Based Policy Example (Teller vs. Manager)

```sql
-- Tellers can only read their own transactions
CREATE POLICY teller_read_policy
ON transactions
FOR SELECT
TO teller_role
USING (created_by = current_user);

-- Branch managers can read all transactions in their branch
CREATE POLICY manager_read_policy
ON transactions
FOR SELECT
TO manager_role
USING (branch_id = current_setting('app.branch_id')::UUID);
```

> Multiple policies on the same table are combined with **OR logic** — a row is visible if *any* applicable policy permits it.

---

## References

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [CREATE POLICY](https://www.postgresql.org/docs/current/sql-createpolicy.html)
- [ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)
- [SAMA Data Management Guidelines](https://www.sama.gov.sa)
- [Saudi PDPL — National Data Management Office](https://ndmo.gov.sa)