# Day 4 — Understanding the Problem Statement
## Al-Noor Digital Retail Banking Platform
### Read This Before You Start the Labs

---

> **Why this document exists.**
>
> Day 4 asks you to design a real banking data architecture
> from scratch — across five domains, three labs, and multiple
> regulatory constraints.
>
> Many participants find themselves confused not because
> the work is too hard — but because they are not sure
> what they are building, why each piece exists, and
> what the labs are actually asking them to produce.
>
> This document answers all of that before you begin.
> Read it fully. It will make everything else clearer.

---

## Section 1 — What Is Al-Noor Bank?

Al-Noor Bank is a fictional Saudi retail bank created
for this programme. It is fictional so we can design freely —
but everything about it is real:

- Real Saudi regulatory frameworks (SAMA, PDPL, ZATCA)
- Real Islamic finance products (Murabaha, Tawarruq, Ijara)
- Real Saudi payment infrastructure (SARIE, SADAD, mada, SWIFT)
- Real external services (Nafath, SIMAH, OFAC)

When you design for Al-Noor Bank today, you are designing
the kind of system that every Saudi retail bank either
already has or urgently needs.

---

## Section 2 — What Problem Are We Solving?

### The Situation

Al-Noor Bank has decided to launch a **Digital Retail Banking Platform**.

Until now, customers visited a branch for everything —
opening accounts, applying for financing, making complex payments.
The bank wants to move this entirely online and to mobile.

### Why This Is Hard

Behind every "Apply Now" button on a mobile app sits a data
architecture that must handle all of the following simultaneously:

```
┌─────────────────────────────────────────────────────────────┐
│              WHAT THE PLATFORM MUST DO                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  IDENTITY      Verify every customer through Nafath         │
│                (Ministry of Interior eKYC) before           │
│                any account can be opened                    │
│                                                             │
│  COMPLIANCE    Screen every customer and payment against    │
│                OFAC and UN sanctions lists before           │
│                any transaction is processed                 │
│                                                             │
│  CREDIT        Query SIMAH (Saudi Credit Bureau) for        │
│                every financing application                  │
│                Score range: 300 to 900                      │
│                                                             │
│  CONSENT       Record every PDPL consent the customer       │
│                gives — which data, for what purpose,        │
│                under which legal basis                      │
│                                                             │
│  PAYMENTS      Route money through the correct Saudi        │
│                payment rail — SARIE for SAR transfers,      │
│                SADAD for bills, SWIFT for international     │
│                                                             │
│  ISLAMIC FIN   Generate Murabaha repayment schedules that   │
│                satisfy Sharia Supervisory Board rules        │
│                                                             │
│  REPORTING     Send daily, weekly, and monthly reports      │
│                to SAMA — on time, every time                │
│                                                             │
│  RETENTION     Keep all data for 10 years (SAMA mandate)   │
│                                                             │
│  PERFORMANCE   Answer balance queries in under 100ms        │
│                Handle 500,000 transactions per day          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**This is not a technology problem. It is a data architecture problem.**

The application code is only as good as the data model underneath it.
A wrong data model cannot be fixed by good code.
It can only be fixed by redesigning the model — on a live system,
with real customer data, under regulatory scrutiny.

**You are the Lead Data Architect. The model is your responsibility.**

---

## Section 3 — Why Should You Care?

These are not hypothetical problems. They happen at Saudi banks.
Here are three real scenarios — the same kind you will face
in your role — and how the right data architecture changes
the outcome.

---

### Scenario A — The SAMA Supervisory Review

A SAMA examiner visits and asks one question:

> *"Show me the complete record for application APP-2024-0847.
> Who reviewed it? When did each status change?
> What was the Nafath verification result?"*

```
WITHOUT the right architecture:

  System shows:    Status = REJECTED
  History:         Not captured
  Nafath log:      Does not exist
  Officer trail:   Unknown

  Result:
  → SAMA raises a supervisory finding
  → Bank must remediate on a live production system
    with hundreds of thousands of active applications
  → Weeks of engineering work
  → Regulatory risk

─────────────────────────────────────────────────────

