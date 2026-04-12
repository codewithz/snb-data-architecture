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