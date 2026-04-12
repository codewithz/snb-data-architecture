# The Retail Mini-Project — Instructor Guide
## How to Approach the Problem, Where to Start, and How to Think Through Each Layer
### Al-Noor Bank | Digital Retail Banking Platform

---

> **A note before you begin.**
>
> This guide is written to you directly — as a participant
> sitting in front of this problem for the first time.
>
> Architecture problems can feel overwhelming when you first
> look at them. Five domains. Six external integrations.
> Regulatory obligations layered on top of every design decision.
> It is easy to stare at the blank page and not know where to start.
>
> This guide solves that. It tells you exactly how to approach
> the problem, in what order, and why that order matters.
> It then walks you through one complete domain — Payments —
> from the first question you should ask all the way through
> to the final DDL. Every decision is explained. Every
> alternative is acknowledged.
>
> Once you have seen it done once, the other four domains
> follow the same process. The method is the transferable skill.
>
> Read this guide before you open any tool or draw any diagram.

---

## Part 1 — How to Approach an Architecture Problem

---

### The Mistake Almost Everyone Makes

The most common mistake when faced with a multi-domain
architecture problem is to start drawing.

Someone opens a diagramming tool, creates a box labelled
CUSTOMER, adds a box labelled ACCOUNT, draws a line between
them, and then starts wondering where PAYMENT goes.

Within ten minutes they have a diagram with fifteen boxes,
no clear boundaries, arrows going in every direction, and
no way to explain why anything is where it is.

This is not architecture. This is decoration.

**Architecture starts with questions, not boxes.**

---

### The Right Starting Order

Every domain, in every architecture project, should be
approached in this order. No exceptions.

```
STEP 1 — Understand the domain's purpose
          Before drawing anything, answer in one sentence:
          What problem does this domain exist to solve?

STEP 2 — Identify the business questions it must answer
          What does the business need to ask of this domain
          every day? These questions become your queries.
          Your queries tell you what data you need.
          Your data tells you what entities to create.

STEP 3 — Find the entities
          What are the real-world things this domain
          needs to remember? Not tables — things.
          A customer. A payment. A contract. A branch.

STEP 4 — Establish the relationships
          How do these things relate to each other?
          One customer makes many payments.
          Each payment uses one payment rail.
          Draw the relationships before worrying about columns.

STEP 5 — Draw the conceptual model
          Now open the diagramming tool.
          Boxes and lines only. No columns yet.
          This is the conversation tool — it must be readable
          by a business stakeholder, not just a developer.

STEP 6 — Add the attributes (logical model)
          Now decide what you need to know about each entity.
          Column names. Data types. Constraints.
          PDPL classification for each attribute.
          Source system for each attribute.

STEP 7 — Write the physical DDL
          Now translate the logical model into real SQL.
          Add indexes. Add partitioning where required.
          Add CHECK constraints that enforce business rules.
          Add foreign keys that enforce referential integrity.

STEP 8 — Validate with a business scenario
          Take a real scenario — a customer makes a payment —
          and trace every table that is read or written,
          in order. If your schema cannot support the scenario,
          the schema is incomplete.
```

This is not a linear process that you complete once.
You will move back and forth between steps — you will
discover a business question in Step 2 that forces you
to add an entity in Step 3, which changes your conceptual
model in Step 5, which adds columns in Step 6.

That is normal. That is architecture.

---

### How to Read the Requirements

Before touching any domain, read the full set of requirements
carefully. Do not skim them. Every requirement contains a
hidden schema decision.

Here is how to read them:

```
FUNCTIONAL REQUIREMENT:
"All payments via SARIE for domestic SAR,
SWIFT for international."

What this tells you about the schema:
→ The payment table needs a payment_rail column
→ SARIE and SWIFT are not interchangeable — they are
  different columns in the schema (sarie_uetr, swift_uetr)
→ A generic "reference_no" column cannot serve both
→ The rail determines which reference column is populated

NON-FUNCTIONAL REQUIREMENT:
"Account balance queries in under 100ms."

What this tells you about the schema:
→ The account table needs an index on account_id
→ A balance_after snapshot on the transaction table avoids
  recalculating from transaction history on every query
→ Redis caching may be needed for the hottest accounts
→ This is a schema decision, not just an infrastructure one

NON-FUNCTIONAL REQUIREMENT:
"No PII in development or test environments."

What this tells you about the schema:
→ Every column containing personal data must be identified
→ A synthetic data pipeline must be designed
→ national_id and date_of_birth must be tokenised
  before leaving production
→ This requires knowing which columns are PDPL-classified
  before any data moves to non-production environments
```

The requirement is the input. The schema decision is the output.
If you cannot draw a direct line from a requirement to a
specific schema decision, you have not read the requirement
carefully enough.

---

### How to Handle the Regulatory Layer

SAMA and PDPL are not separate concerns that you address
at the end of the design. They are design constraints that
shape every entity from the start.

**Before designing any entity, ask these four questions:**

```
1. Does this entity contain personal data?
   → If yes, every column needs a PDPL classification.
   → Restricted columns need encryption and restricted access.
   → The source system must be identified.

2. Does this entity need an audit trail?
   → If it changes state (application status, payment status),
     a history table is almost certainly required.
   → The history table must be append-only.
   → SAMA will ask for it at examination time.

3. Does this entity have a retention obligation?
   → Transaction data: 10 years minimum.
   → KYC data: 10 years after account closure.
   → Is there a soft delete pattern needed?
   → Is there a legal_hold flag needed?

4. Does this entity feed a SAMA report?
   → If yes, the reporting view must be traceable
     directly to this entity.
   → The SAMA report is not an afterthought —
     it is a design requirement for the schema.
```

If you answer these four questions before designing each
entity, the SAMA and PDPL obligations are built into the
schema from the start. If you skip them, you will retrofit
compliance into a schema that was not designed for it —
which is expensive, slow, and error-prone.

---

### The Document That Holds Everything Together — The ADR

Every significant design decision must be documented in an
Architecture Decision Record.

An ADR has exactly three parts:

```
DECISION: What did you decide?
          "We use a parent + subtype model for Customer."

ALTERNATIVES CONSIDERED: What else did you consider?
          "We considered a single table with a discriminator
          column (customer_type = 'I' or 'C')."

RATIONALE: Why did you choose what you chose?
          "The single table creates NULL columns for attributes
          that do not apply to each type. Every query must
          filter on customer_type. The subtype model makes
          the wrong state structurally impossible and keeps
          each entity logically clean."
```

You do not write an ADR for every column.
You write one for every decision that, if reversed,
would require significant rework — the database engine
choice, the partitioning strategy, the customer model,
the payment rail approach.

If someone joins the project six months from now and asks
"why did you do it this way?", the ADR is your answer.
Without ADRs, institutional knowledge lives only in the
memories of the people who were in the room.

---

## Part 2 — The Payments Domain, End to End

---

This section walks through the complete design of the
Payments Domain — from the first question you should ask
to the final DDL you would hand to a developer.

Read every section. Do not skip to the DDL.
The DDL without the reasoning is just syntax.
The reasoning is the architecture.

---

### Step 1 — Understand the Domain's Purpose

**The question:** What problem does the Payments Domain
exist to solve?

**The answer:** To record, route, track, and report every
movement of money initiated through the Al-Noor platform —
whether that money is moving between two Al-Noor accounts,
to another Saudi bank via SARIE, to a utility company via
SADAD, or internationally via SWIFT.

**Why this matters:** The domain's purpose determines its
boundaries. The Payments Domain does not own the customer
who initiated the payment — that belongs to the Customer
Domain. It does not own the account the money came from —
that also belongs to the Customer Domain. The Payments
Domain references those things. It does not own them.

Getting the domain boundary right from the start prevents
the most common architecture mistake: a domain that owns
too much and becomes a dependency for everything else.

---

### Step 2 — Identify the Business Questions

Before drawing a single entity, write down the questions
the business will ask of this domain every day.

```
OPERATIONS TEAM:
→ How many payments are currently in PROCESSING status?
→ Which payments failed in the last 24 hours and why?
→ What is the average response time for SARIE submissions
  today compared to yesterday?

COMPLIANCE TEAM:
→ Which payments above SAR 60,000 were processed today?
→ Were all payments compliance-screened before completing?
→ Show me every payment initiated by customer C000000003
  in the last 90 days.

SAMA REPORTING TEAM:
→ What is the total value of domestic SAR transfers
  via SARIE this week?
→ What is the total volume of SADAD bill payments
  by channel this month?
→ How many international SWIFT payments were processed
  this quarter?

CUSTOMER SERVICE:
→ What is the current status of payment PMT-2025-0042?
→ Why was this payment rejected?
→ When will this payment complete?
```

These questions tell you exactly what data you need.
Every question maps to a column or a relationship.

```
"Which payments are in PROCESSING status?"
→ The payment table needs a status column.

"Which payments failed and why?"
→ The payment table needs a status column AND a
  failure_reason or error_code column.

"Were all payments compliance-screened?"
→ The payment table needs boolean flags:
  compliance_screened and sanctions_checked.

"Show payments by customer in the last 90 days."
→ The payment table needs initiator_customer_id
  AND initiated_at — and an index on both.

"Total SARIE value this week."
→ The payment table needs payment_rail AND amount_sar
  AND initiated_at for grouping and filtering.
```

You have not drawn a single box yet, and you already know
most of the columns your payment table will need.
This is the right way to arrive at a schema.

---

### Step 3 — Find the Entities

Now ask: what are the real-world things the Payments Domain
needs to remember?

```
PAYMENT
The payment itself — the record of an instruction
to move money from one place to another.
This is the core entity. Everything else either
describes the payment or is a consequence of it.

PAYMENT_STATUS_HISTORY
Every status transition the payment goes through —
INITIATED → PROCESSING → COMPLETED (or FAILED).
This is the audit trail. SAMA requires it.
It is a separate entity, not a column on payment.

EXTERNAL_API_LOG
Every call to SARIE, SADAD, OFAC, or SWIFT
that was made as part of processing this payment.
This exists at the platform level, not just for payments —
but every payment processing step that touches an external
service must produce a row here.
```

Notice what is NOT in this list:
- CUSTOMER — lives in the Customer Domain
- ACCOUNT — lives in the Customer Domain
- PRODUCT — lives in the Product Domain

The Payments Domain references these entities.
It does not own or replicate them.

---

### Step 4 — Establish the Relationships

```
CUSTOMER ──────────── initiates ──────────► PAYMENT
(Customer Domain)                           (Payments Domain)

ACCOUNT ─────────────── debited by ────────► PAYMENT
(Customer Domain)                            (Payments Domain)

PAYMENT ──────────── has history of ───────► PAYMENT_STATUS_HISTORY
(one to many — one payment, many status rows)

PAYMENT ──────────── triggers calls to ────► EXTERNAL_API_LOG
(one to many — one payment, many API calls)
```

**The cross-domain dependency to note:**

PAYMENT references ACCOUNT (via debit_account_id).
ACCOUNT lives in the Customer Domain.

This means the Payments Domain is a consumer of
Customer Domain data. It must never replicate or
copy account data into its own tables — it holds
a foreign key reference to the authoritative source.

This is the most commonly missed relationship in
this architecture. If you miss it, your diagram will
show PAYMENT and ACCOUNT in the same domain boundary —
which misrepresents who owns what and who is responsible
for the quality of that data.

---

### Step 5 — The Conceptual Model

The conceptual model shows entities and relationships only.
No columns. No data types. No constraints.

Its purpose is communication — a business stakeholder
should be able to read it and confirm that it represents
how the business actually works.

```
CONCEPTUAL MODEL — PAYMENTS DOMAIN

┌─ CUSTOMER DOMAIN ──────────────────────┐
│                                        │
│   ┌────────────┐    ┌─────────────┐    │
│   │  CUSTOMER  │    │   ACCOUNT   │    │
│   └─────┬──────┘    └──────┬──────┘    │
│         │                  │           │
└─────────┼──────────────────┼───────────┘
          │ initiates        │ debited by
          │                  │
          ▼                  ▼
┌─ PAYMENTS DOMAIN ──────────────────────────────────────┐
│                                                        │
│                    ┌─────────────┐                     │
│                    │   PAYMENT   │                     │
│                    │             │                     │
│                    │ one payment │                     │
│                    │ per row     │                     │
│                    └──────┬──────┘                     │
│                           │                            │
│              ┌────────────┴────────────┐               │
│              │                         │               │
│              │ has history             │ triggers      │
│              ▼                         ▼               │
│  ┌───────────────────────┐  ┌──────────────────────┐  │
│  │  PAYMENT_STATUS_      │  │  EXTERNAL_API_LOG    │  │
│  │  HISTORY              │  │                      │  │
│  │                       │  │ (SARIE / OFAC /      │  │
│  │  append-only audit    │  │  SADAD calls)        │  │
│  │  trail — one row per  │  │                      │  │
│  │  status transition    │  │                      │  │
│  └───────────────────────┘  └──────────────────────┘  │
│                                                        │
└────────────────────────────────────────────────────────┘

PAYMENT RAILS (not a separate entity — a column value):
SARIE → domestic SAR interbank
SADAD → bill payments
mada  → card network
SWIFT → international
INTERNAL → within Al-Noor Bank
```

**What to check before moving on:**

```
□ Is every entity in the correct domain boundary?
□ Are cross-domain references shown as references,
  not as entities copied into this domain?
□ Can a business stakeholder read this and confirm
  it matches how payments actually work?
□ Is there an audit trail entity for status changes?
□ Is the external API log represented?
```

If all boxes are checked, the conceptual model is ready.

---

### Step 6 — The Logical Model

The logical model takes every entity from the conceptual
model and adds the detail: attributes, data types,
constraints, PDPL classification, and source system.

This is where the design decisions become concrete.

---

#### Entity 1: PAYMENT

```
PAYMENT
────────────────────────────────────────────────────────────────
Attribute              Type           Constraint    PDPL    Source
────────────────────────────────────────────────────────────────
payment_id             UUID           PK, NOT NULL  Internal Payment System

DECISION: Why UUID and not SERIAL or BIGSERIAL?
Because Open Banking third-party providers (TPPs) generate
payment initiation records on their own systems before
sending them to Al-Noor Bank. The ID must be globally unique
— not just unique within Al-Noor's database.
SERIAL auto-increments within one database.
UUID is unique across every database in the world.
This is the correct key type for a distributed payment system.

payment_ref            VARCHAR(50)    NOT NULL      Internal Payment System
                                      UNIQUE

DECISION: Why a human-readable reference alongside UUID?
Customers, call centre agents, and SAMA examiners reference
payments by a human-readable code (PMT-2025-0042), not a UUID.
The UUID is the system key. The payment_ref is the business key.
Both are needed.

payment_rail           VARCHAR(15)    NOT NULL      Internal Payment System
                                      CHECK(...)

DECISION: Why a CHECK constraint on payment_rail?
Because SARIE, SADAD, mada, SWIFT, INTERNAL, and STCPAY
are the only valid values. Any value outside this set
represents either a data entry error or a system bug.
The CHECK constraint makes invalid values impossible to store.

payment_type           VARCHAR(20)    NOT NULL      Internal Payment System
                                      CHECK(...)

initiator_customer_id  CHAR(10)       NOT NULL      Customer Domain
                                      FK → customer

amount_sar             NUMERIC(18,2)  NOT NULL      Payment System

DECISION: Why NUMERIC and not FLOAT?
FLOAT uses binary approximation. 0.1 + 0.2 = 0.30000000000000004.
Across millions of payment records, floating-point rounding
accumulates into SAR discrepancies that fail SAMA reconciliation.
NUMERIC stores exact decimal values. Always use it for money.

debit_account_id       CHAR(16)       NOT NULL      Customer Domain
                                      FK → account

credit_account_id      CHAR(16)       NULLABLE      Customer Domain
                                      FK → account

DECISION: Why is credit_account_id nullable?
For external payments (SARIE to another bank, SWIFT
internationally), the credit account is not an Al-Noor account.
It does not exist in our system. NULL is the correct value.
The beneficiary_iban column carries the external destination.

beneficiary_name       VARCHAR(200)   NULLABLE      Confidential  Customer input

DECISION: PDPL classification of beneficiary_name?
The payment recipient is a third party who has not consented
to data processing by Al-Noor Bank. Their name is personal data
under PDPL regardless of how it was received. Confidential
classification — access restricted to authorised payment operations.

beneficiary_iban       VARCHAR(34)    NULLABLE      Confidential  Customer input
beneficiary_bank_code  VARCHAR(20)    NULLABLE      Internal      Customer input

foreign_currency       CHAR(3)        NULLABLE      Internal      FX System
foreign_amount         NUMERIC(18,2)  NULLABLE      Internal      FX System
exchange_rate          NUMERIC(10,6)  NULLABLE      Internal      FX System

DECISION: Why three FX columns all nullable?
For SAR-denominated domestic payments, there is no foreign
currency. These columns are NULL. For SWIFT international
payments, all three are populated. Nullable columns are correct
here — not a design flaw. The nullability is intentional and
represents a real business distinction.

status                 VARCHAR(20)    NOT NULL      Internal      Payment System
                                      DEFAULT 'INITIATED'
                                      CHECK(...)

initiated_at           TIMESTAMPTZ    NOT NULL      Internal      Payment System
                                      DEFAULT NOW()
completed_at           TIMESTAMPTZ    NULLABLE      Internal      Payment System

sarie_uetr             VARCHAR(50)    NULLABLE      Internal      SARIE
swift_uetr             VARCHAR(50)    NULLABLE      Internal      SWIFT

DECISION: Why two separate UETR columns?
A SARIE UETR and a SWIFT UETR are generated by different systems,
for different regulatory purposes, in different formats.
One generic reference_no column cannot distinguish them.
When a SAMA examiner asks for the SARIE UETR for a specific
payment, you need a dedicated column — not a free-text field
that might contain either type of reference.
sarie_uetr is populated for SARIE payments; swift_uetr for SWIFT.
Both are NULL for all other payment rails.

compliance_screened    BOOLEAN        NOT NULL      Internal      AML System
                                      DEFAULT FALSE
sanctions_checked      BOOLEAN        NOT NULL      Internal      OFAC Feed
                                      DEFAULT FALSE

DECISION: Why two boolean flags instead of one status column?
Because AML screening and sanctions screening are two independent
checks run by two different systems. A payment may pass one and
fail the other. A single "compliance_status" column cannot
represent the combination of states. Two booleans can.
Both must be TRUE before status can be set to COMPLETED.
This is enforced in the application layer and verified
by a data quality check on the schema.
────────────────────────────────────────────────────────────────
```

---

#### Entity 2: PAYMENT_STATUS_HISTORY

```
PAYMENT_STATUS_HISTORY
────────────────────────────────────────────────────────────────
Attribute         Type          Constraint      PDPL      Source
────────────────────────────────────────────────────────────────
history_id        BIGSERIAL     PK, NOT NULL    Internal  Payment System
payment_id        UUID          NOT NULL        Internal  Payment System
                                FK → payment
old_status        VARCHAR(20)   NULLABLE        Internal  Payment System

DECISION: Why is old_status nullable?
The first row in this table for any payment records
the transition from nothing to INITIATED. There is
no previous status. NULL correctly represents "this
is the first state this payment has ever been in."

new_status        VARCHAR(20)   NOT NULL        Internal  Payment System
changed_at        TIMESTAMPTZ   NOT NULL        Internal  Payment System
                                DEFAULT NOW()
changed_by        VARCHAR(100)  NOT NULL        Internal  Payment System

DECISION: What goes in changed_by?
Either a staff user ID (for manually processed payments)
or a system name such as 'PAYMENT_ENGINE_v2' or 'AML_SYSTEM'
for automated transitions. Both must be captured.
An audit trail that only shows "the system did it" without
identifying which system is not a useful audit trail.

change_reason     VARCHAR(255)  NULLABLE        Internal  Payment System

DECISION: Why nullable?
Routine status transitions (INITIATED → PROCESSING) do not
require a reason. Rejection transitions must have a reason.
The application layer enforces the reason for rejections.
The schema allows NULL to avoid forcing meaningless reasons
on automated routine transitions.

IMPORTANT: No UPDATE or DELETE is ever permitted on this table.
Every row is written once and never changed.
An immutable trigger should enforce this at the database level.
────────────────────────────────────────────────────────────────
```

---

#### Entity 3: EXTERNAL_API_LOG

```
EXTERNAL_API_LOG (platform-level — not payments-only)
────────────────────────────────────────────────────────────────
Attribute           Type          Constraint    PDPL      Source
────────────────────────────────────────────────────────────────
log_id              BIGSERIAL     PK, NOT NULL  Internal  Platform
service_name        VARCHAR(50)   NOT NULL      Internal  Platform
endpoint            VARCHAR(200)  NOT NULL      Internal  Platform
http_method         VARCHAR(10)   NOT NULL      Internal  Platform
request_ref         VARCHAR(100)  NULLABLE      Internal  Platform

DECISION: What goes in request_ref?
The internal business reference — the payment_id or
application_id that caused this API call. This is the
thread that connects the log entry to the business event.
Without it, the log is a disconnected list of API calls
with no way to trace them back to what caused them.

customer_id         CHAR(10)      NULLABLE      Internal  Customer Domain

DECISION: Why customer_id and not national_id?
The log stores a reference to the customer —
not the customer's personal data. The national_id
stays in the secured KYC system with restricted access.
This table is an internal audit log. The PDPL principle
of data minimisation applies: store only what is needed.
The customer_id reference is sufficient to trace the call.
Raw PII in this table would make it a restricted data store
requiring the same controls as the KYC system. That is not
the purpose of an operational audit log.

request_timestamp   TIMESTAMPTZ   NOT NULL      Internal  Platform
response_timestamp  TIMESTAMPTZ   NULLABLE      Internal  Platform
http_status_code    SMALLINT      NULLABLE      Internal  Platform
response_status     VARCHAR(20)   NULLABLE      Internal  Platform

DECISION: Why is response_status separate from http_status_code?
An HTTP 200 response from SARIE can still mean the payment
was rejected by SARIE's business rules. The HTTP status tells
you the technical result. The response_status tells you the
business result: SUCCESS, FAILED, TIMEOUT.
Both are needed. They are not redundant.

error_code          VARCHAR(50)   NULLABLE      Internal  External System
error_message       VARCHAR(500)  NULLABLE      Internal  External System

DECISION: Do error messages ever contain PII?
They must not. Error messages from Nafath or SIMAH may
include identifying information if not carefully handled.
The application layer must strip PII from error messages
before writing to this table. The schema cannot enforce
this — it must be enforced in the integration layer.

response_time_ms    INTEGER       NULLABLE      Internal  Platform

DECISION: Why is this column so important?
SLA monitoring. If SARIE is averaging 6,000ms response time
against a 2,000ms SLA, the operations team needs data —
not anecdote. This column provides that data. Dashboards
built on this column answer the question "are our external
integrations performing within SLA?" with evidence, not feeling.
────────────────────────────────────────────────────────────────
```

