# The Retail Mini-Project
## Your Mission as Lead Data Architect — Al-Noor Bank
### Problem Statement & Expectations

---

> **Before you read further — a personal note.**
>
> What you are about to work on is not a training exercise.
> It is a real architecture challenge, set in a realistic
> Saudi banking context, with real regulatory constraints,
> real design decisions, and real consequences for getting
> those decisions wrong.
>
> By the time you are done, you will have produced a deliverable
> that you could walk into any Saudi bank and say:
> "This is how I would design this system — and here is why."
>
> Read this document carefully. It tells you everything you
> need to know about what you are building, why it exists,
> and how it connects to the work you do every day.

---

## The Story — Why Al-Noor Bank Needs You

Al-Noor Bank has been operating as a traditional branch-based
retail bank for 15 years. Customers queue at branches.
Paper forms are filled in. KYC documents are photocopied.
Murabaha applications are processed over days, sometimes weeks.

The world has changed. Saudi Vision 2030 is driving digital
transformation across every sector. SAMA has published Open
Banking regulations. Competitors — including new digital-only
banks — are onboarding customers in minutes, not days.

Al-Noor Bank's board has made a decision:

> **Launch a Digital Retail Banking Platform within 12 months.
> End-to-end digital. No branch visit required. Full SAMA
> and PDPL compliance from day one.**

The CEO has signed off. The project is funded. The technology
team is ready to build.

There is one problem.

**Nobody has designed the data architecture yet.**

That is where you come in.

---

## Your Role

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   YOU ARE THE LEAD DATA ARCHITECT                       │
│   FOR AL-NOOR BANK'S DIGITAL RETAIL BANKING PLATFORM   │
│                                                         │
│   Your decisions determine:                             │
│   → What data the bank can store                        │
│   → How that data is structured and governed            │
│   → How it flows between systems                        │
│   → Whether SAMA can be satisfied at audit time         │
│   → Whether PDPL obligations can be proven              │
│   → Whether the platform can scale to 500,000           │
│     transactions per day                                │
│                                                         │
│   No developer writes a line of code until              │
│   your architecture is approved.                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

This is not a junior role. The Lead Data Architect at a Saudi
bank is accountable to the CTO, the Chief Risk Officer, the
Chief Compliance Officer, and — indirectly — to SAMA itself.

Every design decision you make will be justified, documented,
and reviewed.

---

## The Platform — What It Must Do

Al-Noor Bank's Digital Retail Banking Platform must enable
a customer to do everything digitally — from first contact
to active account holder — without stepping into a branch.

```
CUSTOMER JOURNEY — FULLY DIGITAL

  ┌──────────────┐
  │   DISCOVERS  │  Customer finds Al-Noor via app or website
  │   AL-NOOR    │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │   APPLIES    │  Selects a product and submits an application
  │   FOR A      │  Platform captures all details digitally
  │   PRODUCT    │
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  VERIFIED    │  Identity confirmed via Nafath (Absher)
  │  & CHECKED   │  Credit assessed via SIMAH
  │              │  AML screened via OFAC / SAMA watchlists
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │  APPROVED    │  Decision made — automated or officer review
  │  & ONBOARDED │  Account created, contract generated
  │              │  Repayment schedule produced (if financing)
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │   ACTIVELY   │  Makes payments via SARIE, SADAD, mada
  │   BANKING    │  Manages accounts via mobile app
  │              │  Receives SAMA-compliant statements
  └──────────────┘
```

Every step in this journey touches data. Your architecture
determines how that data is captured, structured, governed,
and used.

---

## The Five Domains — The Architecture at a Glance

The platform is organised into five business domains.
Each domain has a clear owner, a clear scope, and a clear
boundary. Understanding these boundaries is the foundation
of everything you will design.