WITH the right architecture:

  APPLICATION_STATUS_HISTORY shows:
    SUBMITTED    → 2024-03-10 09:14:22  system
    UNDER_REVIEW → 2024-03-10 09:15:01  AML_SYSTEM
    REJECTED     → 2024-03-10 11:32:45  OFFICER_A42
                   Reason: AML_FLAGGED

  EXTERNAL_API_LOG shows:
    Nafath call:  2024-03-10 09:14:28  SUCCESS  847ms
    OFAC screen:  2024-03-10 09:14:31  FLAGGED  312ms

  Result:
  → Examiner's question answered in 30 seconds
  → No finding. No remediation. No risk.
```

The difference is **one table** — `application_status_history` —
that either exists in the schema or does not.
That is a Day 4 design decision.

---

### Scenario B — The PDPL Erasure Request

A customer calls and says:

> *"I want all my personal data deleted from your systems."*

```
WITHOUT the right architecture:

  Nobody knows:
  → Which tables contain this customer's data
  → Which data is under SAMA legal hold (cannot delete)
  → Which data can legally be erased
  → What the customer originally consented to

  Result:
  → Response takes weeks
  → May be incorrect or incomplete
  → PDPL violation risk
  → Regulatory fine

─────────────────────────────────────────────────────

WITH the right architecture:

  CUSTOMER_CONSENT table shows:
    ACCOUNT_OPERATIONS   → legal basis: CONTRACT
                           cannot erase (legal obligation)
    MARKETING_COMMS      → legal basis: CONSENT
                           can erase immediately
    AML_COMPLIANCE       → legal basis: LEGAL_OBLIGATION
                           cannot erase (SAMA 10-year mandate)

  PDPL classification on every column identifies:
  → What is Restricted (encrypt + erase)
  → What is under legal hold (retain, cannot touch)

  Result:
  → Accurate response delivered within PDPL timeframe
  → Customer's erasable data removed
  → Protected data retained correctly with documentation
  → Zero violation risk
```

The `customer_consent` table and PDPL column classifications
are Day 4 design decisions.

---

### Scenario C — The Sharia Compliance Failure

The Islamic Finance team launches a new Murabaha product.
Two weeks later, internal audit discovers 47 contracts were
issued without a Sharia Supervisory Board approval reference.

```
WITHOUT the right architecture:

  The product table allows:
    is_sharia_compliant = TRUE
    ssb_approval_ref    = NULL   ← No constraint stops this

  A developer oversight in application code skipped
  the validation check. 47 invalid contracts were created.

  Result:
  → Contracts may be invalid under Sharia law
  → Customer notification required
  → SSB must review all 47 cases
  → SAMA may be informed
  → Weeks of remediation

─────────────────────────────────────────────────────

WITH the right architecture:

  The product table has this CHECK constraint:
    CHECK (
      is_sharia_compliant = FALSE
      OR ssb_approval_ref IS NOT NULL
    )

  The developer's mistake hits the constraint.
  The INSERT is rejected before anything reaches production.
  Zero invalid contracts.

  Result:
  → The wrong state is structurally impossible to represent
  → No audit finding. No remediation. No customer impact.
```

This CHECK constraint is a Day 4 design decision.

---

### The Pattern

```
  Every one of these scenarios follows the same structure:

  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │  A problem that looks like an operations or         │
  │  compliance problem is actually a data              │
  │  architecture problem in disguise.                  │
  │                                                     │
  │  The architecture decision was made — or not made   │
  │  — years earlier.                                   │
  │                                                     │
  │  The consequence arrives during a SAMA audit,       │
  │  a customer complaint, or a regulatory deadline.    │
  │                                                     │
  │  Today you make those decisions.                    │
  │                                                     │
  └─────────────────────────────────────────────────────┘
```

---

## Section 4 — What Are the Five Domains?

The Al-Noor platform is divided into five business domains.
Each domain owns specific data and has a named Business Data Owner.

```
┌─────────────────────────────────────────────────────────────────┐
│             THE FIVE DOMAINS — OVERVIEW                         │
├──────────────┬──────────────────────────────┬───────────────────┤
│   Domain     │       What It Owns           │  Business Owner   │
├──────────────┼──────────────────────────────┼───────────────────┤
│  Product     │ What the bank can sell       │ Head of Product   │
│              │ Categories, products,        │ Management        │
│              │ pricing, Sharia approval     │                   │
├──────────────┼──────────────────────────────┼───────────────────┤
│  Customer    │ Who the bank sells to        │ Head of Retail    │
│              │ Individuals, corporates,     │ Banking / CCO     │
│              │ KYC records, PDPL consents   │                   │
├──────────────┼──────────────────────────────┼───────────────────┤
│  Orders      │ Product application lifecycle│ Head of Digital   │
│              │ From SUBMITTED to FULFILLED  │ Onboarding        │
│              │ Immutable audit trail        │                   │
├──────────────┼──────────────────────────────┼───────────────────┤
│  Inventory   │ Capacity and availability    │ Head of Product   │
│              │ Product quotas, SAMA caps    │ Management / Risk │
│              │ Availability windows         │                   │
├──────────────┼──────────────────────────────┼───────────────────┤
│  Payments    │ How money moves              │ Head of Treasury  │
│              │ SARIE, SADAD, SWIFT, mada   │ / Payments        │
│              │ Sanctions screening results  │                   │
└──────────────┴──────────────────────────────┴───────────────────┘