---

### Step 7 — The Physical DDL

The physical DDL translates the logical model into real
PostgreSQL. Every decision made in the logical model becomes
a concrete implementation choice here.

Read every comment. The comments explain the connection
between the logical decision and the physical implementation.

---

#### Schema Setup

```sql
-- ============================================================
-- The Payments Domain lives in its own schema.
-- This enforces access control at the database layer.
-- Operations staff can be granted access to the payments
-- schema without being granted access to compliance or retail.
-- Schema separation is data protection by design.
-- ============================================================

CREATE SCHEMA payments;
SET search_path TO payments, retail, compliance;
```

---

#### The PAYMENT Table

```sql
-- ============================================================
-- PAYMENT TABLE
-- Core entity of the Payments Domain.
-- One row per payment instruction.
--
-- UUID primary key — globally unique across all systems.
-- Required because Open Banking TPPs generate payment
-- initiation records externally before sending to Al-Noor.
--
-- NUMERIC(18,2) for all monetary values — never FLOAT.
-- Exact decimal arithmetic. No rounding errors.
-- SAR 3,750.00 stored as exactly SAR 3,750.00 always.
-- ============================================================

CREATE TABLE payments.payment (
    payment_id             UUID          NOT NULL
                                         DEFAULT gen_random_uuid(),
    payment_ref            VARCHAR(50)   NOT NULL,
    payment_rail           VARCHAR(15)   NOT NULL
        CHECK (payment_rail IN (
            'SARIE', 'SADAD', 'MADA',
            'SWIFT', 'INTERNAL', 'STCPAY', 'APPLEPAY'
        )),
    payment_type           VARCHAR(20)   NOT NULL
        CHECK (payment_type IN (
            'TRANSFER', 'BILL_PAYMENT', 'SALARY',
            'INTERNATIONAL', 'CARD_PAYMENT', 'REFUND'
        )),

    -- Cross-domain references — payment does not own these
    -- entities; it references them via foreign keys
    initiator_customer_id  CHAR(10)      NOT NULL,
    debit_account_id       CHAR(16)      NOT NULL,
    credit_account_id      CHAR(16),     -- NULL for external payments

    -- Beneficiary — third-party personal data under PDPL
    beneficiary_iban       VARCHAR(34),
    beneficiary_name       VARCHAR(200),  -- PDPL: Confidential
    beneficiary_bank_code  VARCHAR(20),

    -- Monetary values — always NUMERIC, never FLOAT
    amount_sar             NUMERIC(18,2) NOT NULL
        CHECK (amount_sar > 0),
    foreign_currency       CHAR(3),      -- NULL for SAR payments
    foreign_amount         NUMERIC(18,2),
    exchange_rate          NUMERIC(10,6),

    -- Status lifecycle
    status                 VARCHAR(20)   NOT NULL
        DEFAULT 'INITIATED'
        CHECK (status IN (
            'INITIATED', 'PENDING', 'PROCESSING',
            'COMPLETED', 'FAILED', 'REJECTED', 'CANCELLED'
        )),

    -- Timestamps
    initiated_at           TIMESTAMPTZ   NOT NULL
                                         DEFAULT CURRENT_TIMESTAMP,
    completed_at           TIMESTAMPTZ,

    -- Rail-specific reference numbers
    -- Only the column matching the payment_rail is populated.
    -- All others are NULL.
    sarie_uetr             VARCHAR(50),   -- SARIE payments only
    swift_uetr             VARCHAR(50),   -- SWIFT payments only

    -- Compliance gates — both must be TRUE before COMPLETED
    compliance_screened    BOOLEAN       NOT NULL DEFAULT FALSE,
    sanctions_checked      BOOLEAN       NOT NULL DEFAULT FALSE,

    -- Primary key
    CONSTRAINT pk_payment
        PRIMARY KEY (payment_id),

    -- Business key — human-readable, unique
    CONSTRAINT uq_payment_ref
        UNIQUE (payment_ref),

    -- Cross-domain foreign keys
    CONSTRAINT fk_pmt_customer
        FOREIGN KEY (initiator_customer_id)
        REFERENCES retail.customer(customer_id),

    CONSTRAINT fk_pmt_debit_account
        FOREIGN KEY (debit_account_id)
        REFERENCES retail.account(account_id),

    CONSTRAINT fk_pmt_credit_account
        FOREIGN KEY (credit_account_id)
        REFERENCES retail.account(account_id)
);
```

```sql
-- ============================================================
-- INDEXES ON PAYMENT
--
-- Index 1: payment_rail + status + initiated_at
-- Serves: "All failed SARIE payments from yesterday"
-- Operations team runs this every morning.
--
-- Index 2: initiator_customer_id + initiated_at
-- Serves: Customer 360 view — all payments for a customer
-- in the last 90 days. Customer service runs this constantly.
--
-- Index 3: status + initiated_at (partial — non-completed only)
-- Serves: "All payments currently in PROCESSING or PENDING"
-- Operations dashboard. Excludes COMPLETED (the vast majority).
-- Partial index is far smaller than a full status index.
-- ============================================================

CREATE INDEX idx_payment_rail_status
    ON payments.payment (payment_rail, status, initiated_at DESC);

CREATE INDEX idx_payment_customer
    ON payments.payment (initiator_customer_id, initiated_at DESC);

CREATE INDEX idx_payment_active
    ON payments.payment (status, initiated_at DESC)
    WHERE status NOT IN ('COMPLETED', 'CANCELLED');
```

---

#### The PAYMENT_STATUS_HISTORY Table

```sql
-- ============================================================
-- PAYMENT_STATUS_HISTORY TABLE
-- Append-only audit trail. Every status transition recorded.
-- No row is ever updated. No row is ever deleted.
--
-- BIGSERIAL for history_id — high write volume expected.
-- Every payment generates multiple history rows.
-- Integer keys are smaller and faster than UUID here
-- because this table is never exposed externally.
-- ============================================================

CREATE TABLE payments.payment_status_history (
    history_id     BIGSERIAL     NOT NULL,
    payment_id     UUID          NOT NULL,
    old_status     VARCHAR(20),            -- NULL for first transition
    new_status     VARCHAR(20)   NOT NULL,
    changed_at     TIMESTAMPTZ   NOT NULL
                                 DEFAULT CURRENT_TIMESTAMP,
    changed_by     VARCHAR(100)  NOT NULL, -- User ID or system name
    change_reason  VARCHAR(255),           -- Required for rejections

    CONSTRAINT pk_payment_history
        PRIMARY KEY (history_id),

    CONSTRAINT fk_history_payment
        FOREIGN KEY (payment_id)
        REFERENCES payments.payment(payment_id)
);

CREATE INDEX idx_pmt_history_payment
    ON payments.payment_status_history (payment_id, changed_at DESC);
```

```sql
-- ============================================================
-- IMMUTABILITY TRIGGER
-- Prevents any UPDATE or DELETE on this table.
-- The audit trail must be tamper-proof.
-- A SAMA examiner must be able to trust that what they see
-- is what actually happened — not a retrospectively edited version.
-- ============================================================

CREATE OR REPLACE FUNCTION payments.prevent_history_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'payment_status_history is immutable — rows cannot be % d',
        TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payment_history_immutable
    BEFORE UPDATE OR DELETE
    ON payments.payment_status_history
    FOR EACH ROW
    EXECUTE FUNCTION payments.prevent_history_modification();
```

---

#### The EXTERNAL_API_LOG Table

```sql
-- ============================================================
-- EXTERNAL_API_LOG TABLE
-- Platform-level — not payments-only.
-- Records every call to every external service.
-- Nafath, SIMAH, SARIE, SADAD, OFAC, ZATCA — all logged here.
--
-- BIGSERIAL — very high write volume. Every payment and
-- every application triggers multiple external calls.
-- Fast integer PK is the right choice here.
--
-- No raw PII stored in this table.
-- customer_id is a reference, not personal data.
-- Error messages must be stripped of PII by the application
-- before writing to this table.
-- ============================================================

CREATE TABLE payments.external_api_log (
    log_id              BIGSERIAL     NOT NULL,
    service_name        VARCHAR(50)   NOT NULL
        CHECK (service_name IN (
            'NAFATH', 'SIMAH', 'SARIE',
            'SADAD', 'OFAC', 'ZATCA', 'SWIFT_GPI'
        )),
    endpoint            VARCHAR(200)  NOT NULL,
    http_method         VARCHAR(10)   NOT NULL
        CHECK (http_method IN ('GET', 'POST', 'PUT', 'PATCH')),
    request_ref         VARCHAR(100),  -- payment_id or application_id
    customer_id         CHAR(10),      -- reference only, not PII store
    request_timestamp   TIMESTAMPTZ   NOT NULL
                                       DEFAULT CURRENT_TIMESTAMP,
    response_timestamp  TIMESTAMPTZ,
    http_status_code    SMALLINT,
    response_status     VARCHAR(20)
        CHECK (response_status IN (
            'SUCCESS', 'FAILED', 'TIMEOUT', 'PENDING'
        )),
    error_code          VARCHAR(50),
    error_message       VARCHAR(500),  -- must be PII-free
    response_time_ms    INTEGER,

    CONSTRAINT pk_api_log
        PRIMARY KEY (log_id)
);

CREATE INDEX idx_api_log_service_time
    ON payments.external_api_log
    (service_name, request_timestamp DESC);

CREATE INDEX idx_api_log_request_ref
    ON payments.external_api_log
    (request_ref, request_timestamp DESC);
```

---

#### The Reporting View

```sql
-- ============================================================
-- SAMA DAILY PAYMENT VOLUME VIEW
-- Feeds the SAMA daily transaction report.
-- Aggregated by rail and payment type — no PII.
-- Refresh nightly as a materialised view at production scale.
-- ============================================================

CREATE OR REPLACE VIEW payments.v_daily_payment_summary AS
SELECT
    DATE(p.initiated_at)   AS payment_date,
    p.payment_rail,
    p.payment_type,
    p.status,
    COUNT(*)               AS payment_count,
    SUM(p.amount_sar)      AS total_amount_sar,
    AVG(p.amount_sar)      AS avg_amount_sar,
    MIN(p.amount_sar)      AS min_amount_sar,
    MAX(p.amount_sar)      AS max_amount_sar
FROM payments.payment p
WHERE p.initiated_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
    DATE(p.initiated_at),
    p.payment_rail,
    p.payment_type,
    p.status
ORDER BY
    payment_date DESC,
    total_amount_sar DESC;
```

```sql
-- ============================================================
-- SLA MONITORING VIEW
-- Shows average API response times per external service
-- for the last 24 hours. Operations team dashboard.
-- Surfaces SLA breaches before they become incidents.
-- ============================================================

CREATE OR REPLACE VIEW payments.v_api_sla_monitor AS
SELECT
    service_name,
    COUNT(*)                          AS total_calls,
    COUNT(*) FILTER
        (WHERE response_status = 'SUCCESS')
                                      AS successful_calls,
    COUNT(*) FILTER
        (WHERE response_status = 'FAILED')
                                      AS failed_calls,
    COUNT(*) FILTER
        (WHERE response_status = 'TIMEOUT')
                                      AS timeouts,
    ROUND(AVG(response_time_ms))      AS avg_response_ms,
    MAX(response_time_ms)             AS max_response_ms,
    PERCENTILE_CONT(0.95)
        WITHIN GROUP
        (ORDER BY response_time_ms)   AS p95_response_ms
FROM payments.external_api_log
WHERE request_timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY service_name
ORDER BY avg_response_ms DESC;
```

---

### Step 8 — Validate with a Business Scenario

The schema is only proven when a real business scenario can
be traced through it completely. Take this scenario:

**A customer initiates a SAR 85,000 SARIE transfer.**

Trace every table that is read or written, in order:

```
STEP 1: Customer initiates payment via mobile app

  WRITE → payments.payment
    payment_id:            gen_random_uuid()
    payment_ref:           'PMT-2025-0847'
    payment_rail:          'SARIE'
    payment_type:          'TRANSFER'
    initiator_customer_id: 'C000000001'
    debit_account_id:      'ACC0000000000001'
    beneficiary_iban:      'SA09876543210987654321'
    beneficiary_name:      'Mohammed Al-Rashidi'
    amount_sar:            85000.00
    status:                'INITIATED'
    compliance_screened:   FALSE
    sanctions_checked:     FALSE

  WRITE → payments.payment_status_history
    old_status:  NULL
    new_status:  'INITIATED'
    changed_by:  'MOBILE_APP_v4.2'

─────────────────────────────────────────────────────────

STEP 2: AML system screens the payment
        (amount > SAR 60,000 — mandatory SAMA threshold)

  WRITE → payments.external_api_log
    service_name:       'OFAC'
    request_ref:        payment_id
    customer_id:        'C000000001'
    response_status:    'SUCCESS'
    response_time_ms:   312

  UPDATE → payments.payment
    sanctions_checked:  TRUE

  WRITE → payments.payment_status_history
    old_status:  'INITIATED'
    new_status:  'PROCESSING'
    changed_by:  'AML_ENGINE_v3'

─────────────────────────────────────────────────────────

STEP 3: Compliance screening completes

  UPDATE → payments.payment
    compliance_screened: TRUE
    status:              'PROCESSING'

─────────────────────────────────────────────────────────

STEP 4: Payment submitted to SARIE

  WRITE → payments.external_api_log
    service_name:       'SARIE'
    request_ref:        payment_id
    response_status:    'SUCCESS'
    response_time_ms:   1842

  UPDATE → payments.payment
    sarie_uetr:      'f47ac10b-58cc-4372-a567-0e02b2c3d479'
    status:          'COMPLETED'
    completed_at:    CURRENT_TIMESTAMP

  WRITE → payments.payment_status_history
    old_status:  'PROCESSING'
    new_status:  'COMPLETED'
    changed_by:  'SARIE_GATEWAY_v2'

─────────────────────────────────────────────────────────

RESULT: Every step traced. Every table identified.
        No step requires a table that does not exist.
        The schema supports this scenario completely.
```

**Now ask: what if the OFAC check fails?**

```
STEP 2 (alternative): OFAC returns a sanctions match

  WRITE → payments.external_api_log
    service_name:       'OFAC'
    response_status:    'SUCCESS'  ← API succeeded technically
    response_time_ms:   287

  UPDATE → payments.payment
    sanctions_checked:  TRUE       ← check ran
    status:             'REJECTED' ← but payment is rejected

  WRITE → payments.payment_status_history
    old_status:   'INITIATED'
    new_status:   'REJECTED'
    changed_by:   'AML_ENGINE_v3'
    change_reason:'OFAC_SANCTIONS_MATCH — list: SDN, ref: OFX-847'

  → No further steps. Payment stops here.
  → The payment record remains in the database permanently.
  → The history table shows the complete trail.
  → The SAMA examiner can see exactly what happened and why.
```

The scenario trace proves that the schema works.
If a scenario cannot be traced through the schema,
the schema has a gap.

---

## Part 3 — Now Apply This to the Other Four Domains

You have now seen the complete process for one domain.
The method is identical for every other domain.

For each remaining domain, follow the same eight steps:

```
1. Write the domain purpose in one sentence
2. List the business questions it must answer
3. Find the entities (real-world things to remember)
4. Establish the relationships
5. Draw the conceptual model
6. Build the attribute-level logical model
   → For every attribute: type, constraint, PDPL, source system
   → For every decision: write the rationale
7. Write the physical DDL
   → Constraints, indexes, partitioning, immutability triggers
8. Validate with at least one business scenario
```

**A few domain-specific things to watch for:**

```
PRODUCT DOMAIN:
→ The SSB CHECK constraint is the most important design decision.
→ Product terms must be versioned — a customer's Murabaha contract
  must always be traceable to the terms that applied at signing,
  not the current terms.

CUSTOMER DOMAIN:
→ The parent + subtype decision for Individual vs Corporate.
→ The CUSTOMER_CONSENT table is a core entity, not an afterthought.
→ Every attribute needs a PDPL classification before you move on.

ORDERS DOMAIN:
→ APPLICATION_STATUS_HISTORY is mandatory and immutable.
→ The three compliance checks (AML, Nafath, SIMAH) must all be
  columns on the application table — not external lookups.
→ The connection from application to contract to schedule
  must be traceable in both directions.

INVENTORY DOMAIN:
→ The product_quota table is the enforcement mechanism for
  SAMA capital limits. It must be updated atomically with
  every approval — not in a separate batch job.
→ The v_product_availability view is queried on every product
  offer page — it must be fast. Consider materialisation.
```

---

## Part 4 — Before You Begin Working

Three things to do before you open any tool:

```
┌─────────────────────────────────────────────────────────┐
│  READ THE REQUIREMENTS AGAIN                            │
│                                                         │
│  You have read them once. Read them again. Slowly.      │
│  Find the schema decisions hidden inside each one.      │
│  Write them down before you start designing.            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  AGREE ON DOMAIN BOUNDARIES WITH YOUR TEAM              │
│                                                         │
│  Before anyone draws a box, agree on which entities     │
│  live in which domain. The most expensive mistake is    │
│  two team members building the same entity in two       │
│  different domains.                                     │
│                                                         │
│  The rule: the domain that first creates the            │
│  authoritative record owns the entity.                  │
│  Other domains reference it via foreign keys.           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  WRITE YOUR ADR FOR EVERY MAJOR DECISION                │
│                                                         │
│  Do not wait until the design is finished to document   │
│  your decisions. Write the ADR at the moment you make   │
│  the decision. The reasoning is freshest then.          │
│                                                         │
│  If you cannot write the rationale for a decision,      │
│  that is a signal the decision has not been thought     │
│  through sufficiently. Think again before proceeding.   │
└─────────────────────────────────────────────────────────┘
```

---

> **A final thought.**
>
> The architecture you produce is not graded on how many
> entities it contains or how complex the diagram looks.
> It is graded on whether it works — whether a real scenario
> can be traced through it completely, whether every regulatory
> obligation is satisfied, and whether every decision can be
> explained and defended.
>
> Simple, clean, well-justified architecture beats complex,
> cluttered architecture every time.
>
> When in doubt: start with the business question.
> The schema follows from the question.
> It always does.

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*
-e 

---


# The Retail Mini-Project — Customer Domain
## How to Read the Requirements, Find the Schema, and Build It End to End
### Al-Noor Bank | Digital Retail Banking Platform

---

> **How to use this guide.**
>
> This guide follows the same eight-step process used for
> the Payments Domain. If you have not read the Payments
> Domain walkthrough first, do that before reading this one.
> The method is the same. The domain-specific decisions are different.
>
> The Customer Domain is the most complex domain in this
> architecture. It is the one every other domain depends on.
> It contains the most PDPL-sensitive data. It has the most
> design decisions that are genuinely debatable.
>
> Read every decision block carefully. Do not skip them.
> The decisions are where the architecture lives.

---

## Step 1 — Understand the Domain's Purpose

**The question:** What problem does the Customer Domain
exist to solve?

**The answer:** To be the single, authoritative source of
truth for who Al-Noor Bank's customers are — their identity,
their verification status, their risk profile, their consent
to data processing, and their relationship to the bank's
products and accounts.

**Why "single source of truth" matters:**

```
WITHOUT a Customer Domain as the authoritative source:

  The KYC system has one version of Ahmed Al-Omari.
  The CBS has a slightly different version.
  The mobile app onboarding platform has a third version.
  The DWH has aggregated all three into something else entirely.

  When SAMA asks: "What is the current KYC status of
  customer C000000001?" — which system do you trust?

  When the PDPL authority asks: "Show me every piece of
  personal data you hold on this individual and its legal
  basis for processing" — which system do you query?

  The answer must always be the same system.
  That system is the Customer Domain.

WITH a Customer Domain as the authoritative source:

  One record. One version. All other systems reference it.
  SAMA gets one answer. The PDPL authority gets one answer.
  Customer service sees the same data the risk team sees.
```

**The domain boundary:**

The Customer Domain owns customer identity and relationships.
It does not own what the customer has bought — that is Orders.
It does not own how the customer pays — that is Payments.
It does not own what the customer can buy — that is Product.

Every other domain references the Customer Domain.
No other domain owns a customer record.

---

## Step 2 — Identify the Business Questions

Write the questions the business will ask of this domain
every day before drawing a single entity. Every question
becomes a query. Every query tells you what data you need.