```
┌─────────────────────────────────────────────────────────────────┐
│                  AL-NOOR DIGITAL RETAIL PLATFORM                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │   PRODUCT   │    │  CUSTOMER   │    │   ORDERS    │        │
│   │             │    │             │    │             │        │
│   │ What we     │    │ Who we      │    │ The journey │        │
│   │ can sell    │    │ sell to     │    │ from apply  │        │
│   │             │    │             │    │ to active   │        │
│   │ • Categories│    │ • Individual│    │             │        │
│   │ • Products  │    │ • Corporate │    │ • Application│       │
│   │ • Terms     │    │ • KYC       │    │ • Status    │        │
│   │ • Pricing   │    │ • Consent   │    │   History   │        │
│   │ • Sharia    │    │ • Contacts  │    │ • Contract  │        │
│   │   Approval  │    │             │    │ • Schedule  │        │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘        │
│          │                  │                  │               │
│          └──────────────────┼──────────────────┘               │
│                             │                                  │
│   ┌─────────────────────────┼──────────────────────────┐       │
│   │         CROSS-CUTTING: KYC · AML · PDPL · SAMA     │       │
│   └─────────────────────────┼──────────────────────────┘       │
│                             │                                  │
│   ┌─────────────┐           │           ┌─────────────┐        │
│   │  INVENTORY  │           │           │  PAYMENTS   │        │
│   │             │           │           │             │        │
│   │ Capacity    │           │           │ How money   │        │
│   │ and limits  │           │           │ moves       │        │
│   │             │           │           │             │        │
│   │ • Quotas    │           │           │ • SARIE     │        │
│   │ • SAMA caps │           │           │ • SADAD     │        │
│   │ • Promo     │           │           │ • mada      │        │
│   │   windows   │           │           │ • SWIFT     │        │
│   └─────────────┘           │           └─────────────┘        │
│                             │                                  │
└─────────────────────────────┼───────────────────────────────---┘
                              │
                    EXTERNAL INTEGRATIONS
              ┌───────────────┼───────────────┐
              │               │               │
           Nafath           SIMAH           SARIE
           OFAC             SADAD           ZATCA
```

---

## Domain 1 — Product
### What We Can Sell

**In plain terms:** The product catalogue. Every financial product
Al-Noor Bank offers — every account type, every financing product,
every card — is defined here. The Product Domain controls what
can be sold, at what terms, with what Sharia compliance status.

**The entities:**

```
PRODUCT_CATEGORY
      │
      │ "belongs to"
      ▼
   PRODUCT ──────────── SHARIA_APPROVAL (SSB reference)
      │
      │ "has"
      ▼
PRODUCT_TERMS ──────── PRODUCT_PRICING (by customer segment)
      │
      │ "controlled by"
      ▼
PRODUCT_QUOTA (Inventory Domain references this)
```

**The rule that matters most:**

```
┌──────────────────────────────────────────────────────┐
│  EVERY ISLAMIC PRODUCT MUST HAVE AN SSB APPROVAL    │
│  REFERENCE — ENFORCED AT THE DATABASE LEVEL          │
│                                                      │
│  CHECK (                                             │
│    is_sharia_compliant = FALSE                       │
│    OR ssb_approval_ref IS NOT NULL                   │
│  )                                                   │
│                                                      │
│  If this constraint did not exist and an Islamic     │
│  product launched without Sharia Board sign-off,     │
│  every contract under that product could be          │
│  declared invalid. Remediation = contacting every    │
│  affected customer. A SAMA finding. An SSB review    │
│  of the entire product governance process.           │
│                                                      │
│  The constraint makes the wrong state impossible.    │
└──────────────────────────────────────────────────────┘
```

**Business Data Owner:** Head of Product Management
**System of Record:** Product Management System (PMS)

---

## Domain 2 — Customer
### Who We Sell To

**In plain terms:** The single source of truth for customer identity.
Every other domain depends on this one. No product can be sold
to an anonymous customer. No payment can be authorised without
knowing who initiated it.

**The design challenge — Individual vs Corporate:**

```
OPTION A — Single Table (Rejected)
┌────────────────────────────────────────────────────┐
│ CUSTOMER                                           │
│ customer_id | customer_type | national_id | cr_no  │
│ C000000001  │      I        │ 12345...    │ NULL   │
│ C000000002  │      C        │ NULL        │ 987654 │
│ C000000003  │      I        │ 67890...    │ NULL   │
└────────────────────────────────────────────────────┘
Problem: cr_no is NULL for all individuals.
         national_id is NULL for all corporates.
         Every query must remember which columns apply
         to which type. One forgotten filter = wrong data.

OPTION B — Parent + Subtype (Chosen) ✓
┌─────────────────────────────────────────┐
│ CUSTOMER (parent — shared attributes)   │
│ customer_id | type | kyc_status | ...   │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
┌───────▼────────┐  ┌────────▼──────────┐
│ INDIVIDUAL_    │  │ CORPORATE_        │
│ CUSTOMER       │  │ CUSTOMER          │
│                │  │                   │
│ national_id    │  │ commercial_reg_no │
│ date_of_birth  │  │ vat_number        │
│ nationality    │  │ gosi_id           │
│ monthly_income │  │ authorised_       │
│                │  │ signatory_id      │
└────────────────┘  └───────────────────┘

Individual customers can ONLY have individual attributes.
Corporate customers can ONLY have corporate attributes.
The wrong state is structurally impossible to represent.
```