Cutting across ALL five domains without exception:
KYC · AML · PDPL compliance · SAMA reporting
```

---

### Domain 1 — Product

**The catalogue of everything Al-Noor Bank can sell.**

```
  PRODUCT_CATEGORY
       │
       │  one category → many products
       ▼
    PRODUCT
       │  ├── product_name_en  (English)
       │  ├── product_name_ar  (Arabic — requires UTF8)
       │  ├── is_sharia_compliant
       │  └── ssb_approval_ref  ← CHECK constraint:
       │                          if Islamic, this CANNOT be NULL
       │
       ├──── PRODUCT_TERMS  (versioned — rate changes over time)
       │         └── PRODUCT_PRICING  (varies by customer segment)
       │
       └──── PRODUCT_QUOTA  (belongs to Inventory Domain)
```

**The critical constraint:**

```sql
-- This constraint makes Sharia compliance structurally enforced
-- It cannot be bypassed by application code

CONSTRAINT chk_sharia_approval CHECK (
    is_sharia_compliant = FALSE
    OR ssb_approval_ref IS NOT NULL
)

-- Translation:
-- If the product is NOT Islamic → ssb_approval_ref can be NULL
-- If the product IS Islamic     → ssb_approval_ref MUST exist
-- The database enforces this. Always. Without exception.
```

---

### Domain 2 — Customer

**The single source of truth for customer identity.**

The most important design decision in this domain:
**single table versus parent + subtype.**

```
WRONG approach — single table with discriminator:

┌────────────────────────────────────────────────────────────────────┐
│ cust_id │ type │ national_id │ company_name │ gosi_id │ cr_number  │
├────────────────────────────────────────────────────────────────────┤
│ C00001  │  I   │ 12345678901 │    NULL      │  NULL   │   NULL     │
│ C00002  │  C   │    NULL     │ Al-Rajhi Co  │ G000001 │ 1234567890 │
│ C00003  │  I   │ 98765432109 │    NULL      │  NULL   │   NULL     │
└────────────────────────────────────────────────────────────────────┘

Problems:
→ Individual rows: company_name, gosi_id, cr_number always NULL
→ Corporate rows: national_id always NULL
→ Every query must remember to filter on type
→ Developer forgets → wrong results → data quality failure
→ The schema allows inserting impossible combinations


RIGHT approach — parent + subtype:

┌─────────────────────────────────────────────────────┐
│                   CUSTOMER (parent)                  │
│  customer_id │ kyc_status │ risk_rating │ is_pep ... │
└──────────────────────┬──────────────────────────────┘
                       │  shared PK (1:1 relationship)
           ┌───────────┴───────────┐
           ▼                       ▼
┌──────────────────────┐  ┌──────────────────────────┐
│  INDIVIDUAL_CUSTOMER │  │   CORPORATE_CUSTOMER     │
│  🔒                  │  │                          │
│  national_id         │  │  commercial_reg_no       │
│  date_of_birth       │  │  vat_number (ZATCA)      │
│  monthly_income_sar  │  │  gosi_establishment_id   │
│  employer_name       │  │  authorised_signatory_id │
└──────────────────────┘  └──────────────────────────┘