```
COMPLIANCE TEAM:
→ Which high-risk customers are overdue for KYC renewal?
→ Which customers are currently flagged as PEP?
→ Which customers are on the OFAC or UN sanctions list?
→ Show me the full KYC history for customer C000000003.
→ Which customers have withdrawn their marketing consent?
→ Which customers have a legal_hold on their records?

RISK MANAGEMENT:
→ How many customers are in each risk rating (H, M, L)?
→ What is the total deposit exposure per customer segment?
→ Which PREMIUM customers have an active Murabaha contract?
→ Which customers have both a HIGH risk rating and an
  open AML alert on any of their accounts?

CUSTOMER SERVICE:
→ Show me the complete profile for customer C000000001.
→ What accounts does this customer hold and in what capacity?
→ When was this customer's last KYC review and what was
  the outcome?
→ What has this customer consented to?

SAMA REPORTING:
→ How many new customers were onboarded digitally this month?
→ What is the breakdown of customers by nationality
  and customer segment?
→ How many customers have expired KYC as of today?
→ What is the total number of PEP customers currently active?

DIGITAL ONBOARDING PLATFORM:
→ Has this national_id been verified through Nafath?
→ Does this customer already exist in the system
  (duplicate NID check)?
→ What channel was this customer onboarded through?
→ Has this customer given consent for credit bureau sharing?
```

Now map every question to a column or relationship:

```
"Which high-risk customers are overdue for KYC renewal?"
→ risk_rating column on customer table
→ kyc_last_reviewed column on customer table
→ INDEX on (risk_rating, kyc_last_reviewed) for performance

"Which customers are flagged as PEP?"
→ is_pep BOOLEAN column on customer table

"Show the full KYC history for a customer."
→ kyc_record table — one row per review, never overwritten
→ FK from kyc_record to customer

"Which customers have withdrawn marketing consent?"
→ customer_consent table
→ processing_purpose = 'MARKETING_COMMS'
→ withdrawn_at IS NOT NULL

"Has this NID been verified through Nafath?"
→ nafath_verified BOOLEAN on customer table
→ OR external_api_log with service = 'NAFATH'
   and request_ref = application_id

"Does this customer already exist — duplicate NID check?"
→ UNIQUE constraint on national_id column
→ No two rows can share the same NID — enforced at DB level

"What channel was this customer onboarded through?"
→ onboarding_channel column on customer table

"What has this customer consented to?"
→ customer_consent table
→ One row per processing_purpose per customer
```

You now know most of the columns and tables you need
before drawing a single entity. This is the correct
starting point.

---

## Step 3 — Find the Entities

Ask: what are the real-world things the Customer Domain
needs to remember?

```
CUSTOMER (abstract parent)
The core identity record. Shared attributes that apply
to all customer types — KYC status, risk rating, PEP flag,
sanctions flag, onboarding channel and date.
This entity exists because INDIVIDUAL and CORPORATE customers
share a common identity concept, even though their specific
attributes differ significantly.

INDIVIDUAL_CUSTOMER (subtype)
Saudi national or resident individuals. National ID,
date of birth, nationality, income, employment status.
Everything specific to a natural person that does not
apply to a company.

CORPORATE_CUSTOMER (subtype)
Saudi-registered companies and organisations. Commercial
Registration number, GOSI establishment ID, VAT number,
authorised signatory. Everything specific to a legal entity
that does not apply to a natural person.

KYC_RECORD
The record of each Know-Your-Customer review. One customer
can have many KYC records over their lifetime — each review
is a new row, never an overwrite. This is the audit trail
that SAMA requires at examination time.

CUSTOMER_CONTACT
Phone numbers, email addresses, physical addresses.
Separated from the core customer entity because:
(a) a customer can have multiple contacts of each type
(b) contact data has different PDPL retention rules
    than identity data
(c) contact data changes more frequently than identity data

CUSTOMER_DOCUMENT
Copies or references to identity documents — national ID
scan, passport, proof of address. High PDPL sensitivity.
Stored with reference to a secure document store,
not as raw binary data in the database.

CUSTOMER_CONSENT
The PDPL compliance entity. One row per processing purpose
per customer. The legal basis for every data processing
activity documented at the schema level. This is the
evidence of PDPL compliance — not a policy document,
not a checkbox. A database record.

CUSTOMER_RELATIONSHIP
Manages relationships between customers —
joint account holders, guardians for minors,
power of attorney arrangements.
Also manages the link between customers and accounts
via the customer_account bridge.
```

**What is NOT in this list:**

```
ACCOUNT — lives in the Customer Domain but as a
supporting entity, referenced via customer_account.
Its primary relationship is to the retail schema
where accounts are managed.

PAYMENT — lives in the Payments Domain.
The Customer Domain does not own payment records.

PRODUCT_APPLICATION — lives in the Orders Domain.
The Customer Domain does not own application records.
It is referenced by them.
```

---

## Step 4 — Establish the Relationships

```
CUSTOMER (parent) ─────────── 1:1 ──────────► INDIVIDUAL_CUSTOMER
                  └─────────── 1:1 ──────────► CORPORATE_CUSTOMER

DECISION: Why 1:1 and not 1:N?
A customer is either an individual or a corporate entity.
Not both. Not sometimes one and sometimes the other.
The 1:1 relationship with a shared primary key enforces
this at the database level. The parent customer_id is also
the primary key of the subtype table — making it impossible
to have an individual customer without a parent customer row,
and impossible for a customer to have both subtypes.

CUSTOMER ──────────────────── 1:N ──────────► KYC_RECORD
One customer, many KYC reviews over their lifetime.
Each review is a new row. The history is permanent.

CUSTOMER ──────────────────── 1:N ──────────► CUSTOMER_CONTACT
One customer, potentially many contact records
(mobile, home phone, email, postal address).

CUSTOMER ──────────────────── 1:N ──────────► CUSTOMER_DOCUMENT
One customer, potentially many identity documents
(NID, passport, utility bill for address proof).

CUSTOMER ──────────────────── 1:N ──────────► CUSTOMER_CONSENT
One customer, one row per processing purpose.
Maximum six rows per customer (one per defined purpose).
Not truly unbounded — bounded by the number of purposes.

CUSTOMER ──────────────────── M:M ─────────► ACCOUNT
Via the customer_account bridge table.
One customer can hold multiple accounts.
One account can be linked to multiple customers (joint).
The bridge carries the relationship type:
PRIMARY, JOINT, AUTHORISED_SIGNATORY, GUARDIAN.

CORPORATE_CUSTOMER ──────────── N:1 ────────► INDIVIDUAL_CUSTOMER
Via authorised_signatory_id.
Every corporate customer has one designated individual
authorised to sign on its behalf.
That individual must already exist as a customer.
```

---

## Step 5 — The Conceptual Model

```
CONCEPTUAL MODEL — CUSTOMER DOMAIN

┌─ CUSTOMER DOMAIN ──────────────────────────────────────────────────┐
│                                                                    │
│                    ┌─────────────┐                                 │
│                    │  CUSTOMER   │  ← abstract parent              │
│                    │  (parent)   │    shared identity              │
│                    └──────┬──────┘                                 │
│                           │                                        │
│              ┌────────────┴────────────┐                           │
│              │ 1:1                     │ 1:1                        │
│              ▼                         ▼                           │
│  ┌───────────────────┐   ┌───────────────────────┐                 │
│  │   INDIVIDUAL_     │   │   CORPORATE_          │                 │
│  │   CUSTOMER 🔒     │   │   CUSTOMER            │                 │
│  │                   │   │                       │                 │
│  │ NID, DOB,         │   │ CR No, VAT,           │                 │
│  │ nationality,      │   │ GOSI, authorised      │                 │
│  │ income            │   │ signatory ─────────────────────┐        │
│  └───────────────────┘   └───────────────────────┘        │        │
│                                                            │ N:1    │
│  ┌─────────────────────────────────────────────────────┐  │        │
│  │         SUPPORTING ENTITIES                         │  ▼        │
│  │                                                     │ (references│
│  │  ┌─────────────┐  ┌──────────────┐                 │  individual│
│  │  │ KYC_RECORD  │  │ CUSTOMER_    │                 │  customer) │
│  │  │             │  │ CONTACT 🔒   │                 │            │
│  │  │ 1:N per     │  │              │                 │            │
│  │  │ customer    │  │ 1:N per      │                 │            │
│  │  │ append-only │  │ customer     │                 │            │
│  │  └─────────────┘  └──────────────┘                 │            │
│  │                                                     │            │
│  │  ┌─────────────┐  ┌──────────────┐                 │            │
│  │  │ CUSTOMER_   │  │ CUSTOMER_    │                 │            │
│  │  │ DOCUMENT 🔒 │  │ CONSENT      │                 │            │
│  │  │             │  │              │                 │            │
│  │  │ 1:N per     │  │ 1 per        │                 │            │
│  │  │ customer    │  │ purpose per  │                 │            │
│  │  │             │  │ customer     │                 │            │
│  │  └─────────────┘  └──────────────┘                 │            │
│  └─────────────────────────────────────────────────────┘            │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  CUSTOMER ──── M:M (via customer_account bridge) ──── ACCOUNT│  │
│  │  relationship: PRIMARY / JOINT / AUTHORISED_SIGNATORY /      │  │
│  │  GUARDIAN                                                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  🔒 = Contains PDPL-restricted or confidential personal data       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

CROSS-DOMAIN REFERENCES (Customer Domain is referenced by):
→ Orders Domain    (product_application.customer_id)
→ Payments Domain  (payment.initiator_customer_id)
→ Finance Domain   (murabaha_contract.customer_id)
→ Compliance Domain (aml_alert via account → customer_account)
```

**Check before moving on:**

```
□ Is the parent + subtype structure visible?
□ Are all supporting entities shown?
□ Is the M:M customer-account relationship captured?
□ Are PDPL-sensitive entities marked?
□ Are cross-domain references shown as outbound references,
  not as entities owned by this domain?
□ Could a business stakeholder read this and confirm
  it matches how customer data actually works in the bank?
```

---

## Step 6 — The Logical Model

Every entity from the conceptual model now gets its
attributes, data types, constraints, PDPL classification,
and source system — with a decision rationale for every
non-obvious choice.

---

### Entity 1: CUSTOMER (Parent)

```
CUSTOMER
────────────────────────────────────────────────────────────────────
Attribute            Type         Constraint      PDPL      Source
────────────────────────────────────────────────────────────────────
customer_id          CHAR(10)     PK, NOT NULL    Internal  CBS

DECISION: Why CHAR(10) and not SERIAL or UUID?
The customer_id is the CIF number — the Customer Information
File number assigned by the Core Banking System at onboarding.
It is a natural key. It already exists in the source system.
It is stable — it never changes once assigned.
It is meaningful — the CIF number is how every system in the
bank, every integration, and every API identifies a customer.
Making it the primary key means the database enforces uniqueness
on the business identifier itself. SERIAL would create a second
identifier with no business meaning. UUID would waste space
and create a mismatch with the CBS identifier.

customer_type        CHAR(1)      NOT NULL        Internal  CBS
                                  CHECK ('I','C')

DECISION: Why CHAR(1) with a CHECK constraint?
The discriminator tells us whether the subtype row lives in
INDIVIDUAL_CUSTOMER or CORPORATE_CUSTOMER.
CHAR(1) is the smallest correct type for a two-value enum.
The CHECK constraint makes any value other than 'I' or 'C'
impossible to store. This prevents the wrong type from being
assigned at the source.

customer_segment     VARCHAR(30)  NOT NULL        Internal  CBS

risk_rating          CHAR(1)      NOT NULL        Internal  AML System
                                  DEFAULT 'L'
                                  CHECK ('H','M','L')

DECISION: Why is the DEFAULT 'L' (Low)?
New customers have not yet been risk-assessed.
The safest default for a new customer is the lowest risk rating.
This prevents a system failure in the AML risk assessment from
accidentally granting a new customer a HIGH risk rating — which
would trigger a less rigorous review than the correct rating.
Default to the most conservative state. Upgrade with evidence.

kyc_status           VARCHAR(20)  NOT NULL        Internal  KYC Platform
                                  DEFAULT 'PENDING'
                                  CHECK (...)

DECISION: Why DEFAULT 'PENDING' not 'VERIFIED'?
A customer who has just been created has not yet been verified.
Defaulting to PENDING is the only safe choice. Defaulting to
VERIFIED would mean a customer record could exist in the system
as verified without any verification having taken place.
KYC_STATUS = PENDING prevents the account from being activated
until the verification workflow completes.

kyc_last_reviewed    DATE         NOT NULL        Internal  KYC Platform

is_pep               BOOLEAN      NOT NULL        Internal  OFAC / AML System
                                  DEFAULT FALSE

DECISION: Why a boolean flag and not a separate PEP entity?
The is_pep flag is queried on every transaction, every application,
and every customer service interaction. It must be answered in
a single column read — not a JOIN to a separate PEP table.
Performance and simplicity justify the boolean.
The full PEP classification detail (political position, country,
relationship type) is held in the AML system — not replicated here.
This table holds only the flag that other systems need quickly.

is_sanctioned        BOOLEAN      NOT NULL        Internal  OFAC / UN Feed
                                  DEFAULT FALSE

DECISION: Same rationale as is_pep.
When is_sanctioned = TRUE, the system must immediately block
all transactions and applications. The boolean enables this
check in microseconds. A JOIN to a sanctions entity would not.

onboarding_channel   VARCHAR(20)  NOT NULL        Internal  Onboarding Platform
                                  CHECK (BRANCH, DIGITAL,
                                         API, MIGRATION)

DECISION: Why is onboarding_channel a CHECK constraint?
SAMA tracks digital vs branch onboarding separately in
regulatory reports. The valid channels are known in advance.
A CHECK constraint means no channel outside this list can enter
the system — not through the application, not through direct SQL.
MIGRATION is included for the initial data migration from the
legacy branch system — customers whose records are being
transferred to the new platform.

onboarding_date      DATE         NOT NULL        Internal  Onboarding Platform
                                  DEFAULT CURRENT_DATE

created_at           TIMESTAMPTZ  NOT NULL        Internal  System
                                  DEFAULT NOW()
────────────────────────────────────────────────────────────────────
```

---

### Entity 2: INDIVIDUAL_CUSTOMER (Subtype)

```
INDIVIDUAL_CUSTOMER 🔒
────────────────────────────────────────────────────────────────────
Attribute            Type          Constraint     PDPL        Source
────────────────────────────────────────────────────────────────────
customer_id          CHAR(10)      PK, NOT NULL   Internal    CBS
                                   FK → customer

DECISION: Why is customer_id both the PK and a FK?
This is the defining characteristic of the subtype pattern.
The individual_customer table does not have its own identity.
It shares the identity of the parent customer row.
customer_id in this table = the same customer_id in the parent.
This enforces the 1:1 relationship structurally.
You cannot insert an individual_customer row without a matching
parent customer row — the FK prevents it.
You cannot have two individual_customer rows for one customer —
the PK prevents it.

national_id          VARCHAR(15)   NOT NULL       🔒 Restricted  Nafath
                                   UNIQUE

DECISION: Why VARCHAR(15) and not INTEGER or CHAR(10)?
Saudi National IDs are 10 digits. Iqama (residency) numbers
are also numeric but can have leading zeros. Storing as INTEGER
silently drops leading zeros — a record with NID 0123456789
becomes 123456789, which no longer matches the Nafath source.
VARCHAR preserves the value exactly as issued.
UNIQUE enforces that no two customers share the same NID.
This is both a data quality rule and a PDPL obligation.

DECISION: Why is national_id in INDIVIDUAL_CUSTOMER
and not in the CUSTOMER parent table?
Because corporate customers do not have a national_id.
Putting national_id on the parent table would mean every
corporate customer row has NULL in that column.
NULL in a column that should never be null for one type
is a design smell. The subtype pattern eliminates it.

full_name_ar         NVARCHAR(200) NOT NULL       Confidential   Nafath
full_name_en         VARCHAR(200)  NOT NULL       Confidential   Nafath

DECISION: Why NVARCHAR for Arabic but VARCHAR for English?
NVARCHAR stores Unicode characters natively on systems that
distinguish between the two. On PostgreSQL with UTF8 encoding,
VARCHAR handles both correctly. The distinction is noted here
because it matters on SQL Server and Oracle — be aware if
the schema is ever migrated to a different engine.

date_of_birth        DATE          NOT NULL       🔒 Restricted  Nafath

DECISION: PDPL classification of date_of_birth?
Restricted — not Confidential. Date of birth, combined with
name and nationality, is sufficient to uniquely identify an
individual. It is biographic data in the same category as
national_id. It requires explicit consent or legal basis to
process and must be encrypted at rest.

nationality          CHAR(2)       NOT NULL       Confidential   Nafath

DECISION: Why CHAR(2) for nationality?
ISO 3166-1 alpha-2 country codes — SA, US, GB, EG, etc.
Always exactly two characters. CHAR(2) is the correct type.
VARCHAR would allow invalid values of arbitrary length.

mobile_number        VARCHAR(15)   NOT NULL       🔒 Restricted  Customer input

DECISION: PDPL classification of mobile_number?
Restricted. A mobile number directly identifies an individual
and is used as a second factor for authentication.
It is more sensitive than a name — it can be used to contact,
track, or impersonate a person. Restricted classification is correct.

email_address        VARCHAR(200)  NULLABLE       Confidential   Customer input

DECISION: Why nullable?
Not all Saudi bank customers have or provide email addresses.
Making it mandatory would exclude a significant portion of
the target population — particularly older customers and those
in lower income segments. The digital onboarding journey
requests it but cannot require it.

monthly_income_sar   NUMERIC(15,2) NULLABLE       🔒 Restricted  Customer declaration

DECISION: Why Restricted and not Confidential?
This is the classification debate. Monthly income reveals
financial circumstances. Under PDPL, data that reveals an
individual's financial situation is categorised as sensitive
personal data requiring a higher level of protection.
Restricted classification means:
(a) encrypted at rest
(b) access restricted to roles with a documented need
    (credit assessment, Murabaha affordability)
(c) not visible in general customer service screens
Many participants default to Confidential here — challenge them.

DECISION: Why nullable?
Income is required for financing applications (Murabaha
affordability assessment). It is not required for account
opening. Making it mandatory would prevent account-only
customers from being onboarded — which contradicts F1.

employment_status    VARCHAR(20)   NOT NULL       Internal       Customer declaration
                                   CHECK (EMPLOYED,
                                          SELF_EMPLOYED,
                                          RETIRED, STUDENT,
                                          UNEMPLOYED)

employer_name        VARCHAR(200)  NULLABLE       Confidential   Customer declaration
────────────────────────────────────────────────────────────────────
```

---

### Entity 3: CORPORATE_CUSTOMER (Subtype)

```
CORPORATE_CUSTOMER
────────────────────────────────────────────────────────────────────
Attribute                Type         Constraint    PDPL      Source
────────────────────────────────────────────────────────────────────
customer_id              CHAR(10)     PK, NOT NULL  Internal  CBS
                                      FK → customer

company_name_ar          VARCHAR(300) NOT NULL      Confidential  MoC
company_name_en          VARCHAR(300) NOT NULL      Confidential  MoC

commercial_reg_no        VARCHAR(20)  NOT NULL      Internal  MoC
                                      UNIQUE

DECISION: Why VARCHAR(20) for commercial_reg_no?
Saudi Ministry of Commerce CR numbers are 10 digits.
VARCHAR(20) allows for format variations and international
entities. UNIQUE enforces that no two corporate customers
share the same CR number — structurally equivalent to the
UNIQUE constraint on national_id for individuals.

DECISION: Why Internal classification?
The CR number is a public business identifier — it appears on
company letterheads, government portals, and tender documents.
It is not personal data under PDPL. Internal classification
is correct. Some participants classify it as Confidential —
challenge this. Public registration numbers are not sensitive.

vat_number               VARCHAR(15)  NULLABLE      Internal  ZATCA

DECISION: Why nullable?
Not all corporate customers are VAT-registered. Small
businesses below the VAT threshold, non-profit organisations,
and government entities may not have a VAT number.
Making it mandatory would block legitimate corporate customers
from being onboarded.

DECISION: What format is the VAT number?
ZATCA-issued, always 15 digits, always starts with '3'.
A CHECK constraint on format would be ideal but requires
a regex-capable constraint or a trigger. At minimum, document
the format in the attribute dictionary and validate in the
application layer.

gosi_establishment_id    VARCHAR(20)  NULLABLE      Internal  GOSI

DECISION: What is GOSI and why is it here?
General Organisation for Social Insurance employer registration.
Required for Murabaha affordability assessments for corporate
customers — GOSI data confirms payroll stability and workforce
size, which feeds into the financing affordability calculation.
Nullable because not all corporate customers apply for financing.

industry_sector          VARCHAR(50)  NULLABLE      Internal  Customer declaration

annual_revenue_sar       NUMERIC(15,2) NULLABLE     Confidential  Customer declaration

DECISION: Why Confidential and not Restricted for revenue?
Corporate financial data is commercially sensitive but it
is not personal data under PDPL — it belongs to a legal entity,
not a natural person. PDPL applies to natural persons.
Confidential classification is appropriate for commercially
sensitive data about companies. Restricted is for personal data
of individuals.

authorised_signatory_id  CHAR(10)     NULLABLE      Internal  Customer declaration
                                      FK → individual_customer

DECISION: Why FK to individual_customer and not customer?
The authorised signatory must be an individual — a natural
person who can sign documents and bear legal responsibility.
A company cannot be an authorised signatory for another company.
The FK to individual_customer (rather than customer) enforces
this at the database level. A corporate customer_id cannot be
inserted as an authorised_signatory_id — because it would not
exist in the individual_customer table.
────────────────────────────────────────────────────────────────────
```

---

### Entity 4: KYC_RECORD