**The PDPL entity — Customer Consent:**

```
Every processing activity on customer personal data
requires a documented legal basis under PDPL.

CUSTOMER_CONSENT table — one row per purpose per customer

┌──────────────────────┬───────────────────┬──────────────────┐
│ processing_purpose   │ legal_basis       │ consent_given    │
├──────────────────────┼───────────────────┼──────────────────┤
│ ACCOUNT_OPERATIONS   │ CONTRACT          │ TRUE (always)    │
│ MARKETING_COMMS      │ CONSENT           │ TRUE / FALSE     │
│ CREDIT_BUREAU_SHARE  │ LEGAL_OBLIGATION  │ TRUE (always)    │
│ OPEN_BANKING_SHARE   │ CONSENT           │ TRUE / FALSE     │
│ AML_COMPLIANCE       │ LEGAL_OBLIGATION  │ TRUE (always)    │
└──────────────────────┴───────────────────┴──────────────────┘

This table is not a legal afterthought.
It is the evidence of compliance.
If the PDPL authority asks "what is the legal basis for
processing this customer's credit bureau data?" —
the answer must be in the database, not reconstructed
from a policy document.
```

**Business Data Owner:** Head of Retail Banking / Chief Customer Officer
**System of Record:** CRM + KYC Platform (Nafath-verified)

---

## Domain 3 — Orders
### The Lifecycle of a Product Application

**In plain terms:** In banking, an "order" is a product application.
A customer's request to open a Tawarruq account, apply for Murabaha
Home Finance, or get a card. The Orders Domain manages the complete
lifecycle from submission to fulfilment — and records every status
change with an immutable audit trail.

**The application lifecycle:**

```
  SUBMITTED
      │
      │  Automated checks fire immediately:
      │  → AML screening (OFAC / SAMA watchlists)
      │  → Nafath eKYC verification
      │  → SIMAH credit check (financing only)
      │
      ▼
  UNDER_REVIEW
      │
      │  Officer sees full compliance results:
      │  → AML: CLEAR or FLAGGED
      │  → Nafath: verified or failed
      │  → SIMAH score (300–900)
      │
      ▼
  APPROVED / REJECTED
      │
      │  Decision recorded with:
      │  → Officer ID or "AUTOMATED_SYSTEM"
      │  → Timestamp
      │  → Reason (mandatory for rejections)
      │
      ▼
  FULFILLED
      │
      │  Account created
      │  Contract generated (if financing)
      │  Repayment schedule produced
      │  All linked to the original application
      │
      ▼
  ACTIVE → CLOSED
```

**The audit trail — why it cannot be optional:**

```
┌──────────────────────────────────────────────────────────┐
│  REAL SCENARIO — SAMA SUPERVISORY REVIEW                 │
│                                                          │
│  Examiner: "Show me the complete trail for application   │
│  APP-2024-0847. Who reviewed it, when did each status    │
│  change, what was the Nafath verification result?"       │
│                                                          │
│  Bank WITHOUT application_status_history:                │
│  "The application was rejected."                         │
│  Examiner: "Why? Who made that decision? When?"          │
│  Bank: "We... do not have that information."             │
│  Result: Supervisory finding. Schema migration on a      │
│  live production system with 300,000 active applications.│
│                                                          │
│  Bank WITH application_status_history:                   │
│  "Here is every status change, every timestamp, every    │
│  officer ID, every AML check result — all in the         │
│  database, all immutable, all auditable."                │
│  Result: Clean examination.                              │
└──────────────────────────────────────────────────────────┘
```

**APPLICATION_STATUS_HISTORY — append-only, never updated:**

