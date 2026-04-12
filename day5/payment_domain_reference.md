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