```
KYC_RECORD
────────────────────────────────────────────────────────────────────
Attribute          Type         Constraint      PDPL      Source
────────────────────────────────────────────────────────────────────
kyc_id             SERIAL       PK, NOT NULL    Internal  KYC Platform
customer_id        CHAR(10)     NOT NULL        Internal  KYC Platform
                                FK → customer

reviewed_date      DATE         NOT NULL        Internal  KYC Platform
reviewer_id        VARCHAR(50)  NOT NULL        Internal  KYC Platform

DECISION: Why is reviewer_id important?
SAMA supervisory reviews ask who performed the KYC review
and when. "The system" is not an acceptable answer. The
reviewer_id must identify either the officer who conducted
the review or the automated system that approved it.
'KYC_OFFICER_A42' or 'AUTO_NAFATH_VERIFY_v3' — both are valid.
Both are auditable. Neither is anonymous.

outcome            VARCHAR(20)  NOT NULL        Internal  KYC Platform
                                CHECK (PASS, FAIL,
                                       PENDING, ESCALATED)

DECISION: Why ESCALATED as an outcome?
Some KYC reviews cannot be resolved by the reviewing officer —
they require senior compliance review or legal input.
ESCALATED captures this state. Without it, the officer
would have to leave the review as PENDING indefinitely,
which masks the true state of the review from management.

expiry_date        DATE         NOT NULL        Internal  KYC Platform

DECISION: How is expiry_date calculated?
Application logic applies the SAMA schedule:
  risk_rating = 'H' → expiry = reviewed_date + 1 year
  risk_rating = 'M' → expiry = reviewed_date + 2 years
  risk_rating = 'L' → expiry = reviewed_date + 3 years
This is calculated at write time and stored — not calculated
at query time. Storing the expiry date means the nightly
KYC expiry job only needs to compare expiry_date < CURRENT_DATE
rather than recalculating the schedule for every customer.

notes              TEXT         NULLABLE        Internal  KYC Platform

DECISION: This table is append-only.
No row in KYC_RECORD is ever updated or deleted.
Each new review creates a new row.
The history of all reviews is permanently preserved.
An immutability trigger should enforce this — identical
to the one used for payment_status_history.
────────────────────────────────────────────────────────────────────
```

---

### Entity 5: CUSTOMER_CONSENT

```
CUSTOMER_CONSENT
────────────────────────────────────────────────────────────────────
Attribute            Type         Constraint      PDPL      Source
────────────────────────────────────────────────────────────────────
consent_id           SERIAL       PK, NOT NULL    Internal  Onboarding Platform
customer_id          CHAR(10)     NOT NULL        Internal  Onboarding Platform
                                  FK → customer

processing_purpose   VARCHAR(50)  NOT NULL        Internal  Policy
                                  CHECK (...)

DECISION: Why is this a CHECK constraint?
The valid processing purposes are defined by PDPL policy and
cannot be arbitrarily extended by a developer or a business
request. The CHECK constraint means no new purpose can be
added to the database without a deliberate schema change —
which requires compliance and legal review. This is the
correct level of control for PDPL compliance.

The valid purposes:
  ACCOUNT_OPERATIONS    — necessary to perform the contract
  MARKETING_COMMS       — promotional content; explicit consent
  CREDIT_BUREAU_SHARE   — sharing with SIMAH; legal obligation
  OPEN_BANKING_SHARE    — TPP data sharing; explicit consent
  ANALYTICS_PROFILING   — behavioural analysis; legitimate interest
  AML_COMPLIANCE        — legal obligation; cannot be refused

legal_basis          VARCHAR(30)  NOT NULL        Internal  Policy
                                  CHECK (CONSENT,
                                         CONTRACT,
                                         LEGAL_OBLIGATION,
                                         LEGITIMATE_INTEREST)

DECISION: Why does legal_basis matter as a schema attribute?
Because PDPL requires the data controller to be able to
demonstrate the legal basis for every processing activity.
If the PDPL authority asks "what is the legal basis for
processing this customer's credit bureau data?" — the answer
must be queryable from the database. Not reconstructed from
a policy document. Not assumed. Queryable.
legal_basis = 'LEGAL_OBLIGATION' for CREDIT_BUREAU_SHARE.
That is the answer. It is in the database.

consent_given        BOOLEAN      NOT NULL        Internal  Onboarding Platform

DECISION: Why store consent_given = FALSE rows?
A row where consent_given = FALSE records a refusal.
This is as important as a consent. If a customer refused
marketing consent, that refusal must be recorded —
not simply the absence of a consent row.
The absence of a row is ambiguous: it could mean the customer
was never asked, or it could mean the consent was not captured.
A FALSE row is unambiguous: the customer was asked and refused.

consent_date         TIMESTAMPTZ  NOT NULL        Internal  Onboarding Platform
                                  DEFAULT NOW()

consent_expiry       DATE         NULLABLE        Internal  Policy

DECISION: Why is consent_expiry important?
Some consents have a time limit. Marketing consent, under many
PDPL interpretations, cannot be assumed permanent — it must be
renewed periodically. The expiry date triggers a re-consent
workflow before the expiry. If expiry passes without renewal,
the consent is treated as withdrawn.
The system must check this column before sending marketing
communications — not just check whether consent_given = TRUE.

consent_method       VARCHAR(20)  NOT NULL        Internal  Onboarding Platform
                                  CHECK (APP, BRANCH_FORM,
                                         WEBSITE, IVR)

DECISION: Why capture the consent method?
PDPL requires that consent be freely given, specific, informed,
and unambiguous. The method of collection is evidence of
how the consent was obtained. Branch form consent is documented
differently from in-app consent. If the PDPL authority
investigates whether consent was properly obtained, the method
column provides the evidence.

withdrawn_at         TIMESTAMPTZ  NULLABLE        Internal  Customer request

DECISION: Why withdrawn_at and not a status column?
withdrawn_at captures the exact moment consent was withdrawn.
This is important because:
(a) processing must stop immediately after withdrawal
(b) any processing after withdrawn_at is a PDPL violation
(c) the timestamp is the legal evidence of when obligations changed
A status column (ACTIVE / WITHDRAWN) would lose the timing.
────────────────────────────────────────────────────────────────────
```

---

## Step 7 — The Physical DDL

```sql
-- ============================================================
-- CUSTOMER DOMAIN SCHEMAS
-- The retail schema holds customer-facing entities.
-- The compliance schema holds KYC and consent data
-- with restricted access.
-- ============================================================

CREATE SCHEMA retail;
CREATE SCHEMA compliance;
SET search_path TO retail, compliance;
```

---

#### The CUSTOMER Table

```sql
CREATE TABLE retail.customer (
    customer_id          CHAR(10)      NOT NULL,
    customer_type        CHAR(1)       NOT NULL
        CHECK (customer_type IN ('I', 'C')),
    customer_segment     VARCHAR(30)   NOT NULL,
    risk_rating          CHAR(1)       NOT NULL
        DEFAULT 'L'
        CHECK (risk_rating IN ('H', 'M', 'L')),
    kyc_status           VARCHAR(20)   NOT NULL
        DEFAULT 'PENDING'
        CHECK (kyc_status IN (
            'VERIFIED', 'EXPIRED', 'PENDING', 'REJECTED'
        )),
    kyc_last_reviewed    DATE          NOT NULL,
    relationship_branch  CHAR(10),
    onboarding_channel   VARCHAR(20)   NOT NULL
        CHECK (onboarding_channel IN (
            'BRANCH', 'DIGITAL', 'API', 'MIGRATION'
        )),
    onboarding_date      DATE          NOT NULL
                                       DEFAULT CURRENT_DATE,
    is_pep               BOOLEAN       NOT NULL DEFAULT FALSE,
    is_sanctioned        BOOLEAN       NOT NULL DEFAULT FALSE,
    is_deleted           BOOLEAN       NOT NULL DEFAULT FALSE,
    deleted_at           TIMESTAMPTZ,
    legal_hold           BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_customer PRIMARY KEY (customer_id),

    CONSTRAINT fk_customer_branch
        FOREIGN KEY (relationship_branch)
        REFERENCES retail.branch(branch_id)
);

-- ============================================================
-- INDEXES ON CUSTOMER
--
-- Index 1: risk_rating + kyc_last_reviewed
-- Serves the nightly KYC expiry job and compliance reports.
-- "All high-risk customers reviewed more than 12 months ago"
-- runs every night without a sequential scan.
--
-- Index 2: is_pep (partial — only TRUE rows)
-- PEP customers are a tiny minority.
-- A partial index on TRUE rows only is far smaller
-- than a full index on a boolean column.
-- Queries for PEP customers are fast on any dataset size.
--
-- Index 3: onboarding_channel + onboarding_date
-- Serves SAMA monthly digital onboarding report.
-- ============================================================

CREATE INDEX idx_customer_kyc_review
    ON retail.customer (risk_rating, kyc_last_reviewed);

CREATE INDEX idx_customer_pep
    ON retail.customer (is_pep)
    WHERE is_pep = TRUE;

CREATE INDEX idx_customer_onboarding
    ON retail.customer (onboarding_channel, onboarding_date DESC);
```

---

#### The INDIVIDUAL_CUSTOMER Table

```sql
CREATE TABLE retail.individual_customer (
    customer_id          CHAR(10)      NOT NULL,
    national_id          VARCHAR(15)   NOT NULL,
    full_name_ar         VARCHAR(200)  NOT NULL,
    full_name_en         VARCHAR(200)  NOT NULL,
    date_of_birth        DATE          NOT NULL,
    nationality          CHAR(2)       NOT NULL,
    mobile_number        VARCHAR(15)   NOT NULL,
    email_address        VARCHAR(200),
    monthly_income_sar   NUMERIC(15,2),
    employment_status    VARCHAR(20)   NOT NULL
        CHECK (employment_status IN (
            'EMPLOYED', 'SELF_EMPLOYED',
            'RETIRED', 'STUDENT', 'UNEMPLOYED'
        )),
    employer_name        VARCHAR(200),
    nafath_verified      BOOLEAN       NOT NULL DEFAULT FALSE,
    nafath_verified_at   TIMESTAMPTZ,

    CONSTRAINT pk_individual_customer
        PRIMARY KEY (customer_id),

    -- Shared PK with parent — enforces 1:1 subtype relationship
    CONSTRAINT fk_individual_parent
        FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id),

    -- No two individuals can share the same NID
    CONSTRAINT uq_national_id
        UNIQUE (national_id)
);
```

---

#### The CORPORATE_CUSTOMER Table

```sql
CREATE TABLE retail.corporate_customer (
    customer_id              CHAR(10)       NOT NULL,
    company_name_ar          VARCHAR(300)   NOT NULL,
    company_name_en          VARCHAR(300)   NOT NULL,
    commercial_reg_no        VARCHAR(20)    NOT NULL,
    vat_number               VARCHAR(15),
    gosi_establishment_id    VARCHAR(20),
    industry_sector          VARCHAR(50),
    annual_revenue_sar       NUMERIC(15,2),
    authorised_signatory_id  CHAR(10),

    CONSTRAINT pk_corporate_customer
        PRIMARY KEY (customer_id),

    CONSTRAINT fk_corporate_parent
        FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id),

    CONSTRAINT uq_commercial_reg
        UNIQUE (commercial_reg_no),

    -- Signatory must be an individual — not another corporate
    CONSTRAINT fk_signatory
        FOREIGN KEY (authorised_signatory_id)
        REFERENCES retail.individual_customer(customer_id)
);
```

---

#### The KYC_RECORD Table

```sql
CREATE TABLE compliance.kyc_record (
    kyc_id         SERIAL        NOT NULL,
    customer_id    CHAR(10)      NOT NULL,
    reviewed_date  DATE          NOT NULL,
    reviewer_id    VARCHAR(50)   NOT NULL,
    outcome        VARCHAR(20)   NOT NULL
        CHECK (outcome IN
            ('PASS', 'FAIL', 'PENDING', 'ESCALATED')),
    expiry_date    DATE          NOT NULL,
    notes          TEXT,

    CONSTRAINT pk_kyc_record
        PRIMARY KEY (kyc_id),

    CONSTRAINT fk_kyc_customer
        FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id)
);

CREATE INDEX idx_kyc_customer_date
    ON compliance.kyc_record (customer_id, reviewed_date DESC);
```

```sql
-- Immutability trigger — KYC records are permanent
CREATE OR REPLACE FUNCTION compliance.prevent_kyc_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'kyc_record is immutable — rows cannot be %d', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_kyc_immutable
    BEFORE UPDATE OR DELETE
    ON compliance.kyc_record
    FOR EACH ROW
    EXECUTE FUNCTION compliance.prevent_kyc_modification();
```

---

#### The CUSTOMER_CONSENT Table

```sql
CREATE TABLE compliance.customer_consent (
    consent_id           SERIAL        NOT NULL,
    customer_id          CHAR(10)      NOT NULL,
    processing_purpose   VARCHAR(50)   NOT NULL
        CHECK (processing_purpose IN (
            'ACCOUNT_OPERATIONS',
            'MARKETING_COMMS',
            'CREDIT_BUREAU_SHARE',
            'OPEN_BANKING_SHARE',
            'ANALYTICS_PROFILING',
            'AML_COMPLIANCE'
        )),
    legal_basis          VARCHAR(30)   NOT NULL
        CHECK (legal_basis IN (
            'CONSENT',
            'CONTRACT',
            'LEGAL_OBLIGATION',
            'LEGITIMATE_INTEREST'
        )),
    consent_given        BOOLEAN       NOT NULL,
    consent_date         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    consent_expiry       DATE,
    consent_method       VARCHAR(20)   NOT NULL
        CHECK (consent_method IN (
            'APP', 'BRANCH_FORM', 'WEBSITE', 'IVR'
        )),
    withdrawn_at         TIMESTAMPTZ,

    CONSTRAINT pk_consent
        PRIMARY KEY (consent_id),

    CONSTRAINT fk_consent_customer
        FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id),

    -- One row per purpose per customer
    CONSTRAINT uq_consent_purpose
        UNIQUE (customer_id, processing_purpose)
);

CREATE INDEX idx_consent_customer
    ON compliance.customer_consent (customer_id, processing_purpose);
```

---

#### The Reporting View

```sql
-- ============================================================
-- KYC EXPIRY DASHBOARD
-- Used by the compliance team every morning.
-- Shows every customer whose KYC is expired or due soon.
-- No complex JOIN — everything the compliance team needs
-- in one view with consistent logic in one place.
-- ============================================================

CREATE OR REPLACE VIEW compliance.v_kyc_expiry_dashboard AS
SELECT
    c.customer_id,
    ic.full_name_en,
    c.customer_segment,
    c.risk_rating,
    c.kyc_status,
    c.kyc_last_reviewed,
    CURRENT_DATE - c.kyc_last_reviewed     AS days_since_review,
    CASE c.risk_rating
        WHEN 'H' THEN c.kyc_last_reviewed + INTERVAL '1 year'
        WHEN 'M' THEN c.kyc_last_reviewed + INTERVAL '2 years'
        WHEN 'L' THEN c.kyc_last_reviewed + INTERVAL '3 years'
    END                                    AS review_deadline,
    CASE
        WHEN c.kyc_status = 'EXPIRED' THEN 'OVERDUE'
        WHEN (
            CASE c.risk_rating
                WHEN 'H' THEN c.kyc_last_reviewed + INTERVAL '1 year'
                WHEN 'M' THEN c.kyc_last_reviewed + INTERVAL '2 years'
                ELSE          c.kyc_last_reviewed + INTERVAL '3 years'
            END
        ) <= CURRENT_DATE + INTERVAL '30 days' THEN 'DUE_SOON'
        ELSE 'CURRENT'
    END                                    AS kyc_urgency
FROM retail.customer c
JOIN retail.individual_customer ic
    ON c.customer_id = ic.customer_id
WHERE c.is_deleted = FALSE
  AND c.customer_type = 'I'
ORDER BY kyc_urgency, review_deadline;
```

---

## Step 8 — Validate with a Business Scenario

**Scenario: A Saudi national applies digitally for
a Tawarruq Account. Trace every table.**

```
STEP 1: Applicant submits details via mobile app

  WRITE → retail.customer
    customer_id:        'C000000005'
    customer_type:      'I'
    kyc_status:         'PENDING'    ← default — not yet verified
    risk_rating:        'L'          ← default — not yet assessed
    onboarding_channel: 'DIGITAL'
    is_pep:             FALSE
    is_sanctioned:      FALSE

  WRITE → retail.individual_customer
    customer_id:        'C000000005'
    national_id:        '1122334455'
    full_name_en:       'Omar Al-Harbi'
    date_of_birth:      '1992-08-14'
    nationality:        'SA'
    mobile_number:      '+966507654321'
    nafath_verified:    FALSE         ← not yet

──────────────────────────────────────────────────────────────

STEP 2: Nafath eKYC verification

  WRITE → payments.external_api_log
    service_name:       'NAFATH'
    request_ref:        application_id
    customer_id:        'C000000005'
    response_status:    'SUCCESS'
    response_time_ms:   1240

  UPDATE → retail.individual_customer
    nafath_verified:    TRUE
    nafath_verified_at: CURRENT_TIMESTAMP

──────────────────────────────────────────────────────────────

STEP 3: KYC record created

  WRITE → compliance.kyc_record
    customer_id:    'C000000005'
    reviewed_date:  CURRENT_DATE
    reviewer_id:    'AUTO_NAFATH_VERIFY_v3'
    outcome:        'PASS'
    expiry_date:    CURRENT_DATE + INTERVAL '3 years'
                    (L risk = 3 year renewal cycle)

  UPDATE → retail.customer
    kyc_status:         'VERIFIED'
    kyc_last_reviewed:  CURRENT_DATE

──────────────────────────────────────────────────────────────

STEP 4: PDPL consent recorded

  WRITE → compliance.customer_consent (row 1)
    customer_id:          'C000000005'
    processing_purpose:   'ACCOUNT_OPERATIONS'
    legal_basis:          'CONTRACT'
    consent_given:        TRUE
    consent_method:       'APP'

  WRITE → compliance.customer_consent (row 2)
    processing_purpose:   'AML_COMPLIANCE'
    legal_basis:          'LEGAL_OBLIGATION'
    consent_given:        TRUE

  WRITE → compliance.customer_consent (row 3)
    processing_purpose:   'MARKETING_COMMS'
    legal_basis:          'CONSENT'
    consent_given:        FALSE   ← Omar declined marketing
    consent_method:       'APP'

──────────────────────────────────────────────────────────────

STEP 5: Account opened and linked

  WRITE → retail.account
    account_id:     'ACC0000000000005'
    account_type:   'TAWARRUQ'
    status:         'ACTIVE'

  WRITE → retail.customer_account
    customer_id:    'C000000005'
    account_id:     'ACC0000000000005'
    relationship:   'PRIMARY'

──────────────────────────────────────────────────────────────

RESULT: Complete trace. Every table identified.
        No step requires a table that does not exist.
        Omar's consent_given = FALSE for MARKETING_COMMS
        is recorded. He will not receive marketing communications.
        The database enforces this — not a manual suppression list.
```

**Now ask: what if Nafath verification fails?**

```
STEP 2 (alternative): Nafath returns identity mismatch

  WRITE → payments.external_api_log
    service_name:       'NAFATH'
    response_status:    'FAILED'
    error_code:         'NID_MISMATCH'
    error_message:      'Name does not match NID record'
    response_time_ms:   987

  UPDATE → retail.customer
    kyc_status:         'PENDING'    ← remains pending

  → No KYC record created
  → No consent recorded
  → No account created
  → The application returns to the onboarding platform
    with a 'PENDING_DOCS' or 'REJECTED' status
  → The customer_id row exists but cannot progress
    until manual KYC review resolves the mismatch
```

---

> **The Customer Domain is now complete.**
>
> You have gone from the first question — what problem does
> this domain solve? — through to a fully traced business
> scenario in eight steps.
>
> Apply the same method to the remaining three domains.
> The process is identical. The design decisions will differ.
> Every decision should be written down with its rationale
> before you move to the next attribute.
>
> A schema that cannot be explained cannot be defended.
> A schema that can be explained can be improved.

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*
-e 

---


# The Retail Mini-Project — Product Domain
## How to Read the Requirements, Find the Schema, and Build It End to End
### Al-Noor Bank | Digital Retail Banking Platform

---

> **How to use this guide.**
>
> This guide follows the same eight-step process used for the
> Payments Domain and the Customer Domain. If you have not read
> those two first, do that before reading this one.
> The method is the same. The domain-specific decisions differ.
>
> The Product Domain is the foundation everything else is built on.
> No application can be submitted, no account opened, no contract
> signed without a product defined here. Get this domain right
> first. Every other domain depends on it.

---

## Step 1 — Understand the Domain's Purpose

**The question:** What problem does the Product Domain exist to solve?

**The answer:** To define and govern every financial product Al-Noor
Bank can offer — what it is called, what its terms are, what it
costs, whether it is Sharia-compliant, and who has approved it.

**Why "govern" matters:**

```
WITHOUT a Product Domain as the authoritative source:

  The mobile app knows about Murabaha Home Finance at 4.25%.
  The branch system knows about it at 4.5%.
  The contract generation system uses a rate stored in a
  config file that was last updated in 2022.

  Three versions of the same product. Three different rates.
  Customers quote one figure. Contracts reflect another.
  SAMA asks which rate applies. No one can answer.

WITH a Product Domain as the authoritative source:

  One product record. One version. Every system reads from it.
  Rate changes happen in one place, reflected everywhere.
  SAMA gets one answer. Contracts reflect the current terms.
  Sharia compliance status is enforced at the database level.
```

**The domain boundary:**

The Product Domain owns the definition of what can be sold.
It does not own who applies for it — that is Orders.
It does not own how many can be approved — that is Inventory.
It does not own the customer buying it — that is Customer.

---

## Step 2 — Identify the Business Questions

Write the questions the business will ask of this domain every day
before drawing a single entity. Every question is a query.
Every query tells you what data you need.