Benefits:
→ Individual columns only exist for individuals
→ Corporate columns only exist for corporates
→ The wrong state is structurally impossible
→ No query needs a type discriminator filter
→ Clean, unambiguous, maintainable
```

**Supporting entities in the Customer Domain:**

```
CUSTOMER
    │
    ├── INDIVIDUAL_CUSTOMER 🔒  (NID, DOB, income)
    ├── CORPORATE_CUSTOMER      (CR number, GOSI, VAT)
    │
    ├── KYC_RECORD 🔒
    │     One row per review. Never overwritten.
    │     SAMA audit trail of every KYC decision.
    │
    ├── CUSTOMER_CONTACT 🔒
    │     Mobile, email, address. Separately stored
    │     so access can be restricted per PDPL.
    │
    ├── CUSTOMER_DOCUMENT 🔒
    │     ID scans, proof of income, bank statements.
    │
    ├── CUSTOMER_CONSENT           ← THE PDPL ENTITY
    │     One row per processing purpose.
    │     Legal basis documented for every data use.
    │     Evidence of compliance — not a policy document.
    │
    └── CUSTOMER_RELATIONSHIP
          Joint accounts, power of attorney, guardianship.
```

**The CUSTOMER_CONSENT table — why it is a core entity:**

```
Processing purpose          Legal basis            Can be refused?
────────────────────────────────────────────────────────────────
ACCOUNT_OPERATIONS     →  CONTRACT            →  No (needed for service)
MARKETING_COMMS        →  CONSENT             →  Yes (must be revocable)
CREDIT_BUREAU_SHARE    →  LEGAL_OBLIGATION    →  No (SAMA requirement)
OPEN_BANKING_SHARE     →  CONSENT             →  Yes (anytime)
AML_COMPLIANCE         →  LEGAL_OBLIGATION    →  No (mandatory)
ANALYTICS_PROFILING    →  LEGITIMATE_INTEREST →  Yes (with justification)

When a customer says "delete my data" or "stop marketing to me":
→ This table tells you EXACTLY what can be stopped and what cannot
→ The withdrawn_at timestamp is the evidence of compliance
→ Without this table, the answer is guesswork
```

---

### Domain 3 — Orders

**The lifecycle of a product application.**

In banking, an "Order" is a product application —
a customer's request to open an account or apply for financing.

```
Customer submits via mobile app
            │
            ▼
     ┌─────────────┐
     │  SUBMITTED  │──── Three automated checks fire immediately:
     └──────┬──────┘     → Nafath eKYC verification
            │            → OFAC / UN sanctions screening
            │            → SIMAH credit check (financing only)
            │
            ▼            Each check = one row in external_api_log
     ┌──────────────────┐
     │   UNDER_REVIEW   │──── Officer sees application +
     └────────┬─────────┘     all compliance check results
              │
       ┌──────┴──────┐
       ▼             ▼
  ┌──────────┐  ┌──────────┐
  │ APPROVED │  │ REJECTED │──── Reason recorded. Officer ID recorded.
  └────┬─────┘  └──────────┘     Timestamp recorded. Immutable.
       │
       ▼
  ┌───────────┐
  │ FULFILLED │──── Account created (account table)
  └───────────┘     Contract created (murabaha_contract table)
                    Schedule created (murabaha_schedule table)
                    Quota decremented (product_quota table)

EVERY status transition above = ONE ROW in:
application_status_history (old_status, new_status, changed_by,
                             changed_at, change_reason)

This table is APPEND ONLY.
No updates. No deletes. Ever.
It is the audit trail that SAMA will examine.
```

---

### Domain 4 — Inventory

**The capacity and availability of financial products.**

In retail, inventory is physical stock. In banking, inventory
is the capacity to issue financial products — governed by
SAMA capital adequacy rules.

```
Without inventory management:
  A successful digital marketing campaign runs on a Monday.
  10,000 Murabaha Home Finance applications arrive.
  All 10,000 are approved automatically.
  Total exposure: SAR 5 billion — above the regulatory capital limit.
  SAMA breach. Emergency capital raise.

With inventory management:
  The product_quota table for Murabaha Home Finance Q1 2025:
  max_exposure_sar:     SAR 500,000,000
  approved_amount_sar:  SAR 497,200,000  ← updated on every approval
  remaining:            SAR   2,800,000  ← real time

  Application 2,487 arrives requesting SAR 3,000,000.
  v_product_availability view returns: QUOTA_FULL
  The product is hidden from the application flow.
  Application 2,487 is never submitted.
  No breach. No emergency. No risk.
```

```
PRODUCT_QUOTA table:

┌──────────────┬────────────────┬──────────────┬────────────────┐
│  product_id  │ max_applications│ approved_count│    status      │
├──────────────┼────────────────┼──────────────┼────────────────┤
│ PROD_MRB_002 │     500        │     347      │   OPEN         │
│ PROD_TAW_001 │    NULL        │     891      │   OPEN         │
│ PROD_MRB_001 │    2000        │    2000      │   CLOSED       │
└──────────────┴────────────────┴──────────────┴────────────────┘

NULL in max_applications = unlimited (no quota for this product)
2000/2000 = CLOSED (quota exhausted for this period)

v_product_availability view:
→ Calculates remaining capacity in real time
→ Returns availability_status: AVAILABLE / QUOTA_FULL / SUSPENDED
→ The digital onboarding system queries this BEFORE showing
  a product to a customer
```

---

### Domain 5 — Payments

**How money moves — and the data architecture that tracks it.**

Saudi Arabia has six payment rails. Each is structurally different.
Each requires different reference numbers. Each has different
SAMA reporting requirements.

```
┌───────────┬────────────────────────────┬──────────────┬──────────────────┐
│   Rail    │         Use Case           │  Settlement  │  Reference Field │
├───────────┼────────────────────────────┼──────────────┼──────────────────┤
│  SARIE    │ SAR interbank transfers    │  Real-time   │  sarie_uetr      │
│           │ between Saudi banks        │  24/7        │  (UUID format)   │
├───────────┼────────────────────────────┼──────────────┼──────────────────┤
│  SADAD    │ Utility bills, govt fees,  │  Same day    │  sadad_ref       │
│           │ insurance, GOSI payments   │              │  (different fmt) │
├───────────┼────────────────────────────┼──────────────┼──────────────────┤
│   mada    │ POS and ATM transactions   │  Real-time   │  mada_txn_id     │
│           │ Saudi debit card network   │              │                  │
├───────────┼────────────────────────────┼──────────────┼──────────────────┤
│  SWIFT    │ International transfers    │  1–5 days    │  swift_uetr      │
│           │ (ISO 20022 standard)       │              │  (ISO 20022 fmt) │
├───────────┼────────────────────────────┼──────────────┼──────────────────┤
│  STC Pay  │ Mobile wallet payments     │  Real-time   │  wallet_ref      │
│  Apple Pay│                            │              │                  │
├───────────┼────────────────────────────┼──────────────┼──────────────────┤
│ Internal  │ Transfers within           │  Instant     │  internal_ref    │
│           │ Al-Noor Bank               │              │                  │
└───────────┴────────────────────────────┴──────────────┴──────────────────┘

WHY THIS CANNOT BE ONE GENERIC reference_no COLUMN:

  A SARIE UETR looks like:  f47ac10b-58cc-4372-a567-0e02b2c3d479
  A SADAD reference looks like: 1234567890123456
  A SWIFT UETR follows:     ISO 20022 format with check digits

  These are structurally different. They serve different purposes.
  They are reported to SAMA separately.

  The payment table needs:
    sarie_uetr   VARCHAR(50)  — populated for SARIE, NULL for others
    swift_uetr   VARCHAR(50)  — populated for SWIFT, NULL for others

  One typed nullable column per rail.
  Not one generic column trying to serve all six.