```
┌────────────┬──────────────┬─────────────┬─────────────────────┐
│ history_id │ old_status   │ new_status  │ changed_at          │
├────────────┼──────────────┼─────────────┼─────────────────────┤
│          1 │ NULL         │ SUBMITTED   │ 2025-03-15 09:14:22 │
│          2 │ SUBMITTED    │ UNDER_REVIEW│ 2025-03-15 09:14:45 │
│          3 │ UNDER_REVIEW │ APPROVED    │ 2025-03-16 11:30:01 │
│          4 │ APPROVED     │ FULFILLED   │ 2025-03-16 14:22:17 │
└────────────┴──────────────┴─────────────┴─────────────────────┘

No row is ever updated. No row is ever deleted.
Every transition is permanent. This is what "immutable" means.
```

**Business Data Owner:** Head of Digital Onboarding / Operations
**System of Record:** Digital Onboarding Platform

---

## Domain 4 — Inventory
### Capacity and Availability of Financial Products

**In plain terms:** Banking inventory is not physical goods.
It is the capacity to offer financial products — how many
Murabaha contracts the bank can approve this quarter, how much
financing exposure is allowed in one sector, when a promotional
rate offer expires.

**Why this domain exists:**

```
┌──────────────────────────────────────────────────────────┐
│  WITHOUT INVENTORY MANAGEMENT                            │
│                                                          │
│  Al-Noor Bank launches a promotional Murabaha rate.      │
│  10,000 applications arrive in 48 hours.                 │
│  All 10,000 are approved by an automated system.         │
│  Total financing approved: SAR 5 billion.                │
│                                                          │
│  Problem: The bank's capital adequacy ratio allows       │
│  SAR 500 million in new Murabaha this quarter.           │
│  The bank is now SAR 4.5 billion over its SAMA limit.    │
│  SAMA is notified. Emergency capital raise required.     │
│  Senior management accountable.                          │
│                                                          │
│  WITH INVENTORY MANAGEMENT                               │
│                                                          │
│  Product quota: 500 Murabaha approvals this quarter,     │
│  maximum SAR 500 million exposure.                       │
│  Application 501 cannot be approved.                     │
│  The database enforces the limit in real time.           │
│  No human needs to monitor the count.                    │
│  No regulatory breach occurs.                            │
└──────────────────────────────────────────────────────────┘
```

**Three types of banking inventory:**

```
┌────────────────────┬──────────────────────────────────────┐
│ Type               │ Example                              │
├────────────────────┼──────────────────────────────────────┤
│ Product Quotas     │ Max 500 Murabaha contracts in Q1     │
│                    │ Controlled by Risk function          │
├────────────────────┼──────────────────────────────────────┤
│ Regulatory Caps    │ Max 35% of loan book in property     │
│                    │ SAMA concentration limit             │
├────────────────────┼──────────────────────────────────────┤
│ Availability       │ 3.5% Murabaha rate until 31 March    │
│ Windows            │ OR until SAR 500M approved —         │
│                    │ whichever comes first                │
└────────────────────┴──────────────────────────────────────┘
```

**Business Data Owner:** Head of Product Management / Risk
**System of Record:** Risk Management System

---

## Domain 5 — Payments
### How Money Moves

**In plain terms:** Every payment initiated through the platform —
domestic transfers, bill payments, international wires, card
transactions — is managed here. Saudi Arabia has multiple payment
networks, each with different rules, reference numbers, and SAMA
reporting requirements.

**The Saudi payment rails — what your schema must model:**

```
┌──────────┬──────────────────────────────────────┬──────────────────┐
│ Rail     │ What It Is                           │ Your Data Model  │
├──────────┼──────────────────────────────────────┼──────────────────┤
│ SARIE    │ Saudi interbank RTGS — real-time SAR │ sarie_uetr       │
│          │ transfers between banks              │ (UUID reference) │
├──────────┼──────────────────────────────────────┼──────────────────┤
│ SADAD    │ National bills network — utilities,  │ sadad_ref        │
│          │ government fees, insurance           │                  │
├──────────┼──────────────────────────────────────┼──────────────────┤
│ mada     │ Saudi national debit card network    │ card_ref         │
│          │ POS and ATM                          │                  │
├──────────┼──────────────────────────────────────┼──────────────────┤
│ SWIFT    │ International transfers              │ swift_uetr       │
│          │ ISO 20022 standard                   │ (UUID reference) │
├──────────┼──────────────────────────────────────┼──────────────────┤
│ Internal │ Transfers within Al-Noor Bank        │ No external ref  │
│          │ Instant settlement                   │                  │
└──────────┴──────────────────────────────────────┴──────────────────┘

WHY SEPARATE REFERENCE COLUMNS?

A SARIE payment has a UETR (Unique End-to-End Transaction Reference).
A SWIFT payment also has a UETR — different format, different system,
different regulatory purpose.
A SADAD payment has a SADAD reference number — completely different.

One generic reference_no column cannot serve all three.
The schema must have sarie_uetr, swift_uetr, and sadad_ref
as separate typed nullable columns — each populated only
when that rail is used, NULL otherwise.
```