```
PRODUCT MANAGEMENT TEAM:
→ Which products are currently active?
→ Which products are Sharia-compliant and what is their
  SSB approval reference?
→ What are the current terms for Murabaha Home Finance?
→ What profit rate does a PREMIUM customer get on
  Murabaha Personal Finance?
→ When does the current promotional rate expire?

COMPLIANCE TEAM:
→ Show me all Islamic products and their SSB approval references.
→ Has product PROD_MRB_002 ever been offered without an
  SSB approval reference?
→ What were the profit rates in effect on 1 January 2024?
  (point-in-time reporting — requires versioned terms)

SAMA REPORTING:
→ How many products in the catalogue are Sharia-compliant?
→ What products are currently active vs discontinued?
→ What is the profit rate range across financing products?

DIGITAL ONBOARDING PLATFORM:
→ What products is this customer segment eligible for?
  (minimum age, minimum balance, Sharia filter)
→ What is the profit rate for this customer's segment?
→ What are the minimum and maximum tenure options?
```

Now map every question to a column or relationship:

```
"Which products are currently active?"
→ is_active BOOLEAN on product table
→ INDEX on (is_active) — queried on every product page load

"Which Islamic products have an SSB reference?"
→ is_sharia_compliant BOOLEAN on product table
→ ssb_approval_ref VARCHAR on product table
→ CHECK (is_sharia_compliant = FALSE OR ssb_approval_ref IS NOT NULL)
→ The CHECK constraint makes the invalid state impossible

"What profit rate does a PREMIUM customer get?"
→ product_pricing table — one row per segment per product
→ customer_segment column to filter
→ profit_rate_pct column to return

"What were the rates on 1 January 2024?"
→ product_terms table with effective_date and expiry_date
→ Query: WHERE effective_date <= '2024-01-01'
         AND (expiry_date IS NULL OR expiry_date > '2024-01-01')
→ Historical terms must be preserved — never overwritten

"What is the minimum tenure for this product?"
→ min_tenure_months on product_terms
→ max_tenure_months on product_terms
```

You now know the core columns before drawing a single entity.

---

## Step 3 — Find the Entities

Ask: what are the real-world things the Product Domain
needs to remember?

```
PRODUCT_CATEGORY
The grouping that determines what type of product something is.
Islamic Deposits. Islamic Financing. Cards. Investments.
The is_islamic flag on this entity drives Sharia compliance
requirements on every product in the category.

PRODUCT
The product itself. Murabaha Home Finance. Tawarruq Savings.
One row per product. This is the entity that every other
domain references — by product_id — when they need to know
what was applied for, what terms applied, what the rate was.

PRODUCT_TERMS (versioned)
The commercial terms of the product — rates, tenures, amounts.
Terms change over time. The version that was active when a
contract was signed must be preserved permanently.
This is not an overwrite. It is an append with effective dates.

PRODUCT_PRICING
The rate offered to each customer segment.
PREMIUM customers pay a lower profit rate than STANDARD.
The same product. Different price. Separate entity.
```

**What is NOT in this list:**

```
PRODUCT_APPLICATION — belongs in Orders Domain.
  The application for a product is not the product itself.

PRODUCT_QUOTA — belongs in Inventory Domain.
  How many of a product can be sold is a capacity constraint,
  not a product definition.

PRODUCT_INVENTORY — not a banking concept.
  There is no physical stock of Murabaha contracts to deplete.
  Capacity is managed differently — see Inventory Domain.
```

---

## Step 4 — Establish the Relationships

```
PRODUCT_CATEGORY ──── categorises ──► PRODUCT
One category, many products.
A category change affects every product in that category
(is_islamic flag propagates through product rules).

PRODUCT ──── has terms ──────────────► PRODUCT_TERMS
One product, many term versions over time.
At any point in time, exactly one version is current.
Historical versions are never deleted.

PRODUCT ──── has pricing by segment ─► PRODUCT_PRICING
One product, one pricing row per customer segment.
PREMIUM, STANDARD, YOUTH, CORPORATE — each gets its own rate.
```

**The cross-domain references FROM this domain:**

```
product_domain.product.product_id
    ◄── referenced by orders_domain.product_application.product_id
    ◄── referenced by inventory_domain.product_quota.product_id

The Product Domain does not reference any other domain.
It is referenced by others. It is the source, not the consumer.
```

---

## Step 5 — The Conceptual Model

```
CONCEPTUAL MODEL — PRODUCT DOMAIN

┌─ PRODUCT DOMAIN ─────────────────────────────────────────────────┐
│                                                                  │
│   ┌─────────────────────┐                                        │
│   │   PRODUCT_CATEGORY  │                                        │
│   │                     │                                        │
│   │  Type: Islamic /    │                                        │
│   │  Conventional       │                                        │
│   └──────────┬──────────┘                                        │
│              │ categorises (1:N)                                 │
│              ▼                                                   │
│   ┌──────────────────────────────────────────────┐              │
│   │                  PRODUCT                     │              │
│   │                                              │              │
│   │  The core entity — everything else is        │              │
│   │  either a description of this product        │              │
│   │  or a constraint on how many can be sold     │              │
│   │                                              │              │
│   │  🔑 ssb_approval_ref (mandatory if Islamic)  │              │
│   └───────┬──────────────────────┬───────────────┘              │
│           │ has terms            │ has pricing                  │
│           │ (1:N versioned)      │ by segment (1:N)             │
│           ▼                      ▼                              │
│   ┌──────────────┐    ┌──────────────────────┐                 │
│   │ PRODUCT_TERMS│    │  PRODUCT_PRICING      │                 │
│   │              │    │                       │                 │
│   │ effective_   │    │  One row per segment  │                 │
│   │ date versioned│   │  PREMIUM / STANDARD   │                 │
│   │              │    │  YOUTH / CORPORATE    │                 │
│   └──────────────┘    └──────────────────────┘                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

CROSS-DOMAIN OUTBOUND REFERENCES (other domains reference us):
→ Orders Domain    (product_application.product_id)
→ Inventory Domain (product_quota.product_id)
```

**What to check before moving on:**

```
□ Is every entity in the correct domain boundary?
□ Are the versioned terms represented as a separate entity,
  not as a single overwriteable column on PRODUCT?
□ Is pricing by segment represented as its own entity,
  not as multiple columns on PRODUCT?
□ Is the SSB approval constraint visible at the conceptual level?
□ Can a business stakeholder — such as the Head of Product
  Management — read this and confirm it matches how the
  product catalogue actually works?
```

---

## Step 6 — The Logical Model

Every entity now gets its attributes, data types, constraints,
PDPL classification, and source system — with a decision rationale
for every non-obvious choice.

---

### Entity 1: PRODUCT_CATEGORY

```
PRODUCT_CATEGORY
────────────────────────────────────────────────────────────────────
Attribute       Type         Constraint      PDPL      Source
────────────────────────────────────────────────────────────────────
category_id     VARCHAR(10)  PK, NOT NULL    Internal  PMS

DECISION: Why VARCHAR(10) not SERIAL?
This is a business identifier — CAT_DEP (Deposits),
CAT_FIN (Financing), CAT_CRD (Cards). It must be readable
in SQL queries, SAMA reports, and config files without
a JOIN to decode it. SERIAL would require that JOIN everywhere.

category_name   VARCHAR(100) NOT NULL        Internal  PMS
is_islamic      BOOLEAN      NOT NULL        Internal  SSB / PMS
                             DEFAULT FALSE

DECISION: Why is_islamic on the CATEGORY not on the PRODUCT?
Because every product in the Islamic Financing category
is Sharia-compliant by definition. Storing it on the category
means one update when SAMA reclassifies a product type.
Storing it on every product means updating every product row —
and the risk that some rows are inconsistent with others
in the same category. The category is the governing level.
────────────────────────────────────────────────────────────────────
```

---

### Entity 2: PRODUCT

```
PRODUCT
────────────────────────────────────────────────────────────────────
Attribute            Type          Constraint      PDPL      Source
────────────────────────────────────────────────────────────────────
product_id           VARCHAR(15)   PK, NOT NULL    Internal  PMS

DECISION: Why VARCHAR(15) not SERIAL?
Same rationale as category_id. The product_id is a meaningful
business identifier — PROD_MRB_002 is immediately readable
in a query result as Murabaha product number 002.
Every table that references this product carries this ID.
SERIAL would produce 1234 — unintelligible without a JOIN.

category_id          VARCHAR(10)   NOT NULL        Internal  PMS
                                   FK → product_category

product_name_en      VARCHAR(200)  NOT NULL        Internal  PMS
product_name_ar      VARCHAR(200)  NOT NULL        Internal  PMS

DECISION: Why store both Arabic and English names?
SAMA regulatory submissions require Arabic product names.
Customer-facing digital interfaces use both languages.
Storing a single name and translating at runtime is fragile —
translation services change, translations drift, reports
using translated names become inconsistent with source records.
Store both. One is the authoritative Arabic name. One is English.

product_code         VARCHAR(20)   NOT NULL        Internal  PMS
                                   UNIQUE

DECISION: Why a separate product_code alongside product_id?
product_id is the internal system identifier.
product_code is the business-facing code printed on contracts,
letters to customers, and SAMA submissions — ALN-MRB-002.
These are different things serving different audiences.
If a product is ever reissued with a new internal ID, the
customer-facing code may remain the same. Separating them
prevents that business requirement from breaking the schema.

is_active            BOOLEAN       NOT NULL        Internal  PMS
                                   DEFAULT TRUE

DECISION: Why DEFAULT TRUE?
Products are active when they are created. They are deactivated
when discontinued. The default represents the normal state.
Note: is_active is the operational flag. A discontinued product
may still have active contracts that must be serviced.
Deactivating a product prevents new applications — it does not
affect existing obligations.

launch_date          DATE          NOT NULL        Internal  PMS
discontinue_date     DATE          NULLABLE        Internal  PMS

DECISION: Why store discontinue_date separately from is_active?
A product may be scheduled for discontinuation on a future date
before the operational is_active flag is set to FALSE.
The date enables automated deactivation and SAMA reporting
on when a product left the active catalogue.

min_age_years        SMALLINT      NOT NULL        Internal  PMS
                                   DEFAULT 18

DECISION: Why a database column for minimum age?
Some products — student accounts, youth savings — have a maximum
age. Senior products may have different minimums.
Storing this at the schema level means the onboarding platform
can query it rather than hardcoding eligibility rules.
Hardcoded rules in application code are invisible to
SAMA auditors reviewing the product governance framework.

min_balance_sar      NUMERIC(18,2) NOT NULL        Internal  PMS
                                   DEFAULT 0
max_exposure_sar     NUMERIC(18,2) NULLABLE        Internal  PMS / Risk

DECISION: Why is max_exposure_sar nullable?
Some products — current accounts, savings accounts — have no
maximum exposure. The bank is not lending money.
NULL correctly represents "no limit applies".
Zero would mean "no exposure allowed" — which is wrong.

is_sharia_compliant  BOOLEAN       NOT NULL        Internal  SSB / PMS
ssb_approval_ref     VARCHAR(50)   NULLABLE        Internal  SSB

DECISION: The most important constraint in the entire platform.
is_sharia_compliant = TRUE requires ssb_approval_ref IS NOT NULL.
Enforced by CHECK at the database level:
  CHECK (is_sharia_compliant = FALSE OR ssb_approval_ref IS NOT NULL)

Why not enforce this in the application layer?
Application code can be bypassed. A direct SQL INSERT,
a vendor patch, a migration script — all can bypass application
validation. The CHECK constraint cannot be bypassed by anything.
If an Islamic product is created without an SSB reference,
every contract signed under that product may be invalidated
by the Sharia Supervisory Board. The database prevents this
from being possible.
────────────────────────────────────────────────────────────────────
```

---

### Entity 3: PRODUCT_TERMS

```
PRODUCT_TERMS  (versioned)
────────────────────────────────────────────────────────────────────
Attribute           Type          Constraint      PDPL      Source
────────────────────────────────────────────────────────────────────
terms_id            SERIAL        PK, NOT NULL    Internal  PMS

DECISION: Why SERIAL and not a composite key?
The terms entity is an internal record — never referenced
externally by business-facing identifiers.
SERIAL is the correct choice for an entity that exists only
to be referenced by the product.

product_id          VARCHAR(15)   NOT NULL        Internal  PMS
                                  FK → product

effective_date      DATE          NOT NULL        Internal  PMS
expiry_date         DATE          NULLABLE        Internal  PMS

DECISION: Why is expiry_date nullable?
The current version of terms has no expiry date — it applies
until a new version takes effect. When a new version is created,
the previous row's expiry_date is set to the new version's
effective_date. NULL means "currently in effect".

DECISION: Why not a single is_current boolean instead?
Because multiple rows cannot all have is_current = TRUE,
but two rows can both have the same effective_date during
a migration or correction. The date range model is more robust.
Point-in-time queries are simpler: WHERE effective_date <= query_date
AND (expiry_date IS NULL OR expiry_date > query_date).

profit_rate_pct     NUMERIC(5,2)  NULLABLE        Internal  PMS / SSB

DECISION: Why nullable?
Current accounts and savings accounts may not have a profit rate.
The field is relevant for financing products and some deposit
products with profit sharing. NULL means "not applicable"
for this product type.

min_tenure_months   SMALLINT      NULLABLE        Internal  PMS
max_tenure_months   SMALLINT      NULLABLE        Internal  PMS
min_amount_sar      NUMERIC(18,2) NULLABLE        Internal  PMS
max_amount_sar      NUMERIC(18,2) NULLABLE        Internal  PMS
early_settle_fee    NUMERIC(5,2)  NULLABLE        Internal  PMS / SSB
────────────────────────────────────────────────────────────────────
```

---

### Entity 4: PRODUCT_PRICING

```
PRODUCT_PRICING
────────────────────────────────────────────────────────────────────
Attribute          Type          Constraint      PDPL      Source
────────────────────────────────────────────────────────────────────
pricing_id         SERIAL        PK, NOT NULL    Internal  PMS
product_id         VARCHAR(15)   NOT NULL        Internal  PMS
                                 FK → product
customer_segment   VARCHAR(30)   NOT NULL        Internal  PMS

DECISION: Why a segment-based pricing table and not a flat rate?
Al-Noor Bank prices the same Murabaha product differently
depending on who is buying it. A PREMIUM customer represents
a lower risk profile and a longer-term relationship — they get
a lower profit rate. A STANDARD customer gets the standard rate.
Embedding this in the product table would require a column per
segment — which breaks when a new segment is created. A separate
table requires one new row.

profit_rate_pct    NUMERIC(5,2)  NOT NULL        Internal  PMS

DECISION: Why NUMERIC(5,2) and not FLOAT?
A profit rate of 4.25% stored as FLOAT may be stored as
4.249999999... or 4.250000000001. Displayed on a customer
contract, this is wrong. NUMERIC(5,2) stores exactly 4.25.
For a regulated financial product, exact decimal storage
is not optional.

effective_date     DATE          NOT NULL        Internal  PMS
expiry_date        DATE          NULLABLE        Internal  PMS
────────────────────────────────────────────────────────────────────
```

---

## Step 7 — The Physical DDL

```sql
-- ============================================================
-- PRODUCT DOMAIN
-- Schema: product_domain
-- System of Record: Product Management System (PMS)
-- Business Data Owner: Head of Product Management
-- ============================================================

CREATE SCHEMA product_domain;
SET search_path TO product_domain;

-- ──────────────────────────────────────────────────────────
-- PRODUCT_CATEGORY
-- ──────────────────────────────────────────────────────────
CREATE TABLE product_domain.product_category (
    category_id    VARCHAR(10)   NOT NULL,
    category_name  VARCHAR(100)  NOT NULL,
    is_islamic     BOOLEAN       NOT NULL DEFAULT FALSE,
    description    TEXT,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_product_category
        PRIMARY KEY (category_id)
);

-- ──────────────────────────────────────────────────────────
-- PRODUCT
-- The ssb_approval_ref CHECK is the most important constraint
-- in the entire platform. See DECISION block in logical model.
-- ──────────────────────────────────────────────────────────
CREATE TABLE product_domain.product (
    product_id          VARCHAR(15)   NOT NULL,
    category_id         VARCHAR(10)   NOT NULL,
    product_name_en     VARCHAR(200)  NOT NULL,
    product_name_ar     VARCHAR(200)  NOT NULL,
    product_code        VARCHAR(20)   NOT NULL,
    is_active           BOOLEAN       NOT NULL DEFAULT TRUE,
    launch_date         DATE          NOT NULL,
    discontinue_date    DATE,
    min_age_years       SMALLINT      NOT NULL DEFAULT 18,
    min_balance_sar     NUMERIC(18,2) NOT NULL DEFAULT 0,
    max_exposure_sar    NUMERIC(18,2),           -- NULL = no limit
    currency            CHAR(3)       NOT NULL DEFAULT 'SAR',
    is_sharia_compliant BOOLEAN       NOT NULL,
    ssb_approval_ref    VARCHAR(50),             -- mandatory if Islamic
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_product
        PRIMARY KEY (product_id),
    CONSTRAINT uq_product_code
        UNIQUE (product_code),
    CONSTRAINT fk_product_category
        FOREIGN KEY (category_id)
        REFERENCES product_domain.product_category(category_id),
    -- Islamic governance enforced at DB level — cannot be bypassed
    CONSTRAINT chk_sharia_approval
        CHECK (
            is_sharia_compliant = FALSE
            OR ssb_approval_ref IS NOT NULL
        )
);

CREATE INDEX idx_product_active
    ON product_domain.product (is_active)
    WHERE is_active = TRUE;

CREATE INDEX idx_product_category
    ON product_domain.product (category_id, is_active);

-- ──────────────────────────────────────────────────────────
-- PRODUCT_TERMS (versioned — append only, never overwrite)
-- effective_date + expiry_date model for point-in-time queries
-- ──────────────────────────────────────────────────────────
CREATE TABLE product_domain.product_terms (
    terms_id          SERIAL        NOT NULL,
    product_id        VARCHAR(15)   NOT NULL,
    effective_date    DATE          NOT NULL,
    expiry_date       DATE,                     -- NULL = currently active
    profit_rate_pct   NUMERIC(5,2),             -- NULL for non-financing
    min_tenure_months SMALLINT,
    max_tenure_months SMALLINT,
    min_amount_sar    NUMERIC(18,2),
    max_amount_sar    NUMERIC(18,2),
    early_settle_fee  NUMERIC(5,2), -- % of outstanding — NULL if no fee
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_product_terms
        PRIMARY KEY (terms_id),
    CONSTRAINT fk_terms_product
        FOREIGN KEY (product_id)
        REFERENCES product_domain.product(product_id),
    CONSTRAINT chk_terms_dates
        CHECK (expiry_date IS NULL OR expiry_date > effective_date),
    CONSTRAINT chk_tenure_range
        CHECK (
            max_tenure_months IS NULL OR
            min_tenure_months IS NULL OR
            max_tenure_months >= min_tenure_months
        )
);

CREATE INDEX idx_terms_product_date
    ON product_domain.product_terms (product_id, effective_date DESC);

-- ──────────────────────────────────────────────────────────
-- PRODUCT_PRICING (by customer segment)
-- One row per product per segment per pricing period
-- ──────────────────────────────────────────────────────────
CREATE TABLE product_domain.product_pricing (
    pricing_id       SERIAL        NOT NULL,
    product_id       VARCHAR(15)   NOT NULL,
    customer_segment VARCHAR(30)   NOT NULL,
    profit_rate_pct  NUMERIC(5,2)  NOT NULL,
    effective_date   DATE          NOT NULL,
    expiry_date      DATE,                      -- NULL = currently active
    CONSTRAINT pk_pricing
        PRIMARY KEY (pricing_id),
    CONSTRAINT fk_pricing_product
        FOREIGN KEY (product_id)
        REFERENCES product_domain.product(product_id)
);

CREATE INDEX idx_pricing_product_segment
    ON product_domain.product_pricing (product_id, customer_segment);

-- ──────────────────────────────────────────────────────────
-- VIEW: active product catalogue with current terms
-- Used by the digital onboarding platform to show available products
-- and their current rates to each customer segment
-- ──────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW product_domain.v_active_product_catalogue AS
SELECT
    p.product_id,
    p.product_name_en,
    p.product_name_ar,
    p.product_code,
    pc.category_name,
    pc.is_islamic,
    p.is_sharia_compliant,
    p.ssb_approval_ref,
    p.min_age_years,
    p.min_balance_sar,
    pt.profit_rate_pct        AS current_profit_rate_pct,
    pt.min_tenure_months,
    pt.max_tenure_months,
    pt.min_amount_sar,
    pt.max_amount_sar
FROM product_domain.product p
JOIN product_domain.product_category pc
    ON p.category_id = pc.category_id
LEFT JOIN product_domain.product_terms pt
    ON  p.product_id     = pt.product_id
    AND pt.effective_date <= CURRENT_DATE
    AND (pt.expiry_date IS NULL OR pt.expiry_date > CURRENT_DATE)
WHERE p.is_active = TRUE;

-- ──────────────────────────────────────────────────────────
-- SAMPLE DATA
-- ──────────────────────────────────────────────────────────
INSERT INTO product_domain.product_category
    (category_id, category_name, is_islamic, description)
VALUES
    ('CAT_DEP', 'Islamic Deposits',  TRUE,
        'Sharia-compliant deposit products — SSB approval required'),
    ('CAT_FIN', 'Islamic Financing', TRUE,
        'Murabaha and Tawarruq financing products — SSB approval required'),
    ('CAT_CRD', 'Cards',             FALSE,
        'Debit and credit card products'),
    ('CAT_INV', 'Investment',        TRUE,
        'Sukuk and investment products — SSB approval required');

INSERT INTO product_domain.product
    (product_id, category_id, product_name_en, product_name_ar,
     product_code, is_active, launch_date,
     is_sharia_compliant, ssb_approval_ref,
     min_balance_sar, max_exposure_sar)
VALUES
    ('PROD_TAW_001', 'CAT_DEP',
     'Tawarruq Savings Account', 'حساب التورق',
     'ALN-TAW-001', TRUE, '2024-01-01',
     TRUE, 'SSB-2023-0041', 0, NULL),
    ('PROD_MRB_001', 'CAT_FIN',
     'Murabaha Personal Finance', 'تمويل شخصي مرابحة',
     'ALN-MRB-001', TRUE, '2024-01-01',
     TRUE, 'SSB-2023-0044', 0, 500000),
    ('PROD_MRB_002', 'CAT_FIN',
     'Murabaha Home Finance', 'تمويل عقاري مرابحة',
     'ALN-MRB-002', TRUE, '2024-01-01',
     TRUE, 'SSB-2023-0044', 0, 5000000);

INSERT INTO product_domain.product_terms
    (product_id, effective_date, expiry_date,
     profit_rate_pct, min_tenure_months, max_tenure_months,
     min_amount_sar, max_amount_sar)
VALUES
    ('PROD_MRB_001', '2024-01-01', NULL,
     4.50, 12, 60, 10000, 500000),
    ('PROD_MRB_002', '2024-01-01', NULL,
     4.25, 12, 300, 100000, 5000000);

INSERT INTO product_domain.product_pricing
    (product_id, customer_segment, profit_rate_pct, effective_date)
VALUES
    ('PROD_MRB_001', 'PREMIUM',  4.25, '2024-01-01'),
    ('PROD_MRB_001', 'STANDARD', 4.50, '2024-01-01'),
    ('PROD_MRB_002', 'PREMIUM',  3.99, '2024-01-01'),
    ('PROD_MRB_002', 'STANDARD', 4.25, '2024-01-01');
```