```

---

## Section 5 — How the Five Domains Connect

This is the diagram most participants miss in Lab 4A.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    CROSS-DOMAIN RELATIONSHIPS                            │
│                                                                          │
│                                                                          │
│  ┌─────────────────────┐          ┌──────────────────────────────────┐  │
│  │   PRODUCT DOMAIN    │          │        CUSTOMER DOMAIN           │  │
│  │                     │          │                                  │  │
│  │  PRODUCT_CATEGORY   │          │  CUSTOMER (parent)               │  │
│  │         │           │          │      ├── INDIVIDUAL_CUSTOMER 🔒  │  │
│  │         ▼           │          │      ├── CORPORATE_CUSTOMER      │  │
│  │      PRODUCT        │          │      ├── KYC_RECORD 🔒           │  │
│  │      PRODUCT_TERMS  │          │      ├── CUSTOMER_CONSENT        │  │
│  │      PRODUCT_PRICING│          │      └── CUSTOMER_CONTACT 🔒     │  │
│  │                     │          │                                  │  │
│  │      PRODUCT_QUOTA ─┼──────────┼──► (updated on every approval)  │  │
│  │  (Inventory Domain) │          │                                  │  │
│  └──────────┬──────────┘          └────────────────┬─────────────────┘  │
│             │                                       │                    │
│             │          ┌────────────────────────────┘                   │
│             │          │                                                 │
│             ▼          ▼                                                 │
│  ┌─────────────────────────────────────────────────┐                    │
│  │                  ORDERS DOMAIN                  │                    │
│  │                                                 │                    │
│  │  PRODUCT_APPLICATION                            │                    │
│  │      references PRODUCT  (what they applied for)│                    │
│  │      references CUSTOMER (who applied)          │                    │
│  │                                                 │                    │
│  │  APPLICATION_STATUS_HISTORY (immutable trail)   │                    │
│  │                                                 │                    │
│  │  On FULFILLED:                                  │                    │
│  │      WRITE → account          (Customer Domain) │                    │
│  │      WRITE → murabaha_contract (Finance)        │                    │
│  │      WRITE → murabaha_schedule (Finance)        │                    │
│  └─────────────────────────────────────────────────┘                    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     PAYMENTS DOMAIN                             │    │
│  │                                                                 │    │
│  │  PAYMENT                                                        │    │
│  │      references CUSTOMER  (who initiated the payment)           │    │
│  │      references ACCOUNT   (debit_account_id)                    │    │
│  │                                ▲                                │    │
│  │                                │                                │    │
│  │          ┌─────────────────────┘                                │    │
│  │          │                                                       │    │
│  │   ACCOUNT lives in the CUSTOMER DOMAIN ◄── THIS IS THE MOST    │    │
│  │   The Payments Domain REFERENCES it        MISSED DEPENDENCY    │    │
│  │   The Payments Domain does NOT OWN it      IN LAB 4A            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**The most important rule about cross-domain dependencies:**

```
  A domain can REFERENCE data from another domain.
  A domain cannot OWN data from another domain.

  PAYMENT references ACCOUNT — correct.
  PAYMENT owns ACCOUNT — wrong.

  This distinction determines:
  → Who is responsible for ACCOUNT data quality
  → Which team can modify ACCOUNT data
  → Which system is the System of Record for ACCOUNT
  → How access control is structured in production
```

---

## Section 6 — The External Services

Al-Noor Bank connects to six external services.
Every call to every service must be logged.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICE CONNECTIONS                      │
└──────────────────────────────────────────────────────────────────────┘

                        ┌─────────────────┐
                        │  AL-NOOR BANK   │
                        └────────┬────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                       │
          ▼                      ▼                       ▼
    ┌──────────┐           ┌──────────┐           ┌───────────┐
    │  NAFATH  │           │  SIMAH   │           │   OFAC    │
    │          │           │          │           │  UN LIST  │
    │ Ministry │           │ Saudi    │           │           │
    │ of       │           │ Credit   │           │ Sanctions │
    │ Interior │           │ Bureau   │           │ PEP lists │
    │          │           │          │           │           │
    │ eKYC     │           │ Score    │           │ Pre-pay   │
    │ MANDATORY│           │ 300-900  │           │ MANDATORY │
    │ before   │           │ Financing│           │ every     │
    │ account  │           │ only     │           │ payment   │
    └──────────┘           └──────────┘           └───────────┘

          ┌──────────────────────┼──────────────────────┐
          │                      │                       │
          ▼                      ▼                       ▼
    ┌──────────┐           ┌──────────┐           ┌───────────┐
    │  SARIE   │           │  SADAD   │           │   ZATCA   │
    │          │           │          │           │           │
    │ SAMA     │           │ National │           │ Zakat Tax │
    │ payment  │           │ bills    │           │ Customs   │
    │ network  │           │ payment  │           │           │
    │          │           │ network  │           │ VAT and   │
    │ Returns  │           │          │           │ Zakat     │
    │ UETR     │           │ Returns  │           │ reporting │
    │ reference│           │ SADAD ref│           │           │
    └──────────┘           └──────────┘           └───────────┘

ALL SIX SERVICES → every call → one row in external_api_log

external_api_log contains:
  service_name        which service was called
  endpoint            which API endpoint
  customer_id         which customer this relates to
  request_timestamp   when the call was made
  response_timestamp  when the response arrived
  response_time_ms    how long it took (SLA monitoring)
  response_status     SUCCESS / FAILED / TIMEOUT
  error_code          if failed, why

CRITICAL: raw PII (NID, biometrics) is NEVER stored in this table.
Only reference IDs. The sensitive data stays in the KYC system
with restricted access.

WHY THIS MATTERS:
SAMA supervisory reviews ask: "Show me the Nafath verification
log for application APP-2025-0042."
Without external_api_log: the answer is silence.
Silence in a SAMA review is a supervisory finding.
```