**Business Data Owner:** Head of Payments / Operations
**System of Record:** Payment Processing System

---

## The External Integrations — Six Systems You Must Connect

The platform does not operate in isolation. It connects to six
external systems — each of which requires a logged, auditable
connection.

```
                        AL-NOOR PLATFORM
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
    ┌───────────┐       ┌───────────┐       ┌───────────┐
    │  Nafath   │       │   SIMAH   │       │   SARIE   │
    │ (Absher)  │       │           │       │  / SAMA   │
    │           │       │           │       │           │
    │ Ministry  │       │ Saudi     │       │ Real-time │
    │ of        │       │ Credit    │       │ domestic  │
    │ Interior  │       │ Bureau    │       │ payment   │
    │           │       │           │       │ network   │
    │ eKYC ID   │       │ Score     │       │           │
    │ verify    │       │ 300–900   │       │ UETR ref  │
    └───────────┘       └───────────┘       └───────────┘
          │                   │                   │
          ▼                   ▼                   ▼
    ┌───────────┐       ┌───────────┐       ┌───────────┐
    │   SADAD   │       │   OFAC    │       │   ZATCA   │
    │           │       │  / UN     │       │           │
    │ National  │       │ Sanctions │       │ Zakat &   │
    │ bills     │       │           │       │ Tax       │
    │ payment   │       │ AML       │       │ Authority │
    │ gateway   │       │ screening │       │           │
    │           │       │           │       │ VAT &     │
    │ Bill ref  │       │ PEP lists │       │ Zakat     │
    │ confirm   │       │ Watchlist │       │ reporting │
    └───────────┘       └───────────┘       └───────────┘
```

**The rule that applies to every integration — no exceptions:**

```
┌──────────────────────────────────────────────────────────┐
│  EVERY EXTERNAL API CALL PRODUCES ONE LOG ROW            │
│  IN external_api_log                                     │
│                                                          │
│  What is logged:                                         │
│  → Which service was called (Nafath, SIMAH, OFAC...)     │
│  → When the call was made                                │
│  → The internal reference (application_id, payment_id)   │
│  → How long it took (response_time_ms)                   │
│  → Whether it succeeded, failed, or timed out            │
│                                                          │
│  What is NOT logged:                                     │
│  → Raw National ID numbers                               │
│  → Biometric data                                        │
│  → Any PDPL-restricted personal data                     │
│  (These stay in the secured KYC system)                  │
│                                                          │
│  Why response_time_ms matters:                           │
│  If Nafath verification takes 8 seconds against a        │
│  3-second SLA, this column provides the data to          │
│  escalate — not an anecdotal report that "it feels slow" │
└──────────────────────────────────────────────────────────┘
```

---

## What You Will Produce

Your work across this project produces six deliverables.
Together they form a complete Architecture Design Document —
the kind of output handed to a real client at the end of
a real engagement.