---

## Step 8 — Validate with a Business Scenario

**Scenario: A PREMIUM customer applies for Murabaha Home Finance.
The digital onboarding platform must show eligibility and the
applicable rate. Trace every table read.**

```
STEP 1: Platform loads available products for a PREMIUM customer

  READ → product_domain.v_active_product_catalogue
    WHERE is_active = TRUE
    AND is_sharia_compliant = TRUE
    AND min_age_years <= [customer's age]
    → Returns PROD_MRB_002 with current terms

  READ → product_domain.product_pricing
    WHERE product_id = 'PROD_MRB_002'
    AND customer_segment = 'PREMIUM'
    AND effective_date <= CURRENT_DATE
    AND (expiry_date IS NULL OR expiry_date > CURRENT_DATE)
    → Returns profit_rate_pct = 3.99

  RESULT: Platform shows Murabaha Home Finance at 3.99% to
          this PREMIUM customer.

────────────────────────────────────────────────────────────

STEP 2: Application submitted — Orders Domain picks up product_id

  READ → product_domain.product
    WHERE product_id = 'PROD_MRB_002'
    → Confirms is_active = TRUE and ssb_approval_ref is not NULL
    → Confirms is_sharia_compliant = TRUE (triggers SSB reference check)

  READ → product_domain.product_terms
    WHERE product_id = 'PROD_MRB_002'
    AND effective_date <= CURRENT_DATE
    AND (expiry_date IS NULL OR expiry_date > CURRENT_DATE)
    → Confirms requested_amount is within min/max range
    → Confirms requested_tenure is within min/max months

────────────────────────────────────────────────────────────

STEP 3: Contract generated on FULFILLED — terms snapshot

  READ → product_domain.product_terms
    WHERE product_id = 'PROD_MRB_002'
    AND effective_date <= application_date
    AND (expiry_date IS NULL OR expiry_date > application_date)
    → The terms active AT APPLICATION DATE are used for the contract
    → Even if rates change after signing, this contract uses
      the terms in effect at the moment the application was made

  NOTE: This point-in-time read is only possible because terms are
        versioned with effective_date and expiry_date.
        If terms were stored as a single overwriteable row,
        this read would return the current (wrong) terms.
```

**Now ask: what if someone tries to create an Islamic product without an SSB reference?**

```
STEP (attempt): Product Manager creates a new Murabaha product
without the SSB Board reference (not yet approved)

  WRITE → product_domain.product
    INSERT (product_id = 'PROD_MRB_003',
            is_sharia_compliant = TRUE,
            ssb_approval_ref = NULL)

  RESULT: ERROR — violates constraint chk_sharia_approval
    "new row for relation 'product' violates check constraint
     'chk_sharia_approval'"

  The product cannot be created. The SSB reference is mandatory.
  No application can be taken for a product that does not exist.
  No contract can be signed under an unapproved Islamic product.
  The governance requirement is enforced at the database level.
  It cannot be bypassed by application code, a migration script,
  or a direct SQL session.
```

---

> **The Product Domain is now complete.**
>
> Step 1 established the domain's purpose.
> Step 2 derived the schema from business questions.
> Step 3 found the entities.
> Step 4 established the relationships — and noted that
> this domain is referenced by others, not the other way around.
> Step 5 produced the conceptual model.
> Step 6 documented every attribute with its rationale.
> Step 7 produced the physical DDL.
> Step 8 validated against two scenarios — including the
> invalid state that the CHECK constraint prevents.
>
> Apply the same method to Orders and Inventory.
> The process is identical. The domain-specific decisions differ.

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*
-e 

---


# The Retail Mini-Project — Orders Domain
## How to Read the Requirements, Find the Schema, and Build It End to End
### Al-Noor Bank | Digital Retail Banking Platform

---

> **How to use this guide.**
>
> This guide follows the same eight-step process used for the
> Payments, Customer, and Product domains. Read those first.
>
> The Orders Domain is the most operationally complex domain
> in this architecture. It connects to every other domain.
> It produces the audit trail that SAMA examiners ask for first.
> And it is the domain where the most expensive design mistakes
> are made — usually by collapsing the lifecycle into too few
> states, or by failing to create the history table.
>
> Read every step carefully. The immutability decision in Step 7
> is worth more attention than any other single decision
> in this domain.

---

## Step 1 — Understand the Domain's Purpose

**The question:** What problem does the Orders Domain exist to solve?

**The answer:** To manage the complete lifecycle of every product
application — from the moment a customer submits to the moment
the product becomes active — and to preserve an immutable record
of every decision made along the way.

**Why "immutable" is the most important word in this domain:**

```
WITHOUT an immutable audit trail:

  SAMA examiner: "Show me every status change for application
  APP-2025-0847 — who approved it, when, and on what basis."

  Bank: "The application was approved on 15 March."
  SAMA: "By whom? At what time? Was AML cleared first?"
  Bank: "We... do not have that level of detail."
  Result: Supervisory finding. Schema migration on a live
          production system with 400,000 active applications.

WITH an immutable audit trail:

  Bank: "Here is every status change, every timestamp, every
  officer ID, every compliance check result — all in the
  database, all permanent, all auditable."
  Result: Clean examination.
```

**The domain boundary:**

The Orders Domain owns the application lifecycle and the
financing contract. It does not own:
- The customer applying — that is Customer Domain
- The product being applied for — that is Product Domain
- How many can be approved — that is Inventory Domain
- The payments that follow — that is Payments Domain

It references all four. It is the domain that brings them together.

---

## Step 2 — Identify the Business Questions

```
OPERATIONS / ONBOARDING TEAM:
→ How many applications are currently in UNDER_REVIEW status?
→ Which applications have been in UNDER_REVIEW for more than
  5 business days? (SLA breach)
→ Which officer has the highest application backlog today?
→ What was the average time from SUBMITTED to APPROVED
  this month?

COMPLIANCE TEAM:
→ Show me every application where AML was flagged.
→ Which applications were approved despite an AML flag?
→ Show me the full status history for APP-2025-0847 —
  every transition, every timestamp, every officer.
→ Which applications were approved without Nafath verification?

SAMA REPORTING:
→ How many Murabaha applications were received, approved,
  and rejected in Q1 2025?
→ What is the average SIMAH score of approved vs rejected
  Murabaha applications?
→ What is the current NPF ratio? (instalments overdue > 90 days)
→ What is the total outstanding Murabaha exposure?

RISK MANAGEMENT:
→ What is the average approved amount per product type?
→ What is the distribution of approved tenure lengths?
→ How many contracts are within 6 months of maturity?
```

Now map every question to a column or relationship:

```
"How many applications are in UNDER_REVIEW?"
→ status column on product_application
→ INDEX on (status) — queried constantly

"Which applications have been in UNDER_REVIEW > 5 days?"
→ status column AND application_date column
→ Better: query application_status_history for UNDER_REVIEW
  transition timestamp — gives exact time in that state

"Full status history for APP-2025-0847"
→ application_status_history table — one row per transition
→ Columns: old_status, new_status, changed_at, changed_by, change_reason
→ Must be queryable by application_id in order of changed_at

"Which applications approved without Nafath verification?"
→ nafath_verified BOOLEAN on product_application
→ Filter: status = 'APPROVED' AND nafath_verified = FALSE
→ Should return zero rows — if it doesn't, it is a compliance gap

"NPF ratio — instalments overdue > 90 days"
→ murabaha_schedule table — one row per instalment
→ WHERE status = 'OVERDUE' AND due_date < CURRENT_DATE - 90 DAYS
→ NPF numerator / total portfolio = ratio

"Total outstanding Murabaha exposure"
→ murabaha_contract table
→ SUM(total_sale_price) WHERE status = 'ACTIVE'
```

---

## Step 3 — Find the Entities

```
PRODUCT_APPLICATION
The application record. One per customer per product request.
Contains the compliance gate results — AML, Nafath, SIMAH.
Contains the decision — who approved it, when, and why rejected.
This is the core entity. Everything else traces back to it.

APPLICATION_STATUS_HISTORY
Every status transition recorded as a new row.
Never updated. Never deleted.
SAMA requires the complete trail — not just the final state.
This is a separate entity, not a column on the application.

MURABAHA_CONTRACT
Created on FULFILLED for financing applications.
Captures the agreed terms at the moment of signing —
asset cost, profit amount, total sale price.
These cannot change after signing (Islamic finance principle).
The total_sale_price CHECK constraint enforces this.

MURABAHA_SCHEDULE
One row per instalment of the repayment schedule.
A 20-year Murabaha contract generates 240 rows.
This is the entity that drives SAMA NPF reporting.
Without it, overdue analysis requires recalculation
from the contract terms — which is slower and error-prone.
```

**What is NOT in this list:**

```
PRODUCT — lives in the Product Domain.
  Orders references it. It does not own it.

CUSTOMER — lives in the Customer Domain.
  Orders references it. It does not own it.

ACCOUNT — lives in the Customer Domain.
  Created as a consequence of FULFILLED, but owned by Customer.

PRODUCT_QUOTA — lives in the Inventory Domain.
  Updated as a consequence of FULFILLED, but owned by Inventory.
```

---

## Step 4 — Establish the Relationships

```
PRODUCT_APPLICATION ──── has status history ──► APPLICATION_STATUS_HISTORY
(one application, many status rows — append-only)

PRODUCT_APPLICATION ──── references ──────────► CUSTOMER
(Customer Domain — FK only, Customer Domain owns the record)

PRODUCT_APPLICATION ──── references ──────────► PRODUCT
(Product Domain — FK only, Product Domain owns the record)

PRODUCT_APPLICATION ──── results in ──────────► MURABAHA_CONTRACT
(on FULFILLED — one application, at most one contract)

MURABAHA_CONTRACT ──── generates ─────────────► MURABAHA_SCHEDULE
(one contract, many instalment rows — one per month)

MURABAHA_CONTRACT ──── references ────────────► ACCOUNT
(Customer Domain — FK only, Account created on FULFILLED)
```

**The compliance gates that must ALL be satisfied before APPROVED:**

```
product_application.aml_check_status  = 'CLEAR'
product_application.nafath_verified    = TRUE
product_application.credit_bureau_score ≥ threshold  (financing only)

All three must be TRUE before the application can proceed
to APPROVED status. These are checked by the application layer.
The schema records the state. It does not enforce the sequence
of checks — that is the application's responsibility.
What the schema DOES enforce: the values must be valid.
What it does NOT enforce: the order in which they are set.
```

---

## Step 5 — The Conceptual Model

```
CONCEPTUAL MODEL — ORDERS DOMAIN

┌─ CUSTOMER DOMAIN ─────────┐    ┌─ PRODUCT DOMAIN ─────────┐
│                           │    │                          │
│   ┌────────────┐          │    │   ┌─────────────┐        │
│   │  CUSTOMER  │          │    │   │   PRODUCT   │        │
│   └─────┬──────┘          │    │   └──────┬──────┘        │
│         │                 │    │          │               │
└─────────┼─────────────────┘    └──────────┼───────────────┘
          │ submits                          │ applied for
          │                                  │
          ▼                                  ▼
┌─ ORDERS DOMAIN ──────────────────────────────────────────────────┐
│                                                                  │
│          ┌──────────────────────────────────┐                   │
│          │         PRODUCT_APPLICATION       │                   │
│          │                                  │                   │
│          │  AML status · Nafath · SIMAH      │                   │
│          │  Decision · Officer · Reason      │                   │
│          └───────────────┬──────────────────┘                   │
│                          │                                       │
│          ┌───────────────┴──────────────┐                        │
│          │                              │                        │
│          │ has history of               │ results in (on FULFILLED)
│          ▼                              ▼                        │
│  ┌────────────────────┐   ┌─────────────────────────────┐       │
│  │ APPLICATION_STATUS │   │     MURABAHA_CONTRACT        │       │
│  │ _HISTORY           │   │                             │       │
│  │                    │   │  total = cost + profit       │       │
│  │ append-only        │   │  enforced by CHECK           │       │
│  │ immutable          │   │                             │       │
│  │                    │   └──────────────┬──────────────┘       │
│  └────────────────────┘                  │                       │
│                                          │ generates             │
│                                          ▼                       │
│                               ┌──────────────────────┐           │
│                               │   MURABAHA_SCHEDULE  │           │
│                               │                      │           │
│                               │  one row per month   │           │
│                               │  drives NPF query    │           │
│                               └──────────────────────┘           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

ON FULFILLED — creates in other domains:
→ Customer Domain: retail.account  (new account)
→ Customer Domain: retail.customer_account  (bridge row)
→ Inventory Domain: UPDATE product_quota  (quota consumed)
   ↑ This UPDATE must be in the same transaction as FULFILLED
```

**What to check before moving on:**

```
□ Is APPLICATION_STATUS_HISTORY a separate entity —
  not just a column on the application?
□ Is the immutability of the history table noted?
□ Is the FK to Customer Domain shown as a reference,
  not as a Customer entity inside the Orders Domain box?
□ Is MURABAHA_SCHEDULE a separate entity —
  not stored as JSON on the contract?
□ Are the three compliance gates visible in the diagram?
□ Is the cross-domain impact on FULFILLED visible?
```

---

## Step 6 — The Logical Model

---

### Entity 1: PRODUCT_APPLICATION

```
PRODUCT_APPLICATION
────────────────────────────────────────────────────────────────────
Attribute                Type          Constraint      PDPL    Source
────────────────────────────────────────────────────────────────────
application_id           VARCHAR(20)   PK, NOT NULL    Internal  Onboarding Platform

DECISION: Why VARCHAR(20) and not UUID?
The application_id is a business-facing identifier.
SAMA examiners, compliance officers, and customers all reference
it in formal correspondence — APP-2025-0042.
This format is human-readable, meaningful, and auditable.
UUID would make verbal communication of an application
reference impossible.

customer_id              CHAR(10)      NOT NULL        Internal  Customer Domain
                                       FK → customer

product_id               VARCHAR(15)   NOT NULL        Internal  Product Domain
                                       FK → product

application_date         DATE          NOT NULL        Internal  Onboarding Platform
                                       DEFAULT CURRENT_DATE

channel                  VARCHAR(20)   NOT NULL        Internal  Onboarding Platform
                                       CHECK(MOBILE, WEB, BRANCH, API)

status                   VARCHAR(20)   NOT NULL        Internal  Onboarding Platform
                                       DEFAULT 'SUBMITTED'
                                       CHECK(...)

DECISION: Why seven specific status values in a CHECK constraint?
SUBMITTED, UNDER_REVIEW, PENDING_DOCS, APPROVED, REJECTED,
FULFILLED, WITHDRAWN — these are the only valid states.
Any value outside this list represents a system error.
A CHECK constraint means the database rejects invalid values
regardless of where the insert comes from.
A developer cannot accidentally set status = 'PROCESSING'
(a payment concept — not an application concept).

requested_amount_sar     NUMERIC(18,2) NULLABLE        Internal  Customer input

DECISION: Why nullable?
Current account and savings account applications do not have
a requested amount — there is no financing involved.
Only financing applications carry a requested amount.
NULL correctly represents "not applicable for this product type".

requested_tenure_months  SMALLINT      NULLABLE        Internal  Customer input
purpose_of_finance       VARCHAR(100)  NULLABLE        Internal  Customer input
decision_date            DATE          NULLABLE        Internal  Onboarding Platform
decision_by              VARCHAR(100)  NULLABLE        Internal  Onboarding Platform

DECISION: Why store decision_by?
SAMA examiners ask who made the approval decision.
"The system" is not an acceptable answer.
The column must identify either the officer (OFFICER_A42)
or the automated system (AUTO_CREDIT_ENGINE_v3).
Both are auditable. Neither is anonymous.

rejection_reason         VARCHAR(255)  NULLABLE        Internal  Onboarding Platform

DECISION: Why nullable?
Mandatory for REJECTED status (enforced by application layer).
Not applicable for other statuses.
NULL does not mean the reason is unknown — it means
this application was not rejected and no reason is needed.

approved_amount_sar      NUMERIC(18,2) NULLABLE        Internal  Onboarding Platform
approved_profit_rate     NUMERIC(5,2)  NULLABLE        Internal  Onboarding Platform

aml_check_status         VARCHAR(15)   NULLABLE        Internal  AML System
                                       CHECK(CLEAR, FLAGGED, PENDING)

DECISION: Why three states for AML — not just a boolean?
CLEAR means the check ran and found no issue.
FLAGGED means the check ran and found a match.
PENDING means the check has not yet completed.
A boolean TRUE/FALSE cannot represent PENDING.
And NULL cannot be used for "not yet run" because NULL is
ambiguous — did the check not run, or did it run and return null?

credit_bureau_score      SMALLINT      NULLABLE        Internal  SIMAH
                                       CHECK(300-900)

DECISION: Why the 300–900 range CHECK?
Saudi SIMAH credit scores run from 300 to 900.
Any value outside this range represents a system error
or data corruption — not a valid score.
The CHECK constraint makes invalid scores impossible to store.

nafath_verified          BOOLEAN       NOT NULL        Internal  Nafath
                                       DEFAULT FALSE
────────────────────────────────────────────────────────────────────
```

---

### Entity 2: APPLICATION_STATUS_HISTORY

```
APPLICATION_STATUS_HISTORY  (append-only — immutable)
────────────────────────────────────────────────────────────────────
Attribute         Type          Constraint      PDPL      Source
────────────────────────────────────────────────────────────────────
history_id        BIGSERIAL     PK, NOT NULL    Internal  System

DECISION: Why BIGSERIAL and not SERIAL?
SERIAL has a maximum of ~2.1 billion. A bank with 100,000
applications per month, each going through 5–6 status transitions,
generates 6–7 million rows per month. BIGSERIAL (max ~9.2 quintillion)
never overflows. SERIAL could in ~17 years at that volume.

application_id    VARCHAR(20)   NOT NULL        Internal  Onboarding Platform
                                FK → product_application

old_status        VARCHAR(20)   NULLABLE        Internal  System

DECISION: Why is old_status nullable?
The first row for any application records the transition from
nothing to SUBMITTED. There is no previous status.
NULL correctly represents "this is the first state this
application has ever been in."

new_status        VARCHAR(20)   NOT NULL        Internal  System
changed_at        TIMESTAMPTZ   NOT NULL        Internal  System
                                DEFAULT NOW()

DECISION: Why TIMESTAMPTZ and not TIMESTAMP?
Saudi Arabia operates on AST (UTC+3). SAMA examinations
reference timestamps. If timestamps are stored without timezone
and the server is ever moved or queried from a different timezone,
every timestamp in the audit trail shifts. TIMESTAMPTZ stores
the absolute moment in time — independent of server location.

changed_by        VARCHAR(100)  NOT NULL        Internal  System / Officer

DECISION: What value goes here?
Either an officer identifier (OFFICER_A42, RISK_MGR_B17)
or a system identifier (AUTO_AML_ENGINE_v3, NAFATH_CALLBACK).
The column must always be populated.
Anonymous transitions are not acceptable in a regulated audit trail.

change_reason     VARCHAR(255)  NULLABLE        Internal  Officer / System

DECISION: When is this populated?
Mandatory for REJECTED (application layer enforces this).
Optional for routine transitions — SUBMITTED → UNDER_REVIEW
does not require a reason.
NULL does not mean "unknown reason" — it means "no reason required
for this transition type."

IMPORTANT: No UPDATE or DELETE is ever permitted on this table.
An immutability trigger enforces this at the database level.
────────────────────────────────────────────────────────────────────
```

---

### Entity 3: MURABAHA_CONTRACT