---

## Section 7 — What Each Lab Is Asking You to Produce

Now that you understand what you are building, here is exactly
what success looks like in each lab.

---

### Lab 4A — Conceptual and Logical ERD 

**You are producing:** A diagram. One diagram covering all five
domains on a single page — drawn in draw.io, dbdiagram.io, or on paper.

**What a complete diagram contains:**

```
┌──────────────────────────────────────────────────────────────┐
│  PRODUCT DOMAIN        │  CUSTOMER DOMAIN                    │
│  ┌──────────────────┐  │  ┌──────────────────────────────┐  │
│  │ PRODUCT_CATEGORY │  │  │ CUSTOMER (parent)            │  │
│  │ PRODUCT          │  │  │ INDIVIDUAL_CUSTOMER 🔒       │  │
│  │ PRODUCT_TERMS    │  │  │ CORPORATE_CUSTOMER           │  │
│  │ PRODUCT_PRICING  │  │  │ KYC_RECORD 🔒                │  │
│  └──────────────────┘  │  │ CUSTOMER_CONSENT             │  │
│                        │  │ CUSTOMER_CONTACT 🔒          │  │
│  INVENTORY DOMAIN      │  └──────────────────────────────┘  │
│  ┌──────────────────┐  │                                     │
│  │ PRODUCT_QUOTA    │  │  ORDERS DOMAIN                      │
│  └──────────────────┘  │  ┌──────────────────────────────┐  │
│                        │  │ PRODUCT_APPLICATION          │  │
│  PAYMENTS DOMAIN       │  │ APPLICATION_STATUS_HISTORY   │  │
│  ┌──────────────────┐  │  │ MURABAHA_CONTRACT            │  │
│  │ PAYMENT 🔒       │  │  │ MURABAHA_SCHEDULE            │  │
│  └──────────────────┘  │  └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘

Arrows between entities show relationships and direction.
🔒 marks PDPL-sensitive entities.
Domain boundaries are clearly visible.
```

**Three questions your diagram must answer:**

```
Question 1: Where does ACCOUNT live?
Correct answer: Customer Domain.
Common mistake: Payments Domain or Orders Domain.

Question 2: Which entity most people forget?
Correct answer: APPLICATION_STATUS_HISTORY
It is not glamorous. It is essential.

Question 3: Does KYC belong in Customer or Compliance?
Both answers are defensible.
You must choose one and write down why.
The reasoning matters more than the choice.
```

**Systems of Record — one per domain:**

```
Product Domain    → Product Management System (PMS)
Customer Domain   → CRM + KYC Platform (Nafath-verified)
Orders Domain     → Digital Onboarding Platform
Inventory Domain  → Risk Management System
Payments Domain   → Payment Processing System

NOT the data warehouse — that is a copy, not a source.
NOT "the database" — that is a storage location, not a system.
```

---

### Lab 4B — Attribute Dictionary 

**You are producing:** A governance document — one row per column
in INDIVIDUAL_CUSTOMER and PAYMENT — defining what each column
means, how it is classified, and how long it is retained.

**The template:**

```
┌────────────────┬───────────────┬───────────────────────────┬──────────────┬──────────────┬──────────────┬─────────────────┬────────────────┐
│  Attribute     │ Business Name │  Definition               │  Data Type   │ Constraints  │  PDPL Class  │   Retention     │ Source System  │
├────────────────┼───────────────┼───────────────────────────┼──────────────┼──────────────┼──────────────┼─────────────────┼────────────────┤
│ customer_id    │ Customer CIF  │ Bank-assigned unique ID    │ CHAR(10)     │ PK, NOT NULL │ Internal     │ Lifetime        │ CBS            │
│ national_id    │ NID / Iqama   │ Saudi NID (10 digits) or  │ VARCHAR(15)  │ NOT NULL,    │ 🔒 Restricted│ 10 yrs post     │ Nafath         │
│                │               │ Iqama number              │              │ UNIQUE       │              │ account closure │                │
└────────────────┴───────────────┴───────────────────────────┴──────────────┴──────────────┴──────────────┴─────────────────┴────────────────┘
```

**The four debates you must resolve correctly:**