```
DELIVERABLE 1 — Multi-Domain Conceptual ERD
┌─────────────────────────────────────────────────────┐
│ A single diagram showing:                           │
│ → All five domains clearly bounded                  │
│ → All entities within each domain                   │
│ → All cross-domain relationships                    │
│ → PDPL-sensitive entities marked 🔒                 │
│ → System of Record identified per domain            │
│ → Business Data Owner named per domain              │
└─────────────────────────────────────────────────────┘

DELIVERABLE 2 — Attribute Dictionary
┌─────────────────────────────────────────────────────┐
│ A formal data dictionary for CUSTOMER and PAYMENT:  │
│ → Business name for every attribute                 │
│ → Data type and constraints                         │
│ → PDPL classification (Restricted / Confidential /  │
│   Internal / Public)                                │
│ → Retention period                                  │
│ → Source system (not "database" — the upstream      │
│   system that first creates the data)               │
└─────────────────────────────────────────────────────┘

DELIVERABLE 3 — Business Scenario Validation
┌─────────────────────────────────────────────────────┐
│ Three end-to-end traces:                            │
│ → New customer digital onboarding                   │
│   (every table read and written, in order)          │
│ → Murabaha Home Finance application                 │
│   (apply → approve → contract → schedule)           │
│ → AML-flagged payment                               │
│   (initiation → flag → review → resolve)            │
└─────────────────────────────────────────────────────┘

DELIVERABLE 4 — Physical DDL
┌─────────────────────────────────────────────────────┐
│ Production-grade PostgreSQL for all five domains:   │
│ → All tables with correct data types                │
│ → All constraints (CHECK, FK, UNIQUE, NOT NULL)     │
│ → All indexes with justification                    │
│ → Partitioning where required (transaction table)   │
│ → Sample data across all domains                    │
└─────────────────────────────────────────────────────┘

DELIVERABLE 5 — Analytics Layer
┌─────────────────────────────────────────────────────┐
│ Reporting views and materialised views:             │
│ → SAMA daily liquidity report feed                  │
│ → NPF (Non-Performing Finance) ratio view           │
│ → Murabaha portfolio exposure summary               │
│ → Customer 360 view                                 │
└─────────────────────────────────────────────────────┘

DELIVERABLE 6 — Architecture Design Document
┌─────────────────────────────────────────────────────┐
│ The full ADD:                                       │
│ → Five ADRs (Architecture Decision Records)         │
│ → Domain diagrams with entity relationships         │
│ → Data flow: source systems → ODS → DWH → reports  │
│ → PDPL data map                                     │
│ → SAMA compliance traceability matrix               │
└─────────────────────────────────────────────────────┘
```

---

## The Decisions That Will Be Debated

Some design decisions in this project are genuinely debatable.
There is not always one correct answer. What matters is that
your decision is defensible and documented.

Here are the five debates you should be ready for:

```
DEBATE 1: Single table vs parent + subtype for Customer
One CUSTOMER table with a discriminator column, or a CUSTOMER
parent with INDIVIDUAL and CORPORATE subtypes?
→ Both work. One is much cleaner at scale. Which and why?

DEBATE 2: Where does KYC live?
Does KYC_RECORD belong in the Customer Domain or a separate
Compliance Domain?
→ Both are defensible. What are the governance implications?

DEBATE 3: Who owns the ACCOUNT entity?
Payments needs the account to process a payment.
Customer Domain is where accounts are opened and managed.
Which domain owns ACCOUNT — and what are the query implications?

DEBATE 4: PDPL classification of monthly_income_sar
Is monthly income Restricted or Confidential under PDPL?
→ The classification determines encryption requirements
  and who can query the column.

DEBATE 5: Source system for national_id
What is the source system for the national_id column?
→ "The database" is not an answer. The database stores it.
  Something else creates it. What and why does it matter?
```

---

## What Success Looks Like

A successful outcome means being able to:

```
✓ Walk a SAMA examiner through the complete data trail
  for any application — every status change, every
  compliance check, every decision with its timestamp
  and officer ID.

✓ Answer "where does this customer's national_id come from
  and who is authorised to see it?" with a reference to
  the schema, the PDPL classification, and the source system.

✓ Show why a Murabaha contract with incorrect totals cannot
  be inserted — because the CHECK constraint prevents it.

✓ Demonstrate that a payment above SAR 60,000 cannot complete
  without passing the AML compliance check — enforced by
  boolean flags in the schema, not application code.

✓ Produce an Architecture Design Document with decisions
  justified, alternatives documented, and trade-offs
  acknowledged — ready to be handed to a real client.
```

---

## How This Connects to Your Real Work

This is not a fictional exercise that exists only in the classroom.
Every design challenge here maps directly to challenges that exist
in real Saudi banking systems right now.