```
MURABAHA_CONTRACT
────────────────────────────────────────────────────────────────────
Attribute          Type          Constraint      PDPL        Source
────────────────────────────────────────────────────────────────────
contract_id        CHAR(15)      PK, NOT NULL    Internal    Onboarding Platform
application_id     VARCHAR(20)   NULLABLE        Internal    Onboarding Platform
                                 FK → product_application

DECISION: Why nullable?
In rare migration scenarios, a historical contract may exist
without a corresponding digital application. NULL allows these
to be imported without fabricating an application record.
For all new contracts on this platform, the FK is populated.

customer_id        CHAR(10)      NOT NULL        Internal    Customer Domain
                                 FK → customer
account_id         CHAR(16)      NOT NULL        Internal    Customer Domain
                                 FK → account

asset_cost_sar     NUMERIC(18,2) NOT NULL        🔒 Restricted  Onboarding Platform

DECISION: Why PDPL Restricted for financial terms?
Under PDPL, data that reveals the financial circumstances of
an individual is sensitive personal data.
The asset cost of a home finance contract reveals the value
of the property being financed and the customer's financial
capacity. Restricted classification requires encryption at rest
and access restricted to authorised roles only.
Not all financial data is Restricted — product profit rates
are public. The specific contract terms of an individual
customer are personal and Restricted.

profit_amount_sar  NUMERIC(18,2) NOT NULL        🔒 Restricted  Onboarding Platform
total_sale_price   NUMERIC(18,2) NOT NULL        🔒 Restricted  Onboarding Platform

DECISION: The CHECK constraint on total_sale_price.
CHECK (total_sale_price = asset_cost_sar + profit_amount_sar)
This enforces the Islamic finance principle at the database level:
the total price a customer pays equals the asset cost plus
the disclosed profit margin. These cannot drift apart.
An application bug cannot silently change the profit margin
after the contract is created — the constraint rejects it.
In conventional lending, a bank can restructure and change
the rate. In Murabaha, the profit is fixed and disclosed
at inception. The schema enforces this.

ssb_approval_ref   VARCHAR(50)   NOT NULL        Internal    SSB

DECISION: Why NOT NULL here as well as on product?
The product carries the SSB approval reference for the
product category. This column carries the reference on
the individual contract — linking this specific contract
to the SSB approval that authorises it.
Both are required. A contract without an SSB reference cannot
be proven to have been issued under an approved product.

disbursement_date  DATE          NOT NULL        Internal    CBS
maturity_date      DATE          NOT NULL        Internal    Onboarding Platform
tenure_months      SMALLINT      NOT NULL        Internal    Onboarding Platform
status             VARCHAR(15)   NOT NULL        Internal    Onboarding Platform
                                 DEFAULT 'ACTIVE'
                                 CHECK(ACTIVE, SETTLED,
                                       DEFAULTED, SETTLED_EARLY)
────────────────────────────────────────────────────────────────────
```

---

### Entity 4: MURABAHA_SCHEDULE

```
MURABAHA_SCHEDULE
────────────────────────────────────────────────────────────────────
Attribute          Type          Constraint      PDPL      Source
────────────────────────────────────────────────────────────────────
schedule_id        SERIAL        PK, NOT NULL    Internal  Onboarding Platform
contract_id        CHAR(15)      NOT NULL        Internal  Onboarding Platform
                                 FK → murabaha_contract
instalment_no      INTEGER       NOT NULL        Internal  Onboarding Platform

instalment_sar     NUMERIC(18,2) NOT NULL        Internal  Onboarding Platform
principal_portion  NUMERIC(18,2) NOT NULL        Internal  Onboarding Platform
profit_portion     NUMERIC(18,2) NOT NULL        Internal  Onboarding Platform

DECISION: Why store principal_portion and profit_portion separately?
In Murabaha financing, the profit component is fixed and disclosed.
A SAMA examiner or a customer can ask: "Of the SAR 2,437.50
I paid this month, how much was principal repayment and how much
was the bank's profit?"
Calculating this at query time from the contract terms is possible —
but it requires recomputing the amortisation schedule on demand.
For a SAMA NPF query running across 5,000 active contracts,
that recalculation is expensive and error-prone.
Storing the split at generation time — and enforcing the sum
with a CHECK constraint — gives direct query access to the
audit-ready breakdown.

DECISION: The CHECK constraint on instalment components.
CHECK (instalment_sar = principal_portion + profit_portion)
Same principle as the contract-level constraint.
The three monetary values must always be consistent.
The constraint enforces this on every row, every INSERT.

paid_amount        NUMERIC(18,2) NULLABLE        Internal  Payment System
paid_date          DATE          NULLABLE        Internal  Payment System

DECISION: Why nullable?
The schedule row is created before any payment is made.
NULL means "not yet paid". A non-null value means "paid".
The paid_date and paid_amount are populated when the
instalment payment is processed by the Payments Domain.

status             VARCHAR(15)   NOT NULL        Internal  Payment System / System
                                 DEFAULT 'PENDING'
                                 CHECK(PENDING, PAID,
                                       OVERDUE, SETTLED_EARLY)

DECISION: How does OVERDUE status get set?
A nightly job runs the following:
  UPDATE murabaha_schedule
  SET    status = 'OVERDUE'
  WHERE  status = 'PENDING'
  AND    due_date < CURRENT_DATE
  RETURNING contract_id, schedule_id, due_date;
The RETURNING clause captures the list for the compliance
team's morning review. The status update is authoritative —
all NPF queries filter on status = 'OVERDUE'.
────────────────────────────────────────────────────────────────────
```

---

## Step 7 — The Physical DDL

```sql
-- ============================================================
-- ORDERS DOMAIN
-- Schema: orders_domain
-- System of Record: Digital Onboarding Platform
-- Business Data Owner: Head of Digital Onboarding / Operations
-- ============================================================

CREATE SCHEMA orders_domain;

-- ──────────────────────────────────────────────────────────
-- PRODUCT_APPLICATION
-- Cross-domain FKs:
--   customer_id → retail.customer (Customer Domain)
--   product_id  → product_domain.product (Product Domain)
-- ──────────────────────────────────────────────────────────
CREATE TABLE orders_domain.product_application (
    application_id           VARCHAR(20)   NOT NULL,
    customer_id              CHAR(10)      NOT NULL,
    product_id               VARCHAR(15)   NOT NULL,
    application_date         DATE          NOT NULL DEFAULT CURRENT_DATE,
    channel                  VARCHAR(20)   NOT NULL
        CHECK (channel IN ('MOBILE','WEB','BRANCH','API')),
    status                   VARCHAR(20)   NOT NULL DEFAULT 'SUBMITTED'
        CHECK (status IN (
            'SUBMITTED','UNDER_REVIEW','PENDING_DOCS',
            'APPROVED','REJECTED','FULFILLED','WITHDRAWN')),
    requested_amount_sar     NUMERIC(18,2),
    requested_tenure_months  SMALLINT,
    purpose_of_finance       VARCHAR(100),
    decision_date            DATE,
    decision_by              VARCHAR(100),
    rejection_reason         VARCHAR(255),
    approved_amount_sar      NUMERIC(18,2),
    approved_profit_rate     NUMERIC(5,2),
    aml_check_status         VARCHAR(15)
        CHECK (aml_check_status IN ('CLEAR','FLAGGED','PENDING')),
    credit_bureau_score      SMALLINT
        CHECK (credit_bureau_score BETWEEN 300 AND 900),
    nafath_verified          BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at               TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_application
        PRIMARY KEY (application_id),
    -- Cross-domain FK: Orders → Customer Domain
    CONSTRAINT fk_app_customer
        FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id),
    -- Cross-domain FK: Orders → Product Domain
    CONSTRAINT fk_app_product
        FOREIGN KEY (product_id)
        REFERENCES product_domain.product(product_id)
);

CREATE INDEX idx_app_status
    ON orders_domain.product_application (status, application_date DESC);
CREATE INDEX idx_app_customer
    ON orders_domain.product_application (customer_id, application_date DESC);
CREATE INDEX idx_app_product
    ON orders_domain.product_application (product_id, application_date DESC);

-- ──────────────────────────────────────────────────────────
-- APPLICATION_STATUS_HISTORY
-- Append-only. An immutability trigger enforces this.
-- No row may ever be updated or deleted.
-- ──────────────────────────────────────────────────────────
CREATE TABLE orders_domain.application_status_history (
    history_id     BIGSERIAL    NOT NULL,
    application_id VARCHAR(20)  NOT NULL,
    old_status     VARCHAR(20),            -- NULL for first transition
    new_status     VARCHAR(20)  NOT NULL,
    changed_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    changed_by     VARCHAR(100) NOT NULL,  -- officer ID or system name
    change_reason  VARCHAR(255),           -- mandatory for REJECTED
    CONSTRAINT pk_app_history
        PRIMARY KEY (history_id),
    CONSTRAINT fk_hist_application
        FOREIGN KEY (application_id)
        REFERENCES orders_domain.product_application(application_id)
);

CREATE INDEX idx_app_history_app
    ON orders_domain.application_status_history
    (application_id, changed_at DESC);

-- Immutability trigger — the audit trail cannot be altered
CREATE OR REPLACE FUNCTION orders_domain.prevent_history_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'application_status_history is immutable. '
        'Rows cannot be % d. application_id: %',
        TG_OP, OLD.application_id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_app_history_immutable
    BEFORE UPDATE OR DELETE
    ON orders_domain.application_status_history
    FOR EACH ROW
    EXECUTE FUNCTION orders_domain.prevent_history_modification();

-- ──────────────────────────────────────────────────────────
-- MURABAHA_CONTRACT
-- Cross-domain FKs:
--   customer_id    → retail.customer (Customer Domain)
--   account_id     → retail.account  (Customer Domain)
--   application_id → orders_domain.product_application
--
-- The total_sale_price CHECK enforces the Islamic finance
-- principle that profit is fixed and disclosed at inception.
-- ──────────────────────────────────────────────────────────
CREATE TABLE orders_domain.murabaha_contract (
    contract_id        CHAR(15)      NOT NULL,
    application_id     VARCHAR(20),               -- nullable (see logical model)
    customer_id        CHAR(10)      NOT NULL,     -- 🔒 PDPL Restricted context
    account_id         CHAR(16)      NOT NULL,
    asset_cost_sar     NUMERIC(18,2) NOT NULL,     -- 🔒 PDPL Restricted
    profit_amount_sar  NUMERIC(18,2) NOT NULL,     -- 🔒 PDPL Restricted
    total_sale_price   NUMERIC(18,2) NOT NULL,     -- 🔒 PDPL Restricted
    ssb_approval_ref   VARCHAR(50)   NOT NULL,
    disbursement_date  DATE          NOT NULL,
    maturity_date      DATE          NOT NULL,
    tenure_months      SMALLINT      NOT NULL,
    status             VARCHAR(15)   NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','SETTLED','DEFAULTED','SETTLED_EARLY')),
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_murabaha
        PRIMARY KEY (contract_id),
    CONSTRAINT fk_mrb_application
        FOREIGN KEY (application_id)
        REFERENCES orders_domain.product_application(application_id),
    CONSTRAINT fk_mrb_customer
        FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id),
    CONSTRAINT fk_mrb_account
        FOREIGN KEY (account_id)
        REFERENCES retail.account(account_id),
    -- Islamic finance principle: profit fixed and disclosed at inception
    CONSTRAINT chk_mrb_total
        CHECK (total_sale_price = asset_cost_sar + profit_amount_sar)
);

CREATE INDEX idx_mrb_customer
    ON orders_domain.murabaha_contract (customer_id, status);
CREATE INDEX idx_mrb_status
    ON orders_domain.murabaha_contract (status, maturity_date);

-- ──────────────────────────────────────────────────────────
-- MURABAHA_SCHEDULE
-- One row per instalment. 240 rows for a 20-year contract.
-- The status column drives SAMA NPF reporting.
-- Nightly job: UPDATE status = OVERDUE WHERE due_date < TODAY
-- ──────────────────────────────────────────────────────────
CREATE TABLE orders_domain.murabaha_schedule (
    schedule_id        SERIAL        NOT NULL,
    contract_id        CHAR(15)      NOT NULL,
    instalment_no      INTEGER       NOT NULL,
    due_date           DATE          NOT NULL,
    instalment_sar     NUMERIC(18,2) NOT NULL,
    principal_portion  NUMERIC(18,2) NOT NULL,
    profit_portion     NUMERIC(18,2) NOT NULL,
    paid_amount        NUMERIC(18,2),              -- NULL = not yet paid
    paid_date          DATE,                       -- NULL = not yet paid
    status             VARCHAR(15)   NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','PAID','OVERDUE','SETTLED_EARLY')),
    CONSTRAINT pk_schedule
        PRIMARY KEY (schedule_id),
    CONSTRAINT fk_schedule_contract
        FOREIGN KEY (contract_id)
        REFERENCES orders_domain.murabaha_contract(contract_id),
    -- Instalment components must always sum correctly
    CONSTRAINT chk_schedule_sum
        CHECK (instalment_sar = principal_portion + profit_portion)
);

CREATE INDEX idx_schedule_contract
    ON orders_domain.murabaha_schedule (contract_id, instalment_no);
CREATE INDEX idx_schedule_due
    ON orders_domain.murabaha_schedule (due_date, status)
    WHERE status IN ('PENDING','OVERDUE');

-- ──────────────────────────────────────────────────────────
-- SAMA NPF REPORTING VIEW
-- Non-Performing Finance ratio: overdue > 90 days
-- Queried for monthly SAMA regulatory submission
-- ──────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW orders_domain.v_npf_exposure AS
SELECT
    mc.contract_id,
    mc.customer_id,
    mc.total_sale_price,
    mc.disbursement_date,
    mc.maturity_date,
    COUNT(*) FILTER (
        WHERE ms.status = 'OVERDUE'
        AND   ms.due_date < CURRENT_DATE - INTERVAL '90 days'
    ) AS instalments_overdue_90d,
    SUM(ms.instalment_sar) FILTER (
        WHERE ms.status = 'OVERDUE'
        AND   ms.due_date < CURRENT_DATE - INTERVAL '90 days'
    ) AS overdue_amount_sar_90d,
    SUM(ms.instalment_sar) FILTER (
        WHERE ms.status = 'OVERDUE'
    ) AS total_overdue_sar
FROM orders_domain.murabaha_contract mc
JOIN orders_domain.murabaha_schedule ms
    ON mc.contract_id = ms.contract_id
WHERE mc.status = 'ACTIVE'
GROUP BY
    mc.contract_id, mc.customer_id,
    mc.total_sale_price, mc.disbursement_date, mc.maturity_date
HAVING COUNT(*) FILTER (
    WHERE ms.status = 'OVERDUE'
    AND   ms.due_date < CURRENT_DATE - INTERVAL '90 days'
) > 0;

-- ──────────────────────────────────────────────────────────
-- COMPLIANCE AUDIT QUERY — SAMA supervisory examination
-- "Show the full trail for APP-2025-0847"
-- This is the query SAMA asks for. Ensure it returns results.
-- ──────────────────────────────────────────────────────────
-- SELECT
--     pa.application_id,
--     pa.customer_id,
--     pa.product_id,
--     pa.aml_check_status,
--     pa.nafath_verified,
--     pa.credit_bureau_score,
--     pa.approved_amount_sar,
--     pa.approved_profit_rate,
--     pa.decision_by,
--     ash.old_status,
--     ash.new_status,
--     ash.changed_at,
--     ash.changed_by,
--     ash.change_reason
-- FROM orders_domain.product_application pa
-- JOIN orders_domain.application_status_history ash
--     ON pa.application_id = ash.application_id
-- WHERE pa.application_id = 'APP-2025-0847'
-- ORDER BY ash.changed_at ASC;
```

---

## Step 8 — Validate with a Business Scenario

**Scenario: A Murabaha Home Finance application is submitted,
approved, and fulfilled. Trace every table written.**

```
STEP 1: Application submitted

  WRITE → orders_domain.product_application
    application_id:     'APP-2025-0042'
    customer_id:        'C000000001'
    product_id:         'PROD_MRB_002'
    status:             'SUBMITTED'
    nafath_verified:    FALSE
    aml_check_status:   NULL
    credit_bureau_score: NULL

  WRITE → orders_domain.application_status_history
    old_status:  NULL
    new_status:  'SUBMITTED'
    changed_by:  'MOBILE_APP_v4.1'
    changed_at:  NOW()

────────────────────────────────────────────────────────────

STEP 2: AML screening runs (Payments Domain logs this)

  WRITE → payments.external_api_log
    service_name:    'OFAC'
    request_ref:     'APP-2025-0042'
    response_status: 'SUCCESS'
    response_time_ms: 312

  UPDATE → orders_domain.product_application
    aml_check_status: 'CLEAR'

────────────────────────────────────────────────────────────

STEP 3: Nafath eKYC verification

  WRITE → payments.external_api_log
    service_name:    'NAFATH'
    request_ref:     'APP-2025-0042'

  UPDATE → retail.individual_customer
    nafath_verified:    TRUE
    nafath_verified_at: NOW()

  UPDATE → orders_domain.product_application
    nafath_verified: TRUE

────────────────────────────────────────────────────────────

STEP 4: SIMAH credit check

  WRITE → payments.external_api_log
    service_name: 'SIMAH'
    request_ref:  'APP-2025-0042'

  UPDATE → orders_domain.product_application
    credit_bureau_score: 720

  UPDATE → orders_domain.product_application
    status: 'UNDER_REVIEW'

  WRITE → orders_domain.application_status_history
    old_status: 'SUBMITTED'
    new_status: 'UNDER_REVIEW'
    changed_by: 'AUTO_COMPLIANCE_ENGINE_v3'

────────────────────────────────────────────────────────────

STEP 5: Officer reviews and approves

  UPDATE → orders_domain.product_application
    status:               'APPROVED'
    approved_amount_sar:   500000.00
    approved_profit_rate:  3.99
    decision_date:         CURRENT_DATE
    decision_by:           'OFFICER_A42'

  WRITE → orders_domain.application_status_history
    old_status:  'UNDER_REVIEW'
    new_status:  'APPROVED'
    changed_by:  'OFFICER_A42'

────────────────────────────────────────────────────────────

STEP 6: FULFILLED — atomic transaction across three domains

  BEGIN;

    UPDATE → orders_domain.product_application
      status: 'FULFILLED'

    WRITE → orders_domain.application_status_history
      old_status: 'APPROVED'
      new_status: 'FULFILLED'
      changed_by: 'ONBOARDING_PLATFORM_v2'

    WRITE → orders_domain.murabaha_contract
      contract_id:        'MRB-2025-0042'
      customer_id:        'C000000001'
      asset_cost_sar:      500000.00
      profit_amount_sar:    85000.00   -- 3.99% over 20 years
      total_sale_price:    585000.00   -- CHECK: 500000 + 85000 = 585000 ✓
      ssb_approval_ref:   'SSB-2023-0044'
      tenure_months:       240

    WRITE → orders_domain.murabaha_schedule  (× 240 rows)
      one row per monthly instalment
      instalment_sar = principal_portion + profit_portion  ✓

    WRITE → retail.account
      account_id:    'ACC0000000000009'
      account_type:  'TAWARRUQ'   -- financing account
      status:        'ACTIVE'

    WRITE → retail.customer_account
      customer_id:  'C000000001'
      account_id:   'ACC0000000000009'
      relationship: 'PRIMARY'

    UPDATE → inventory_domain.product_quota
      SET approved_count       = approved_count + 1,
          approved_amount_sar  = approved_amount_sar + 500000
      WHERE product_id = 'PROD_MRB_002'
        AND status = 'OPEN'
        AND CURRENT_DATE BETWEEN period_start AND period_end;

  COMMIT;

  ↑ All of the above commits together or not at all.
    If the quota update fails, no part of the fulfilment
    is committed. The application remains APPROVED.
    The fulfilment is retried when the issue is resolved.
```

**Now ask: what if the immutability trigger is working?**

```
ATTEMPT: Someone tries to update an audit trail row
         to remove an unfavourable status transition

  UPDATE orders_domain.application_status_history
  SET    changed_by = 'OFFICER_B99'
  WHERE  history_id = 47;

  RESULT: ERROR — trigger fires
    "application_status_history is immutable.
     Rows cannot be UPDATEd. application_id: APP-2025-0042"

  The audit trail is permanent. The original changed_by
  is preserved. SAMA sees exactly what happened and when.
  The trigger makes retrospective editing of audit records
  structurally impossible.
```

---

> **The Orders Domain is now complete.**
>
> Four entities. Two CHECK constraints enforcing business rules.
> One immutability trigger protecting the audit trail.
> One cross-domain atomic transaction on FULFILLED.
> One NPF reporting view for SAMA.
>
> The method is the same as every domain before it.
> The decisions are specific to Orders.
> Apply the same eight steps to Inventory.

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*
-e 

---


# The Retail Mini-Project — Inventory Domain
## How to Read the Requirements, Find the Schema, and Build It End to End
### Al-Noor Bank | Digital Retail Banking Platform

---

> **How to use this guide.**
>
> This guide follows the same eight-step process used for all
> other domains in this architecture. Read the other four first.
>
> The Inventory Domain is the smallest domain in this architecture.
> Two entities — one table, one view. But the design decision
> it contains — how to enforce a quota atomically across concurrent
> approvals — is one of the most consequential decisions in the
> entire platform.
>
> The small size is not a signal that this domain is simple.
> It is a signal that it is focused. It does one thing.
> It does that one thing correctly or the bank breaches
> its SAMA capital limits.

---

## Step 1 — Understand the Domain's Purpose

**The question:** What problem does the Inventory Domain exist to solve?

**The answer:** To enforce the limits on how many of each financial
product the bank can approve — preventing over-approval that would
breach SAMA capital adequacy requirements or exceed risk-approved
capacity limits.

**Why this domain exists — the concrete failure scenario:**

```
WITHOUT the Inventory Domain:

  Al-Noor Bank launches a promotional Murabaha rate.
  10,000 applications arrive in 48 hours.
  The automated approval system processes them all.
  Total financing approved: SAR 5 billion.

  The risk function had approved a quarterly cap of
  SAR 500 million in new Murabaha exposure.

  The bank is now SAR 4.5 billion over its SAMA capital limit.
  SAMA is notified. Emergency capital raise required.
  Senior management accountable.
  SAMA places the bank under enhanced supervision.

WITH the Inventory Domain:

  Product quota: 500 approvals this quarter, max SAR 500M.
  Application 501 is blocked by the availability check.
  The database enforces the limit in real time.
  No human needs to monitor the count.
  No SAMA capital breach occurs.
```

**The domain boundary:**

The Inventory Domain owns the capacity rules for products.
It does not own the products themselves — that is Product Domain.
It does not own the applications — that is Orders Domain.
It references products. It is updated by Orders on every approval.

---