```
DEBATE 1: monthly_income_sar
  Wrong answer: Confidential
  Right answer: 🔒 Restricted
  Why: It reveals financial circumstances — a higher
       protection category than Confidential under PDPL.
       Restricted data requires explicit consent and
       encryption at rest.

DEBATE 2: beneficiary_name on a payment
  Wrong answer: Internal
  Right answer: Confidential
  Why: The beneficiary is a THIRD PARTY who has NOT consented
       to Al-Noor processing their data. PDPL obligations
       extend to third-party personal data received incidentally.

DEBATE 3: payment_rail
  Wrong answer: Public or Internal (unclassified)
  Right answer: Internal
  Why: It reveals the customer's banking behaviour pattern.
       Frequent SWIFT usage signals international activity.
       Behavioural data is personal data under PDPL.

DEBATE 4: source_system for national_id
  Wrong answer: Database / System / CRM
  Right answer: Nafath
  Why: The database is where data is stored.
       Nafath is where the data is CREATED and verified.
       The source system is the system of creation,
       not the system of storage.
```

**Retention periods reference:**

```
national_id, transaction data   → 10 years (SAMA AML mandate)
consent records                 → Lifetime of consent + 5 years
AML alert data                  → 10 years minimum (SAMA)
marketing data                  → Until consent withdrawn

PDPL Article 18: right to erasure
PDPL Article 19: data must be disposed of after retention period
SAMA AML Rules:  legal hold overrides PDPL erasure for 10 years
```

---

### Lab 4C — Schema Validation 

**You are producing:** For each of three scenarios, a step-by-step
trace of every table that is read or written — in the correct order.

**What a good trace looks like:**

```
❌ NOT this (too vague):
   "The customer is onboarded and an account is opened"

✅ THIS (table-by-table, step-by-step):
   Step 1:  WRITE → customer (new row, kyc_status = PENDING)
   Step 2:  WRITE → individual_customer (NID, DOB from Nafath)
   Step 3:  WRITE → external_api_log (Nafath call — INITIATED)
   Step 4:  READ  → Nafath API (external identity verification)
   Step 5:  UPDATE→ external_api_log (result received, 847ms)
   Step 6:  WRITE → kyc_record (outcome = PASS, expiry set)
   Step 7:  UPDATE→ customer (kyc_status = VERIFIED)
   Step 8:  WRITE → customer_consent (ACCOUNT_OPERATIONS / CONTRACT)
   Step 9:  READ  → v_product_availability (confirm AVAILABLE)
   Step 10: WRITE → product_application (status = SUBMITTED)
   Step 11: WRITE → application_status_history (SUBMITTED)
   Step 12: WRITE → external_api_log (OFAC screening — INITIATED)
   Step 13: UPDATE→ product_application (aml_check_status = CLEAR)
   Step 14: UPDATE→ product_application (status = APPROVED)
   Step 15: WRITE → application_status_history (APPROVED)
   Step 16: WRITE → account (status = ACTIVE)
   Step 17: WRITE → customer_account (relationship = PRIMARY)
   Step 18: UPDATE→ product_application (status = FULFILLED)
   Step 19: WRITE → application_status_history (FULFILLED)
   Step 20: UPDATE→ product_quota (approved_count + 1)
```

**The three scenarios at a glance:**

```
SCENARIO 1 — New Customer Digital Onboarding
A Saudi national applies for a Tawarruq Account via mobile app.

Key tables to trace:
customer → individual_customer → external_api_log (Nafath)
→ kyc_record → customer_consent → product_application
→ application_status_history → account → customer_account
→ product_quota

─────────────────────────────────────────────────────────────

SCENARIO 2 — Murabaha Home Finance Application (SAR 500,000)
An existing PREMIUM customer applies for home financing.

Key tables to trace:
external_api_log (OFAC + Nafath + SIMAH) → product_application
→ application_status_history (multiple transitions)
→ murabaha_contract → murabaha_schedule (240 rows for 20 years)
→ product_quota (exposure updated)

─────────────────────────────────────────────────────────────

SCENARIO 3 — AML-Flagged Payment (SAR 85,000)
A large payment triggers the AML system.

Key tables to trace:
payment (INITIATED) → external_api_log (OFAC screening)
→ aml_alert (OPEN) → payment (PENDING — held for review)
→ [officer review and decision]
→ payment (COMPLETED or REJECTED)
→ external_api_log (SARIE submission if approved)
```

---