```
ON SCHEMA DESIGN:
→ The single-table vs subtype debate happens at every Saudi bank
  that serves both individual and corporate customers.
→ The generic reference_no problem exists in most Saudi payment
  systems built before 2020.
→ The missing audit trail is the most common SAMA finding in
  digital onboarding system reviews.

ON DATA GOVERNANCE:
→ The PDPL attribute dictionary is a required artefact under
  Saudi data protection obligations — most organisations
  have not produced a complete one.
→ The consent management design is what PDPL compliance
  looks like at the schema level. Most organisations manage
  consent in spreadsheets.
→ System of Record identification is the foundation of any
  data lineage programme. Most Saudi banks cannot trace a
  customer record from the DWH back to the source system
  that created it.

ON REGULATORY REPORTING:
→ The SAMA compliance traceability matrix connects every
  report to the schema that produces it. If a SAMA examiner
  asks where the NPF ratio comes from, you point to the view.
  If you cannot, that is a finding.
```

---

---

# SAMA & PDPL Quick Reference Checklist

*Use this checklist as you design. Every item here is a real
obligation — not a guideline, not a best practice.
A box left unchecked is a risk that a SAMA examiner or PDPL
authority will surface before you do.*

---

## SAMA Requirements Checklist

### Data Retention

```
□ Transaction records retained for a minimum of 10 years
  → Partition strategy defined for the transaction table
  → Hot (0–2yr), Warm (2–5yr), Cold (5–10yr) tiers identified
  → No transaction row can be hard deleted

□ KYC records retained for 10 years after account closure
  → is_deleted flag used — never physical deletion
  → legal_hold flag implemented to prevent automated purge

□ AML records retained for 10 years
  → AML alerts are append-only
  → Closed alerts remain in the database with closed status
```

### Reporting

```
□ Daily liquidity report available by 07:00 AM
  → Materialised view refreshed nightly before 06:00 AM
  → Airflow DAG or equivalent scheduled refresh confirmed
  → Report traces to source tables in the schema

□ Weekly transaction report automated
  → View or materialised view defined in the analytics schema
  → Data lineage: transaction table → view → report

□ Monthly NPL / NPF ratio report automated
  → NPF definition (>90 days overdue) encoded in the view
  → Numerator and denominator both traceable to schema
```

### Transaction Monitoring

```
□ Transactions above SAR 60,000 flagged for review
  → AML system receives transaction data in real time
  → compliance_screened and sanctions_checked flags
    on the payment table — both must be TRUE before COMPLETED

□ Structuring detection implemented
  → Query pattern detects 3+ transactions on same day
    between SAR 10,000 and SAR 59,999 on the same account
  → AML alert raised automatically — alert_type = STRUCTURING

□ PEP and sanctions screening on every application and payment
  → is_pep and is_sanctioned flags on the customer table
  → external_api_log records every OFAC / SAMA watchlist call
  → FLAGGED applications cannot auto-approve
```

### KYC Renewal Tracking

```
□ High-risk customers (H) reviewed every 12 months
□ Medium-risk customers (M) reviewed every 24 months
□ Low-risk customers (L) reviewed every 36 months
  → kyc_last_reviewed column on customer table
  → kyc_status = EXPIRED triggers account restriction
  → Nightly job updates expired customers automatically
  → RETURNING clause captures the list for compliance team
```

### Audit Trail

```
□ Every application status change recorded with:
  → old_status and new_status
  → changed_at timestamp
  → changed_by (officer ID or system name)
  → change_reason (mandatory for rejections)
  → Rows are NEVER updated or deleted (append-only)

□ Every external API call logged in external_api_log:
  → service_name, endpoint, request_timestamp
  → response_timestamp, response_status
  → response_time_ms (for SLA monitoring)
  → customer_id or application_id reference
  → No raw PII in this table — references only

□ Every payment status change traceable
  → Payment status transitions documented
  → Compliance screening status recorded on payment row
```

### Capital and Concentration

```
□ Product quotas enforced in real time
  → product_quota table updated on every approval
  → v_product_availability view checked before every offer
  → Application 501 cannot be approved when max = 500

□ SAMA concentration limits tracked by product / sector
  → Approved exposure tracked in product_quota table
  → Reporting view shows current exposure vs limit
```

---

## PDPL Requirements Checklist

### Data Classification