## Step 2 — Identify the Business Questions

```
RISK MANAGEMENT:
→ What is the current approval count for Murabaha Home Finance
  this quarter vs the approved limit?
→ How much of the SAR 500M quarterly Murabaha exposure cap
  has been consumed?
→ Which products are currently in SUSPENDED status and why?
→ When does the current quarterly quota period end?

PRODUCT MANAGEMENT:
→ Which products are currently AVAILABLE for new applications?
→ Which products have hit QUOTA_FULL and are hidden from customers?
→ What is the promotional rate availability window for each product?

DIGITAL ONBOARDING PLATFORM:
→ Is PROD_MRB_002 currently available for a new application?
  (called on every product page load — must be fast)
→ How many approvals remain before this product quota closes?

SAMA REPORTING:
→ Show the total approved exposure by product type this quarter.
→ How many products were suspended due to quota exhaustion?
```

Now map every question to a column or relationship:

```
"Approval count vs limit for Murabaha Home Finance this quarter"
→ product_quota.approved_count  (current)
→ product_quota.max_applications  (limit)
→ WHERE product_id = 'PROD_MRB_002'
  AND CURRENT_DATE BETWEEN period_start AND period_end

"Remaining SAR exposure capacity"
→ product_quota.max_exposure_sar - product_quota.approved_amount_sar
→ This is a subtraction — not a stored value
→ The view computes it on read

"Is PROD_MRB_002 currently AVAILABLE?"
→ v_product_availability view — queried on every product page
→ Returns availability_status: AVAILABLE / QUOTA_FULL / SUSPENDED
→ Must be fast — index on product_id and active period

"Total approved exposure by product type this quarter"
→ product_quota.approved_amount_sar grouped by product_id
→ JOIN to product_domain.product for product name and category
```

---

## Step 3 — Find the Entities

```
PRODUCT_QUOTA
The single entity in this domain. One row per product per period.
Tracks the approved limit (max_applications, max_exposure_sar)
and the current consumption (approved_count, approved_amount_sar).
The two counters are incremented atomically on every approval.

v_product_availability  (view — not a table)
The interface the onboarding platform uses to check availability.
Joins product_quota with product to determine the current state.
Returns availability_status: AVAILABLE, QUOTA_FULL,
SUSPENDED, UNAVAILABLE, EXPOSURE_FULL.
```

**Why only one table?**

```
Banking inventory is not physical goods.
There is no warehouse, no SKU, no bin location.
The only thing that needs to be tracked is:

  How many of this product can be approved this period?
  How many have been approved so far?

That is one table. One row per product per period.
The simplest schema that correctly solves the problem.
```

**What is NOT in this list:**

```
PRODUCT — lives in the Product Domain.
  Inventory references it via product_id.

PRODUCT_APPLICATION — lives in the Orders Domain.
  Inventory is updated when an application is FULFILLED.
  It does not own or track the applications themselves.
```

---

## Step 4 — Establish the Relationships

```
PRODUCT_QUOTA ──── controls capacity of ──────► PRODUCT
(Inventory Domain)                               (Product Domain)

FK: product_quota.product_id → product_domain.product.product_id

PRODUCT_QUOTA ──── updated by ────────────────► PRODUCT_APPLICATION
(Inventory Domain)                               (Orders Domain)

This is NOT a FK relationship. It is a consequence.
When Orders Domain fulfils an application, it runs:
  UPDATE product_quota
  SET    approved_count      = approved_count + 1,
         approved_amount_sar = approved_amount_sar + [amount]
  WHERE  product_id = [product]
  AND    CURRENT_DATE BETWEEN period_start AND period_end;

The UPDATE is performed by the Orders Domain inside its
FULFILLED transaction. No FK enforces this — the business
logic enforces it.
```

**The atomicity requirement:**

```
The product_quota UPDATE must be inside the SAME transaction
as the application status update to FULFILLED.

If they are in separate transactions:

  Transaction A: reads approved_count = 499 (one below max)
  Transaction B: reads approved_count = 499 (same read)
  Transaction A: updates approved_count to 500 → commits
  Transaction B: updates approved_count to 500 → commits

Two applications approved. Count = 500. But two approvals occurred.
Next read: approved_count = 500. Limit appears to be at max.
But the quota was breached — 501 effective approvals happened.

The fix: SELECT FOR UPDATE
  SELECT approved_count, max_applications
  FROM   inventory_domain.product_quota
  WHERE  product_id = 'PROD_MRB_002'
  AND    CURRENT_DATE BETWEEN period_start AND period_end
  FOR UPDATE;

  -- Row is now locked. Transaction B must wait.
  -- Transaction A checks: 499 < 500 → can approve
  -- UPDATE approved_count to 500
  -- COMMIT
  -- Transaction B can now read: 500 = 500 → cannot approve
```

---

## Step 5 — The Conceptual Model

```
CONCEPTUAL MODEL — INVENTORY DOMAIN

┌─ PRODUCT DOMAIN ─────────────────────────────┐
│                                              │
│   ┌───────────────────────────────────────┐  │
│   │                PRODUCT                │  │
│   │  What can be sold — terms, Sharia     │  │
│   │  approval, active status              │  │
│   └───────────────────────────────────────┘  │
│                        │                    │
└────────────────────────┼────────────────────┘
                         │ capacity controlled by
                         ▼
┌─ INVENTORY DOMAIN ──────────────────────────────────────────────┐
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                   PRODUCT_QUOTA                         │   │
│   │                                                         │   │
│   │  max_applications  ──►  approved_count                  │   │
│   │  max_exposure_sar  ──►  approved_amount_sar             │   │
│   │                                                         │   │
│   │  One row per product per period.                        │   │
│   │  approved_count incremented atomically on FULFILLED.   │   │
│   │  SELECT FOR UPDATE prevents concurrent over-approval.  │   │
│   └──────────────────────────────────────────────────────── ┘   │
│                         │                                       │
│                         │ drives                                │
│                         ▼                                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │             v_product_availability  (view)               │   │
│   │                                                         │   │
│   │  availability_status:                                   │   │
│   │  AVAILABLE / QUOTA_FULL / EXPOSURE_FULL / SUSPENDED     │   │
│   │                                                         │   │
│   │  Queried by digital onboarding platform before          │   │
│   │  every product page load.                               │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

UPDATED BY (not a FK — a transactional consequence):
→ Orders Domain updates product_quota on every FULFILLED application
  inside the same database transaction as the status change
```

**What to check before moving on:**

```
□ Is the product_quota entity correctly positioned as
  controlling the Product Domain entity — not owning it?
□ Is the atomicity requirement noted — that the quota update
  must be in the same transaction as FULFILLED?
□ Is the view shown as the interface for external consumers,
  not as an entity with stored data?
□ Is the business rationale — SAMA capital limits, promotional
  windows, risk-approved caps — visible in the model?
```

---

## Step 6 — The Logical Model

---

### Entity 1: PRODUCT_QUOTA

```
PRODUCT_QUOTA
────────────────────────────────────────────────────────────────────
Attribute            Type          Constraint      PDPL      Source
────────────────────────────────────────────────────────────────────
quota_id             SERIAL        PK, NOT NULL    Internal  Risk System

product_id           VARCHAR(15)   NOT NULL        Internal  Risk System
                                   FK → product

quota_period         VARCHAR(10)   NOT NULL        Internal  Risk System
                                   CHECK(MONTHLY, QUARTERLY, ANNUAL)

DECISION: Why a period type column instead of just dates?
The period type tells the system what kind of quota this is.
QUARTERLY quotas align with SAMA capital reporting periods.
MONTHLY quotas are used for short-term promotional campaigns.
ANNUAL quotas are used for long-term concentration limits.
The period type is used in reporting queries to group quota
consumption by the correct business period — not just any date range.

period_start         DATE          NOT NULL        Internal  Risk System
period_end           DATE          NOT NULL        Internal  Risk System

DECISION: Why explicit start and end dates instead of
calculating them from quota_period?
A quarter runs Q1 to Q4 in the Gregorian calendar — but SAMA
reporting also uses the Hijri calendar for some submissions.
A Hijri quarter does not align with a Gregorian quarter.
Storing explicit dates means the system does not need to know
which calendar applies. The dates are always unambiguous.

max_applications     INTEGER       NULLABLE        Internal  Risk System

DECISION: Why nullable?
Some products have no application count limit — only an exposure
SAR limit. A Tawarruq savings account has no cap on the number
of accounts that can be opened — the bank sets no count limit.
The SAR exposure limit may still apply.
NULL means "no count limit for this product in this period".
Zero would mean "zero applications allowed" — which is wrong.

max_exposure_sar     NUMERIC(18,2) NULLABLE        Internal  Risk System

DECISION: Same rationale as max_applications.
Some products have no SAR exposure cap.
Current accounts have unlimited exposure by product design.
NULL means "no SAR limit applies for this period".

approved_count       INTEGER       NOT NULL        Internal  Orders Domain
                                   DEFAULT 0

DECISION: Why an integer counter and not a COUNT query?
At scale — 100,000+ active applications — a COUNT query on
product_application WHERE status = 'APPROVED' is expensive.
The counter on product_quota is a pre-computed aggregate.
It is incremented by one on every approval.
The increment is atomic and consistent because it happens
inside the FULFILLED transaction.

DECISION: What if the counter drifts out of sync?
A reconciliation query can be run periodically:
  SELECT pq.approved_count, COUNT(pa.application_id)
  FROM   inventory_domain.product_quota pq
  JOIN   orders_domain.product_application pa
      ON  pa.product_id = pq.product_id
      AND pa.status = 'FULFILLED'
      AND pa.application_date BETWEEN pq.period_start AND pq.period_end
  GROUP BY pq.quota_id, pq.approved_count;
If the counts disagree, the counter can be corrected.
This is a data quality check — not a normal operation.

approved_amount_sar  NUMERIC(18,2) NOT NULL        Internal  Orders Domain
                                   DEFAULT 0

status               VARCHAR(10)   NOT NULL        Internal  Risk System
                                   DEFAULT 'OPEN'
                                   CHECK(OPEN, CLOSED, SUSPENDED)

DECISION: Why three status values?
OPEN: the quota period is active and accepting approvals.
CLOSED: the quota period has ended (end_date has passed).
SUSPENDED: Risk Management has temporarily halted new approvals
— for example, during a credit policy review or a market
stress event. SUSPENDED is a manual override.
A system that only has OPEN and CLOSED cannot represent
a temporary suspension without closing the period entirely.
────────────────────────────────────────────────────────────────────
```

---

## Step 7 — The Physical DDL

```sql
-- ============================================================
-- INVENTORY DOMAIN
-- Schema: inventory_domain
-- System of Record: Risk Management System
-- Business Data Owner: Head of Product Management / Risk
-- ============================================================

CREATE SCHEMA inventory_domain;

-- ──────────────────────────────────────────────────────────
-- PRODUCT_QUOTA
-- Cross-domain FK: product_id → product_domain.product
-- Updated by Orders Domain atomically on every FULFILLED
-- ──────────────────────────────────────────────────────────
CREATE TABLE inventory_domain.product_quota (
    quota_id             SERIAL        NOT NULL,
    product_id           VARCHAR(15)   NOT NULL,
    quota_period         VARCHAR(10)   NOT NULL
        CHECK (quota_period IN ('MONTHLY','QUARTERLY','ANNUAL')),
    period_start         DATE          NOT NULL,
    period_end           DATE          NOT NULL,
    max_applications     INTEGER,                   -- NULL = unlimited
    max_exposure_sar     NUMERIC(18,2),             -- NULL = unlimited
    approved_count       INTEGER       NOT NULL DEFAULT 0,
    approved_amount_sar  NUMERIC(18,2) NOT NULL DEFAULT 0,
    status               VARCHAR(10)   NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN','CLOSED','SUSPENDED')),
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_quota
        PRIMARY KEY (quota_id),
    -- Cross-domain FK: Inventory → Product Domain
    CONSTRAINT fk_quota_product
        FOREIGN KEY (product_id)
        REFERENCES product_domain.product(product_id),
    CONSTRAINT chk_quota_dates
        CHECK (period_end > period_start),
    CONSTRAINT chk_quota_non_negative
        CHECK (
            approved_count       >= 0 AND
            approved_amount_sar  >= 0
        )
);

CREATE INDEX idx_quota_product_period
    ON inventory_domain.product_quota
    (product_id, period_start, period_end)
    WHERE status = 'OPEN';

-- ──────────────────────────────────────────────────────────
-- v_product_availability
-- The interface the onboarding platform queries on every
-- product page load. Must be fast — index on product_id.
--
-- availability_status values:
--   AVAILABLE    = can accept new applications
--   QUOTA_FULL   = approved_count >= max_applications
--   EXPOSURE_FULL= approved_amount_sar >= max_exposure_sar
--   SUSPENDED    = manually suspended by Risk Management
--   UNAVAILABLE  = product is_active = FALSE
-- ──────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW inventory_domain.v_product_availability AS
SELECT
    p.product_id,
    p.product_name_en,
    p.product_code,
    p.is_sharia_compliant,
    p.ssb_approval_ref,
    pq.quota_id,
    pq.quota_period,
    pq.period_start,
    pq.period_end,
    pq.max_applications,
    pq.approved_count,
    CASE
        WHEN pq.max_applications IS NULL THEN NULL
        ELSE pq.max_applications - pq.approved_count
    END                                                   AS remaining_applications,
    pq.max_exposure_sar,
    pq.approved_amount_sar,
    CASE
        WHEN pq.max_exposure_sar IS NULL THEN NULL
        ELSE pq.max_exposure_sar - pq.approved_amount_sar
    END                                                   AS remaining_exposure_sar,
    CASE
        WHEN p.is_active = FALSE                          THEN 'UNAVAILABLE'
        WHEN pq.status   = 'SUSPENDED'                   THEN 'SUSPENDED'
        WHEN pq.max_applications IS NOT NULL
         AND pq.approved_count >= pq.max_applications    THEN 'QUOTA_FULL'
        WHEN pq.max_exposure_sar IS NOT NULL
         AND pq.approved_amount_sar >= pq.max_exposure_sar THEN 'EXPOSURE_FULL'
        ELSE 'AVAILABLE'
    END                                                   AS availability_status
FROM product_domain.product p
LEFT JOIN inventory_domain.product_quota pq
    ON  p.product_id    = pq.product_id
    AND pq.period_start <= CURRENT_DATE
    AND pq.period_end   >= CURRENT_DATE
    AND pq.status        = 'OPEN'
WHERE p.is_active = TRUE;

-- ──────────────────────────────────────────────────────────
-- ATOMIC QUOTA UPDATE PATTERN
-- Used by Orders Domain inside the FULFILLED transaction.
-- The SELECT FOR UPDATE locks the row before checking.
-- No two concurrent transactions can both proceed.
-- ──────────────────────────────────────────────────────────

-- Step 1: Lock and read the quota row
-- SELECT quota_id, approved_count, max_applications,
--        approved_amount_sar, max_exposure_sar
-- FROM   inventory_domain.product_quota
-- WHERE  product_id  = 'PROD_MRB_002'
--   AND  status      = 'OPEN'
--   AND  CURRENT_DATE BETWEEN period_start AND period_end
-- FOR UPDATE;

-- Step 2: Application layer checks the result
-- IF approved_count >= max_applications → reject with QUOTA_FULL
-- IF approved_amount_sar >= max_exposure_sar → reject with EXPOSURE_FULL

-- Step 3: If within limits, increment and commit
-- UPDATE inventory_domain.product_quota
-- SET    approved_count      = approved_count + 1,
--        approved_amount_sar = approved_amount_sar + :approved_amount
-- WHERE  quota_id = :quota_id;

-- This UPDATE is part of the FULFILLED transaction.
-- If any part of FULFILLED fails, this UPDATE also rolls back.
-- The count is never incremented for a failed fulfilment.

-- ──────────────────────────────────────────────────────────
-- SAMPLE DATA
-- ──────────────────────────────────────────────────────────
INSERT INTO inventory_domain.product_quota
    (product_id, quota_period, period_start, period_end,
     max_applications, max_exposure_sar, status)
VALUES
    -- Murabaha Personal Finance: 500 approvals, SAR 50M cap, Q1 2025
    ('PROD_MRB_001', 'QUARTERLY', '2025-01-01', '2025-03-31',
     500, 50000000.00, 'OPEN'),

    -- Murabaha Home Finance: 200 approvals, SAR 200M cap, Q1 2025
    ('PROD_MRB_002', 'QUARTERLY', '2025-01-01', '2025-03-31',
     200, 200000000.00, 'OPEN'),

    -- Tawarruq Savings Account: no count limit, no SAR cap, full year
    ('PROD_TAW_001', 'ANNUAL', '2025-01-01', '2025-12-31',
     NULL, NULL, 'OPEN');

-- ──────────────────────────────────────────────────────────
-- QUOTA RECONCILIATION QUERY
-- Run periodically to verify approved_count is in sync
-- with actual FULFILLED applications in Orders Domain.
-- If counts disagree: investigate and correct the counter.
-- ──────────────────────────────────────────────────────────
-- SELECT
--     pq.quota_id,
--     pq.product_id,
--     pq.period_start,
--     pq.period_end,
--     pq.approved_count        AS counter_value,
--     COUNT(pa.application_id) AS actual_fulfilled_count,
--     pq.approved_count - COUNT(pa.application_id)  AS discrepancy
-- FROM inventory_domain.product_quota pq
-- LEFT JOIN orders_domain.product_application pa
--     ON  pa.product_id = pq.product_id
--     AND pa.status = 'FULFILLED'
--     AND pa.application_date
--         BETWEEN pq.period_start AND pq.period_end
-- GROUP BY pq.quota_id, pq.product_id,
--          pq.period_start, pq.period_end, pq.approved_count
-- HAVING pq.approved_count != COUNT(pa.application_id);
```

---

## Step 8 — Validate with a Business Scenario

**Scenario: The 200th Murabaha Home Finance application in Q1 2025
is approved. The 201st application attempts to approve.
Trace what happens in both cases.**

```
CASE A: Application 200 — last available slot

STEP 1: Orders Domain queries availability before offering the product

  READ  → inventory_domain.v_product_availability
    WHERE product_id = 'PROD_MRB_002'
    → approved_count = 199
    → max_applications = 200
    → remaining_applications = 1
    → availability_status = 'AVAILABLE'
    ✓ Product is shown to the customer

STEP 2: Customer applies. Application proceeds through lifecycle.
        On FULFILLED:

  BEGIN;  -- one transaction

    UPDATE orders_domain.product_application
      SET status = 'FULFILLED' WHERE application_id = 'APP-2025-0199';

    WRITE  orders_domain.application_status_history;

    WRITE  retail.account;
    WRITE  retail.customer_account;
    WRITE  orders_domain.murabaha_contract;
    WRITE  orders_domain.murabaha_schedule × 240;

    -- Lock and check quota before incrementing
    SELECT approved_count, max_applications
    FROM   inventory_domain.product_quota
    WHERE  product_id = 'PROD_MRB_002' AND status = 'OPEN'
    AND    CURRENT_DATE BETWEEN period_start AND period_end
    FOR UPDATE;
    -- Returns: approved_count = 199, max_applications = 200
    -- 199 < 200 → proceed

    UPDATE inventory_domain.product_quota
    SET    approved_count      = 200,
           approved_amount_sar = approved_amount_sar + 500000
    WHERE  product_id = 'PROD_MRB_002' AND status = 'OPEN';

  COMMIT;

  RESULT: Application 200 approved. Counter = 200. Quota = full.

────────────────────────────────────────────────────────────

CASE B: Application 201 — quota exhausted

STEP 1: Orders Domain queries availability

  READ  → inventory_domain.v_product_availability
    WHERE product_id = 'PROD_MRB_002'
    → approved_count = 200
    → max_applications = 200
    → remaining_applications = 0
    → availability_status = 'QUOTA_FULL'

  The onboarding platform receives availability_status = 'QUOTA_FULL'.
  The product page is hidden from the customer.
  The customer cannot submit an application for a product
  that has no remaining quota.
  Application 201 is never created.

────────────────────────────────────────────────────────────

CASE C: Race condition — two applications attempt simultaneously

  Transaction A: reads approved_count = 199  FOR UPDATE  → locks row
  Transaction B: attempts to read              FOR UPDATE  → waits

  Transaction A: checks 199 < 200 → proceeds → increments to 200 → commits
  Transaction B: lock released → reads approved_count = 200
  Transaction B: checks 200 >= 200 → QUOTA_FULL → cannot approve

  The FOR UPDATE lock ensures only one transaction can read,
  check, and increment at a time.
  The race condition is eliminated at the database level.
```

**Now ask: what if someone tries to SUSPEND the quota mid-quarter?**

```
SCENARIO: Risk Management issues a credit policy hold.
          No new Murabaha Home Finance approvals until further notice.

  UPDATE inventory_domain.product_quota
  SET    status = 'SUSPENDED'
  WHERE  product_id = 'PROD_MRB_002' AND status = 'OPEN';

  RESULT: v_product_availability now returns:
    availability_status = 'SUSPENDED'

  The onboarding platform hides the product immediately.
  No new applications can be submitted.
  Existing applications in UNDER_REVIEW are not affected —
  they can still be processed to completion if the policy
  allows it.
  When the hold is lifted: UPDATE status = 'OPEN' → quota resumes.
  No data is lost. The approved_count and approved_amount_sar
  are preserved exactly as they were.
```

---

> **The Inventory Domain is now complete.**
>
> One table. One view. One SELECT FOR UPDATE pattern.
> Three status values: OPEN, CLOSED, SUSPENDED.
> The domain is small but its consequence is large.
>
> Without it: the bank over-approves Murabaha contracts
> and breaches its SAMA capital limit.
>
> With it: the limit is enforced at the database level,
> atomically, concurrently, without race conditions.
>
> All five domains are now complete.
> The method is the transferable skill.

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*