```
□ Every column in every entity is classified:
  → 🔒 Restricted  : national_id, date_of_birth, income,
                      biometrics, health data
  → Confidential   : full_name, email, mobile, account balance,
                      payment details, beneficiary name
  → Internal        : customer_id, account_id, risk_rating,
                      payment_rail, transaction type
  → Public          : branch names, product names, exchange rates

□ Restricted columns:
  → Encrypted at rest
  → Masked in non-production environments
  → Access restricted by schema-level grants
  → Processing requires explicit consent or legal obligation
```

### Consent Management

```
□ CUSTOMER_CONSENT table exists with one row per purpose
□ Six processing purposes defined:
  → ACCOUNT_OPERATIONS   (legal basis: CONTRACT)
  → MARKETING_COMMS      (legal basis: CONSENT — can be withdrawn)
  → CREDIT_BUREAU_SHARE  (legal basis: LEGAL_OBLIGATION)
  → OPEN_BANKING_SHARE   (legal basis: CONSENT — can be withdrawn)
  → ANALYTICS_PROFILING  (legal basis: LEGITIMATE_INTEREST)
  → AML_COMPLIANCE       (legal basis: LEGAL_OBLIGATION)

□ consent_expiry populated where applicable
  → System checks expiry before processing under that consent
  → Marketing consent typically expires — not lifetime

□ Consent withdrawal handled immediately
  → withdrawn_at timestamp recorded
  → Processing stops immediately — not at next batch
  → Confirmation sent to customer
```

### Retention and Erasure

```
□ Retention periods defined for every entity:
  → Customer PII: 10 years post account closure
  → Transaction records: 10 years (SAMA mandate)
  → KYC records: 10 years post account closure
  → AML records: 10 years minimum
  → Marketing consents: retain withdrawal record permanently

□ Right to erasure (PDPL Article 18) documented:
  → Erasure does NOT apply when SAMA legal hold is active
  → legal_hold flag prevents automated purge on protected records
  → Erasure applies to marketing data and non-obligatory data
  → Process for handling erasure requests defined

□ Automated purge process defined:
  → Runs only on records past retention period
  → Skips records with legal_hold = TRUE
  → Audit log of what was purged and when
```

### Data Minimisation

```
□ Reporting views contain only the columns needed:
  → Aggregated views (risk summary) contain no PII
  → Named views (overdue report) include names only
    where the use case requires it
  → Marketing views exclude financial data

□ Non-production environments contain no real PII:
  → Synthetic data generation pipeline defined
  → National IDs tokenised in dev and test
  → No production data copied to lower environments

□ external_api_log stores references — never raw data:
  → customer_id reference, not national_id
  → application_id reference, not personal details
  → Error messages contain no PII
```

### Third-Party Data

```
□ Beneficiary names on payments classified as Confidential:
  → Third-party personal data received incidentally
  → PDPL applies to third-party data of Saudi residents
  → Access restricted to authorised payment operations staff

□ SIMAH credit data not stored beyond what is needed:
  → Score stored (credit_bureau_score column)
  → Full bureau report not persisted in the schema
  → Reference to SIMAH query stored in external_api_log

□ Nafath data handled at the boundary:
  → Verification result (nafath_verified BOOLEAN) stored
  → Raw NID and biometric payload not stored in operational DB
  → Stays in secured KYC system with restricted access
```

### Access Control

```
□ Schema separation enforces access at the database layer:
  → compliance schema: compliance team only
  → finance schema: finance and risk teams
  → retail schema: operational teams
  → analytics schema: reporting and BI teams
  → staging schema: data engineering only

□ Role-based grants defined per schema:
  → GRANT SELECT ON ALL TABLES IN SCHEMA compliance
    TO compliance_role
  → No cross-schema access without explicit grant

□ No SELECT * in application queries:
  → Specific columns listed in every query
  → Views expose only the columns required for each role
```

---

> **Keep this checklist open as you work.**
>
> These are not hypothetical obligations. Every Saudi bank
> operating under SAMA supervision is subject to these requirements.
> Every organisation processing personal data of Saudi residents
> is subject to PDPL.
>
> The architecture you design either satisfies these requirements
> or it does not. A checklist item left unchecked today becomes
> a finding in a SAMA examination or a PDPL investigation tomorrow.
>
> Design it right from the start. Retrofitting compliance into
> a production system is one of the most expensive things a
> bank can do.

---

*SNB Data Management Capability Programme | Delivered by Fitch Learning*