# Data Architect's Framework: Business Requirement to Database Implementation
### A Practical Playbook for Banking & Financial Services

> *"A requirement without a model is just a wish. A model without a requirement is just art."*
> — Every battle-scarred Data Architect, ever.

---


## Table of Contents

### Part A — The Core Framework (Phase by Phase)

| # | Phase | Key Activity |
|---|-------|-------------|
| [1](#phase-1--understand-the-business-intent) | Understand the Business Intent | The five questions. Use case register. Assumption log. |
| [2](#phase-2--extract-entities-events-and-facts) | Extract Entities, Events and Facts | Noun → entity. Verb → event. Number → fact. EEF register. |
| [3](#phase-3--conceptual-data-model) | Conceptual Data Model | Technology-free ERD. Business glossary. Subject areas. |
| [4](#phase-4--choose-the-modeling-approach) | Choose the Modeling Approach | 3NF vs Star Schema vs Data Vault. Decision matrix. |
| [5](#phase-5--logical-data-model) | Logical Data Model | Attributes. Types. Constraints. Business rules. |
| [6](#phase-6--physical-data-model) | Physical Data Model | DDL. Partitioning. Indexing. Retention. |
| [7](#phase-7--governance-lineage--compliance) | Governance, Lineage & Compliance | PDPL. SAMA. Masking. Lineage. Audit. |
| [8](#phase-8--validate-against-requirements) | Validate Against Requirements | Traceability matrix. UAT. Reconciliation. |

---

### Part B — Domain Walkthroughs (Al-Noor Bank Case Study)

> A full end-to-end worked example across five banking domains —
> from the first business question to the final DDL.
> Each domain follows the same 8-step process. Read Payments first.

#### Domain Navigation Index

| Domain | Conceptual Model | Logical Model | Physical DDL | Scenario Trace |
|--------|-----------------|---------------|--------------|----------------|
| [Payments](#domain-1--payments) | [→ Conceptual](#payments--conceptual-model) | [→ Logical](#payments--logical-model) | [→ DDL](#payments--physical-ddl) | [→ Scenario](#payments--scenario-trace) |
| [Customer](#domain-2--customer) | [→ Conceptual](#customer--conceptual-model) | [→ Logical](#customer--logical-model) | [→ DDL](#customer--physical-ddl) | [→ Scenario](#customer--scenario-trace) |
| [Product](#domain-3--product) | [→ Conceptual](#product--conceptual-model) | [→ Logical](#product--logical-model) | [→ DDL](#product--physical-ddl) | [→ Scenario](#product--scenario-trace) |
| [Orders](#domain-4--orders) | [→ Conceptual](#orders--conceptual-model) | [→ Logical](#orders--logical-model) | [→ DDL](#orders--physical-ddl) | [→ Scenario](#orders--scenario-trace) |
| [Inventory](#domain-5--inventory) | [→ Conceptual](#inventory--conceptual-model) | [→ Logical](#inventory--logical-model) | [→ DDL](#inventory--physical-ddl) | [→ Scenario](#inventory--scenario-trace) |

#### Quick Reference — Key Design Decisions by Domain

| Domain | Most Important Decision | Why It Matters |
|--------|------------------------|----------------|
| Payments | UUID vs SERIAL for payment_id | Open Banking TPPs generate IDs externally — must be globally unique |
| Payments | Two boolean compliance flags (not one status) | AML and sanctions are independent checks — one can pass, one fail |
| Payments | Two separate UETR columns (SARIE + SWIFT) | Different regulatory references — a generic field cannot distinguish them |
| Customer | Parent + subtype model (Individual / Corporate) | Eliminates NULL columns; makes wrong state structurally impossible |
| Customer | CUSTOMER_CONSENT as a core entity | PDPL compliance is a database record, not a policy document |
| Customer | withdrawn_at timestamp (not a status column) | Captures the exact legal moment processing obligations changed |
| Product | SSB approval reference CHECK constraint | Islamic product without SSB reference is unenforced at application level |
| Product | Versioned PRODUCT_TERMS (effective + expiry dates) | Contracts must reference the terms active at signing — not today's terms |
| Orders | APPLICATION_STATUS_HISTORY is immutable | SAMA examiners must see exactly what happened — not a retrospective edit |
| Orders | total_sale_price CHECK constraint | Murabaha profit is fixed at inception — this cannot drift after signing |
| Inventory | SELECT FOR UPDATE on quota check | Prevents two concurrent transactions both seeing "one slot remaining" |
| Inventory | approved_count as a stored counter | Avoids expensive COUNT queries across 100K+ application rows on every page load |

---

### Part C — Appendices

| Appendix | Contents |
|----------|---------|
| [Appendix A](#appendix-a--architecture-decision-record-adr-template) | ADR Template — standard format for documenting every major decision |
| [Appendix B](#appendix-b--regulatory-quick-reference-saudi-banking) | Regulatory Quick Reference — SAMA, PDPL, IFRS 9, Basel III |
| [Appendix C](#appendix-c--deliverables-checklist-by-phase) | Deliverables Checklist — all outputs, owners, and approvers by phase |

---


## How to Use This Framework

This framework is designed to be **repeatable, technology-agnostic, and banking-aware**. It works whether you are building a new data warehouse from scratch, extending an existing one, or migrating a legacy system. Each phase has:

- **What you do** — the core activity
- **Why it matters** — the architectural reasoning
- **Inputs required** — what you need before starting
- **Outputs/deliverables** — what you produce
- **Banking-specific considerations** — SAMA, PDPL, IFRS 9, Basel III, AML nuances
- **Common mistakes** — traps that even experienced architects fall into
- **Checklist** — gate criteria before moving to the next phase

---

## The 8-Phase Framework at a Glance

```
Phase 1  →  Understand the Business Intent
Phase 2  →  Extract Entities, Events and Facts
Phase 3  →  Conceptual Data Model
Phase 4  →  Choose the Modeling Approach
Phase 5  →  Logical Data Model
Phase 6  →  Physical Data Model
Phase 7  →  Governance, Lineage & Compliance
Phase 8  →  Validate Against Requirements
         ↻  Iterate
```

---

## Phase 1 — Understand the Business Intent

### What You Do

Before a single box is drawn or a single table is named, you must fully understand **why** this requirement exists, **who** it serves, and **what decision or action** it enables. This is the most underestimated phase and the one most architects rush through.

Sit with the business stakeholders. Bring a blank page, not a laptop. Listen more than you speak.

### The Five Questions You Must Answer

1. **What business decision does this data support?**
   - Regulatory reporting? Fraud detection? Customer segmentation? Product P&L?
   - Each use case has a radically different data shape.

2. **Who are the consumers of this data?**
   - An analyst writing SQL? A BI tool rendering dashboards? An upstream system via API? A regulator receiving a file?
   - Consumers determine freshness, access patterns, and format requirements.

3. **What is the required data freshness?**
   - Real-time (< 1 second)? Near-real-time (< 5 minutes)? Daily batch? Monthly?
   - Freshness is one of the biggest cost and architecture drivers.

4. **What is the expected data volume and growth rate?**
   - Millions of transactions per day? Hundreds of millions? What is the 3-year growth projection?
   - Volume drives partitioning, indexing, and infrastructure choices.

5. **What are the regulatory or compliance obligations tied to this data?**
   - In Saudi banking: SAMA Data Management Framework, PDPL, IFRS 9, Basel III, FATF AML guidelines.
   - Compliance is non-negotiable and must be designed in, not bolted on.

### Inputs Required

- Business requirement document (BRD) or user story
- Access to subject matter experts (SMEs) — business analysts, compliance officers, operations leads
- Any existing reports, dashboards, or manual processes this replaces
- Relevant regulatory guidelines (SAMA circulars, PDPL articles)

### Outputs / Deliverables

- **Business Requirement Summary (BRS)** — a 1-2 page plain-English restatement of the requirement, confirmed by the business stakeholder
- **Use Case Register** — a table listing each use case, its consumer, freshness requirement, and regulatory flag
- **Assumption Log** — everything you assumed that was not explicitly stated, signed off by stakeholders

### Banking-Specific Considerations

- **SAMA Data Management Framework** requires that data used for regulatory reporting must have documented lineage, ownership, and quality thresholds.
- **PDPL (Personal Data Protection Law, Saudi Arabia)** requires that any personal data collected must have a stated and lawful purpose. If the requirement involves customer data, PII justification must be established here — not in Phase 7.
- **IFRS 9** requirements for Expected Credit Loss (ECL) models mean historical transaction data must be available for defined lookback periods (typically 3–5 years). Establish this at Phase 1.
- Watch for requirements that are really **three requirements in disguise** — e.g., "customer 360" often means operational CRM + regulatory reporting + fraud analytics. Split them early.

### Common Mistakes

- Accepting a vague requirement and hoping it becomes clearer during modeling. It won't.
- Skipping the "who consumes it" question. The same data looks very different when it serves an analyst versus a regulator versus a real-time fraud engine.
- Not documenting assumptions. When the model is questioned six months later, undocumented assumptions become your liability.
- Confusing a report requirement with a data requirement. A dashboard is a view. What you need to understand is what data underpins it.

### Phase 1 Exit Checklist

- [ ] Business intent is documented and confirmed by at least one business stakeholder
- [ ] All use cases are listed with consumers, freshness, and volume estimates
- [ ] Regulatory obligations are identified and linked to specific regulations
- [ ] All assumptions are documented and signed off
- [ ] Ambiguities are resolved or escalated

---

## Phase 2 — Extract Entities, Events and Facts

### What You Do

Now you parse the confirmed requirement **linguistically and analytically** to extract the raw building blocks of your data model. This is systematic, not creative — you are mining the text for structure that is already there.

Apply a simple rule:
- **Nouns** → Entities (things you need to store data about)
- **Verbs** → Events or Relationships (things that happen between entities)
- **Numbers and measures** → Facts or Metrics (what you want to count, sum, average, or analyse)
- **Adjectives and qualifiers** → Attributes (properties of entities)

### Example: Parsing a Banking Requirement

> *"The bank needs to track all customer transactions across accounts, calculate monthly interest accruals, and produce a regulatory report showing net exposure by product type for all corporate clients."*

**Entities extracted:**
- Customer
- Account
- Transaction
- Product
- Corporate Client (possibly a subtype of Customer)
- Regulatory Report

**Events extracted:**
- Customer makes Transaction
- Account accrues Interest
- Report is generated

**Facts extracted:**
- Transaction amount
- Transaction count
- Monthly interest accrual amount
- Net exposure (aggregated)

**Attributes extracted:**
- Product type
- Client classification (corporate vs retail)
- Accrual period (monthly)

### Build the Entity-Event-Fact (EEF) Register

| # | Element | Type | Source | Notes |
|---|---------|------|--------|-------|
| 1 | Customer | Entity | Core Banking | Includes individual and corporate |
| 2 | Account | Entity | Core Banking | Multiple types: savings, current, loan |
| 3 | Transaction | Entity / Event | Transaction System | High volume, append-only |
| 4 | Interest Accrual | Event | GL System | Monthly batch |
| 5 | Transaction Amount | Fact | Transaction System | In SAR, with FX conversion needed |
| 6 | Net Exposure | Fact (Derived) | Calculated | Aggregated, not stored at transaction level |
| 7 | Product Type | Attribute | Product Catalogue | Slowly Changing |

### Identify Data Sources

For each entity or fact, trace it back to a source system:

- **Core Banking System (CBS)** — accounts, customers, balances
- **Transaction Processing System** — payment and transfer transactions
- **General Ledger (GL)** — accruals, journal entries
- **CRM System** — customer demographics, relationship data
- **Credit Risk System** — exposure, ratings, ECL parameters
- **Sanctions / AML System** — watchlist flags, case data

Document the source system, the system of record (the authoritative source), and any known data quality issues.

### Identify Data Gaps

At this stage you will often find data that the business needs but that no system currently captures. Document these as **data gaps** — they may require new data collection processes, API integrations, or manual uploads.

### Inputs Required

- Confirmed Business Requirement Summary from Phase 1
- Access to system catalogues, data dictionaries, or existing ERDs from source systems
- SME who knows where the data lives operationally

### Outputs / Deliverables

- **Entity-Event-Fact (EEF) Register** — complete table of all extracted elements
- **Source System Map** — which system owns which entity or fact
- **Data Gap Register** — data needed but not currently captured anywhere

### Banking-Specific Considerations

- In banking, the **same entity often exists in multiple systems with different representations**. A "Customer" in the CBS may have a different identifier format than in the CRM. Document these discrepancies now — they become your integration challenge.
- **Transaction** in banking is a heavily overloaded term. Clarify: is it a financial transaction (debit/credit)? A payment instruction? A trade? A journal entry? Each has different granularity, volume, and retention requirements.
- **Counterparty** is a critical entity in corporate banking and trade finance. Often missed until late in the process.
- Be alert to **regulatory-defined entities** — SAMA and Basel III have specific definitions for concepts like "Exposure", "Obligor", "Facility", and "Collateral" that may differ from the business's informal usage.

### Common Mistakes

- Treating "customer" as a single entity without asking whether it includes individuals, corporations, and counterparties — which may need separate treatment.
- Missing **derived facts** — quantities that must be calculated rather than stored. These need transformation logic defined now, not in the ETL phase.
- Ignoring **slowly changing attributes** — a customer's credit rating, address, or risk classification changes over time. Flag these early because they drive modeling choices in Phase 4.

### Phase 2 Exit Checklist

- [ ] All entities, events, and facts are extracted and documented
- [ ] Each element is traced to a source system
- [ ] System of record is identified for each entity
- [ ] Data gaps are documented
- [ ] Slowly changing attributes are flagged
- [ ] Derived/calculated facts are identified and separated from stored facts

---

## Phase 3 — Conceptual Data Model

### What You Do

The conceptual model is the **highest-level representation** of your data domain. It is deliberately technology-free, implementation-free, and jargon-free. Its purpose is to communicate structure to business stakeholders and validate your understanding before investing in detailed design.

Think of it as the architectural blueprint before any construction drawings exist.

### What Goes Into a Conceptual Model

- **Entities** — represented as named boxes
- **Relationships** — lines connecting entities, with cardinality (one-to-one, one-to-many, many-to-many)
- **Relationship labels** — plain-English verbs describing the relationship
- **Key attributes** — only the most important identifying attributes; not a full attribute list

**What does NOT go into a conceptual model:**
- Data types
- Primary keys / foreign keys
- Index strategies
- Table names
- Any technology-specific syntax

### Example: Banking Core Domain — Conceptual Relationships

```
CUSTOMER ──< holds >── ACCOUNT ──< has >── TRANSACTION
    |                      |
 < is classified as >   < belongs to >
    |                      |
CUSTOMER SEGMENT       PRODUCT TYPE
    
TRANSACTION ──< triggers >── INTEREST ACCRUAL
ACCOUNT ──< generates >── REGULATORY EXPOSURE
REGULATORY EXPOSURE ──< reported in >── REGULATORY REPORT
```

### Cardinality Notation

Use simple crow's foot or text notation:

| Notation | Meaning |
|----------|---------|
| `||--||` | One and only one |
| `||--o{` | One to zero or many |
| `||--|{` | One to one or many |
| `}o--o{` | Zero or many to zero or many |

### Build the Business Glossary

Alongside the conceptual model, produce a **Business Glossary**. This is the single most overlooked deliverable in data architecture, and the one that causes the most downstream pain.

| Term | Business Definition | Technical Notes | Owner |
|------|---------------------|-----------------|-------|
| Customer | Any individual or legal entity that holds or has applied for a banking product | Includes prospects; excludes internal entities | Business Banking |
| Transaction | A financial event that changes the balance of an account | Includes debits, credits, reversals; excludes pending authorisations | Operations |
| Net Exposure | The total outstanding credit risk to a counterparty after collateral and netting | Defined per Basel III Article 6 | Risk |
| Active Account | An account with at least one transaction in the past 90 days | SAMA regulatory definition applies | Compliance |

### Subject Area Decomposition

For large banking data warehouses, group your conceptual entities into **Subject Areas** — logical groupings that will later inform your physical layer organisation:

- **Customer & Party** — Customer, Counterparty, Corporate Client, Relationship Manager
- **Product & Account** — Product, Account, Facility, Collateral
- **Transaction & Event** — Transaction, Payment, Trade, Journal Entry
- **Risk & Exposure** — Credit Exposure, Market Risk, Liquidity Position
- **Regulatory & Compliance** — Regulatory Report, AML Case, Sanctions Flag
- **Reference Data** — Currency, Country, Industry Code, GL Account Code

### Inputs Required

- EEF Register from Phase 2
- Source System Map from Phase 2
- Access to any existing business glossaries or data dictionaries

### Outputs / Deliverables

- **Conceptual ERD** — entity-relationship diagram at business level
- **Business Glossary** — agreed definitions of all key terms
- **Subject Area Map** — grouping of entities into logical domains
- **Relationship Narrative** — plain-English description of each key relationship

### Banking-Specific Considerations

- Maintain strict alignment with **SAMA's defined data domains** from the Data Management Framework. SAMA defines standard subject areas for Saudi banks — your conceptual model should map to these.
- **Party vs Customer** — in banking architecture, the concept of "Party" (a person or organisation that plays a role) is often more correct than "Customer" alone. A party can be a customer, a guarantor, a counterparty, a regulator, all at once.
- **Account vs Facility vs Product** — these three concepts are distinct in banking and are frequently confused. A Product is the template. A Facility is the approved credit limit. An Account is the operational record of balances and transactions.

### Common Mistakes

- Adding data types or column names to the conceptual model. This confuses business stakeholders and locks you into implementation decisions too early.
- Skipping the Business Glossary. Without it, the word "customer" means different things to different people, and you will pay for this ambiguity in every downstream phase.
- Drawing the conceptual model in a technical tool that generates intimidating output. Use a whiteboard, Lucidchart, or draw.io. Keep it visual and approachable.
- Not getting business sign-off. This diagram is your contract with the business. Get it confirmed in writing.

### Phase 3 Exit Checklist

- [ ] Conceptual ERD is complete and reviewed with business stakeholders
- [ ] All key relationships have cardinality and relationship labels
- [ ] Business Glossary is populated with all key terms
- [ ] Subject areas are defined and agreed
- [ ] Conceptual model is signed off by business and compliance representatives

---

## Phase 4 — Choose the Modeling Approach

### What You Do

This is the decision that defines the architecture of your entire warehouse. Choose the wrong approach and you will spend years fighting your own data model. Choose the right one and the model will absorb change gracefully.

There is no universally correct answer. The right approach depends on **use case, volatility, team maturity, and regulatory requirements**.

### The Three Primary Approaches

---

#### 4.1 Third Normal Form (3NF) — Inmon Style

**What it is:** A fully normalised relational model where data is stored without redundancy. Every non-key attribute depends on the primary key and nothing else.

**Best for:**
- Operational data stores (ODS) that feed downstream marts
- Systems requiring high write throughput
- When the canonical "single version of truth" is the primary goal
- Enterprise Data Warehouses (EDW) following Inmon's top-down methodology

**Not suitable for:**
- Direct analytical queries by business users (too many joins)
- Environments where query performance is critical without a dedicated BI layer

**Banking fit:**
- Excellent for the **Integration Layer** of a banking EDW — the single authoritative store of all banking data before it is transformed into dimensional models
- Well-suited for regulatory reporting stores where data integrity is more important than query speed

**Example structure for banking:**
```
PARTY (party_id PK, party_type, legal_name, tax_id, ...)
ACCOUNT (account_id PK, party_id FK, product_id FK, open_date, status, ...)
TRANSACTION (txn_id PK, account_id FK, txn_date, amount, currency_code, txn_type, ...)
PRODUCT (product_id PK, product_name, product_category, ...)
CURRENCY (currency_code PK, currency_name, iso_code, ...)
```

---

#### 4.2 Dimensional Modeling — Kimball Style (Star Schema)

**What it is:** Data is organised into **Fact tables** (measurements and events) and **Dimension tables** (the context — who, what, when, where). The result looks like a star when diagrammed.

**Best for:**
- Analytical queries and BI dashboards
- Self-service analytics for business users
- When query performance is a primary concern
- Data marts serving specific business domains

**Not suitable for:**
- Systems with highly volatile schemas (dimensions change frequently)
- Environments requiring full historical audit trail at the source level
- When source-system traceability is a hard regulatory requirement

**Banking fit:**
- Excellent for **departmental data marts** — the Retail Banking Mart, the Treasury Mart, the Risk Mart
- Well-suited for management reporting and executive dashboards
- Query-friendly for analysts writing SQL against Snowflake, BigQuery, or Redshift

**Example structure for banking:**
```
FACT_TRANSACTION
  - txn_sk (surrogate key)
  - date_sk (FK to DIM_DATE)
  - account_sk (FK to DIM_ACCOUNT)
  - customer_sk (FK to DIM_CUSTOMER)
  - product_sk (FK to DIM_PRODUCT)
  - branch_sk (FK to DIM_BRANCH)
  - txn_amount_sar
  - txn_count
  - fee_amount_sar

DIM_DATE (date_sk, full_date, day_of_week, month, quarter, year, is_holiday, hijri_date, ...)
DIM_CUSTOMER (customer_sk, customer_id, customer_name, segment, risk_rating, nationality, ...)
DIM_ACCOUNT (account_sk, account_id, account_type, opening_date, status, ...)
DIM_PRODUCT (product_sk, product_id, product_name, product_category, ...)
DIM_BRANCH (branch_sk, branch_id, branch_name, region, city, ...)
```

**Note on Slowly Changing Dimensions (SCDs) in banking:**
- A customer's credit rating changes → SCD Type 2 (preserve history)
- A branch name changes → SCD Type 1 (overwrite, history not needed)
- A product is repriced → SCD Type 2 (preserve historical product attributes at time of sale)

---

#### 4.3 Data Vault 2.0

**What it is:** A modeling methodology designed specifically for enterprise data warehouses that need to handle **high auditability, multiple source systems, and frequent schema change**. Built on three core components:
- **Hubs** — the unique business keys (e.g., Customer ID, Account Number)
- **Links** — the relationships between hubs
- **Satellites** — the descriptive attributes, with full history and source tracking

**Best for:**
- Enterprise-scale banking data warehouses
- Environments with many source systems feeding the same entities
- When regulatory auditability and full historical lineage are mandatory
- When the source schema changes frequently (which it always does in banking)
- When SAMA or external auditors need to trace any data point back to its origin

**Not suitable for:**
- Small-scale implementations (significant structural overhead)
- Teams without Data Vault training
- When time-to-delivery is extremely short and the schema is stable

**Banking fit:**
- The gold standard for **Saudi and regional banking EDWs** where SAMA data lineage requirements and PDPL compliance make auditability non-negotiable
- Excellent for integrating data from core banking, CRM, GL, and risk systems simultaneously
- Naturally accommodates the frequent regulatory changes that banking data environments face

**Example structure for banking:**
```
-- Hubs (business keys only)
HUB_CUSTOMER (customer_hk PK, customer_bk, load_dts, record_source)
HUB_ACCOUNT  (account_hk PK, account_bk, load_dts, record_source)

-- Links (relationships)
LINK_CUSTOMER_ACCOUNT (link_hk PK, customer_hk FK, account_hk FK, load_dts, record_source)

-- Satellites (descriptive attributes with history)
SAT_CUSTOMER_DEMOGRAPHICS (customer_hk FK, load_dts, load_end_dts, hash_diff,
                            full_name, nationality, id_type, id_number, risk_rating,
                            record_source)
SAT_ACCOUNT_DETAILS (account_hk FK, load_dts, load_end_dts, hash_diff,
                     account_type, status, open_date, credit_limit,
                     record_source)
```

---

### Decision Matrix

| Criterion | 3NF (Inmon) | Star Schema (Kimball) | Data Vault 2.0 |
|-----------|------------|----------------------|----------------|
| Query performance | Low (many joins) | High (simple joins) | Medium (needs Information Marts) |
| Historical auditability | Medium | Low | Very High |
| Schema flexibility | Low | Low | Very High |
| Source traceability | Medium | Low | Very High |
| Business user friendliness | Low | Very High | Low |
| Regulatory compliance fit | Medium | Low | Very High |
| Implementation complexity | Medium | Low | High |
| Team skill requirement | Standard SQL | Standard SQL | Data Vault training needed |
| Best layer | Integration / ODS | Data Mart / Presentation | Core Warehouse / Raw Vault |

### The Architecture Recommendation for Banking

In practice, mature banking data warehouses use **all three in combination**:

```
[Source Systems]
      ↓
[Staging Layer]        ← Raw copies of source data, no transformation
      ↓
[Raw Vault]            ← Data Vault 2.0 (auditability, lineage, source traceability)
      ↓
[Business Vault]       ← Data Vault 2.0 + business rules applied
      ↓
[Information Mart]     ← Star Schema (dimensional, query-optimised)
      ↓
[Consumption Layer]    ← BI tools, APIs, regulatory reports, ML feature stores
```

### Inputs Required

- Confirmed conceptual model from Phase 3
- Use Case Register from Phase 1 (drives which layer serves which use case)
- Source system inventory and change frequency data
- Team skill assessment
- Infrastructure platform decision (or constraints)

### Outputs / Deliverables

- **Modeling Approach Decision Document** — selected approach per layer, with documented rationale
- **Architecture Layer Diagram** — showing which layers use which approach
- **SCD Strategy** — dimension-by-dimension decision on Type 1/2/3/4/6

### Phase 4 Exit Checklist

- [ ] Modeling approach is selected for each architectural layer
- [ ] Decision is documented with rationale
- [ ] SCD strategy is defined for all key dimensions
- [ ] Architecture layer diagram is produced
- [ ] Decision is reviewed with data engineering and BI teams

---

## Phase 5 — Logical Data Model

### What You Do

The logical model is the **detailed, technology-agnostic specification** of your data structures. It takes the conceptual model and adds precision — full attribute lists, data types at a logical level, primary and foreign keys, business rules, and constraints — without yet binding to any specific database technology.

Think of the logical model as the engineering drawings that a contractor could use, independent of which materials will be used.

### What Goes Into a Logical Data Model

- All entities with full attribute lists
- Logical data types (String, Integer, Decimal, Date, Boolean — not VARCHAR(255) or NUMBER(18,2))
- Primary keys (natural or surrogate)
- Foreign key relationships
- Unique constraints
- Null / Not-null constraints
- Business rules expressed as constraints or notes
- Relationship cardinality (fully specified)

### Logical Model for a Banking Transaction Entity (Example)

```
ENTITY: FINANCIAL_TRANSACTION

Attribute                   | Logical Type  | Constraint         | Notes
----------------------------|--------------|--------------------|---------------------------------
transaction_id              | String        | PK, NOT NULL       | System-generated unique identifier
account_id                  | String        | FK → ACCOUNT, NN   | The account being debited/credited
counterparty_account_id     | String        | FK → ACCOUNT, NULL | NULL for external counterparties
transaction_date            | Date          | NOT NULL           | Date of transaction (business date)
value_date                  | Date          | NOT NULL           | Settlement date
booking_date                | Date          | NOT NULL           | Date posted to GL
transaction_type            | String        | NOT NULL           | e.g. DEBIT, CREDIT, REVERSAL
amount                      | Decimal(18,2) | NOT NULL, > 0      | Always positive; direction via type
currency_code               | String(3)     | FK → CURRENCY, NN  | ISO 4217 code
amount_sar                  | Decimal(18,2) | NOT NULL           | Converted to SAR for reporting
fx_rate                     | Decimal(12,6) | NULL               | NULL when currency_code = SAR
channel                     | String        | NOT NULL           | ATM, MOBILE, BRANCH, SWIFT, API
transaction_status          | String        | NOT NULL           | PENDING, COMPLETED, REVERSED, FAILED
reference_number            | String        | UNIQUE, NULL       | External reference from initiating system
narrative                   | String        | NULL               | Free-text description
aml_flag                    | Boolean       | NOT NULL, DEF: F   | Flagged by AML screening
created_by_system           | String        | NOT NULL           | Source system identifier
created_timestamp           | Timestamp     | NOT NULL           | UTC timestamp of record creation
last_modified_timestamp     | Timestamp     | NOT NULL           | UTC timestamp of last update
```

### Defining Business Rules in the Logical Model

Business rules should be captured explicitly:

| Rule ID | Entity | Rule Description | Implementation Hint |
|---------|--------|-----------------|---------------------|
| BR-001 | TRANSACTION | amount must always be positive; direction is determined by transaction_type | CHECK constraint |
| BR-002 | TRANSACTION | value_date cannot be earlier than transaction_date | CHECK constraint |
| BR-003 | ACCOUNT | An account cannot be closed if it has a non-zero balance | Application + trigger |
| BR-004 | CUSTOMER | A corporate customer must have a valid CR (Commercial Registration) number | NOT NULL for corporate subtype |
| BR-005 | EXPOSURE | Net exposure must be recalculated whenever a transaction, payment, or rate change occurs | Trigger / event-driven |

### Key / Surrogate Key Strategy

Define your key strategy at the logical level:

- **Natural Key** — the business identifier as it exists in the source system (Customer ID, IBAN, Account Number). Use for integration and traceability.
- **Surrogate Key** — a system-generated integer or UUID. Use for dimensional modeling and when natural keys are unstable, composite, or reused.
- **Hash Key (Data Vault)** — a MD5 or SHA-256 hash of the business key. Use in Data Vault for deterministic, load-order-independent key generation.

**Recommendation for banking:** Use surrogate keys in the warehouse, but always retain and index the natural key for traceability and regulatory lookup.

### Address Many-to-Many Relationships

Many real-world banking relationships are many-to-many and must be resolved through an **associative entity (bridge table)**:

```
CUSTOMER ─── ACCOUNT: One customer can hold many accounts; one account can have multiple signatories (joint accounts)

Resolved via:
ACCOUNT_HOLDER (account_id FK, customer_id FK, holder_role, primary_flag, valid_from, valid_to)
```

### Inputs Required

- Conceptual ERD from Phase 3
- Modeling approach decision from Phase 4
- Business rules from SMEs and compliance team
- Source system data dictionaries (for attribute derivation)

### Outputs / Deliverables

- **Full Logical ERD** — all entities, attributes, keys, and relationships
- **Business Rule Register** — formalised list of all business rules and where they are enforced
- **Key Strategy Document** — natural key vs surrogate key decisions per entity
- **Attribute Dictionary** — definition of every attribute including business meaning, allowed values, and source

### Banking-Specific Considerations

- **Hijri and Gregorian dates** — Saudi banking systems must support both calendar systems. Always store dates in Gregorian (ISO 8601) as the canonical form and compute Hijri equivalents as derived attributes or in the presentation layer.
- **Multi-currency** — all monetary amounts should be stored in their original currency AND converted to SAR (Saudi Riyal). Never store only the converted amount — you lose the source currency and rate information.
- **IBAN** — use structured storage of IBAN components (country code, check digits, BBAN) alongside the full IBAN string, to support regulatory lookups.
- **Transaction reversals** — model reversals explicitly. A reversal is not a deletion; it is a new transaction with a reference to the original transaction_id.

### Phase 5 Exit Checklist

- [ ] All entities have complete attribute lists with logical data types
- [ ] All primary keys, foreign keys, and unique constraints are defined
- [ ] Many-to-many relationships are resolved through associative entities
- [ ] Business rules are documented and linked to enforcement mechanisms
- [ ] Attribute dictionary is complete
- [ ] Key strategy is documented
- [ ] Logical ERD reviewed and approved by data architects and lead developers

---

## Phase 6 — Physical Data Model

### What You Do

The physical model translates the logical model into **specific, platform-targeted database structures**. Every decision here has performance, cost, and operational implications. This is where your knowledge of the target platform (Snowflake, Oracle, PostgreSQL, Azure Synapse, etc.) becomes critical.

### Physical Data Type Mapping

Translate logical types to platform-specific physical types:

| Logical Type | Oracle | PostgreSQL | Snowflake | SQL Server |
|-------------|--------|------------|-----------|------------|
| String (short) | VARCHAR2(255) | VARCHAR(255) | VARCHAR(255) | NVARCHAR(255) |
| String (long) | CLOB | TEXT | VARCHAR(16777216) | NVARCHAR(MAX) |
| Integer | NUMBER(10) | INTEGER | NUMBER(10,0) | INT |
| Decimal(18,2) | NUMBER(18,2) | NUMERIC(18,2) | NUMBER(18,2) | DECIMAL(18,2) |
| Date | DATE | DATE | DATE | DATE |
| Timestamp | TIMESTAMP WITH TIME ZONE | TIMESTAMPTZ | TIMESTAMP_TZ | DATETIMEOFFSET |
| Boolean | NUMBER(1) | BOOLEAN | BOOLEAN | BIT |
| UUID | RAW(16) | UUID | VARCHAR(36) | UNIQUEIDENTIFIER |

**Always use TIMESTAMP WITH TIME ZONE for banking.** Naive timestamps in banking create reconciliation nightmares when systems span time zones. Store in UTC, display in local time.

### Partitioning Strategy

Partitioning is one of the most important physical design decisions. It determines query performance, data management efficiency, and archival capability.

#### Partition by Date (Most Common in Banking)

```sql
-- Example: Oracle Range Partitioning on transaction_date
CREATE TABLE FACT_TRANSACTION (
    txn_id          VARCHAR2(36)     NOT NULL,
    transaction_date DATE            NOT NULL,
    account_id      VARCHAR2(36)     NOT NULL,
    amount_sar      NUMBER(18,2)     NOT NULL,
    ...
)
PARTITION BY RANGE (transaction_date) INTERVAL (NUMTOYMINTERVAL(1,'MONTH'))
(
    PARTITION p_before_2020 VALUES LESS THAN (DATE '2020-01-01')
);
```

#### When to Use Which Partition Key

| Use Case | Recommended Partition Key |
|----------|--------------------------|
| Transaction history queries | transaction_date (monthly) |
| Regulatory reports (SAMA) | reporting_date (monthly/quarterly) |
| AML case data | case_creation_date (monthly) |
| Customer snapshots | snapshot_date (daily/monthly) |
| Large reference tables | No partitioning needed |

### Indexing Strategy

Indexes speed up reads but slow down writes. In a data warehouse, be selective.

| Index Type | When to Use | Banking Example |
|-----------|-------------|-----------------|
| Primary Key Index | Always, on surrogate key | txn_sk on FACT_TRANSACTION |
| Natural Key Index | Always, for traceability lookups | transaction_id, account_number |
| Foreign Key Index | On all FK columns | account_sk, customer_sk in fact tables |
| Composite Index | On frequently-combined filter columns | (account_id, transaction_date) |
| Bitmap Index (DW only) | Low-cardinality columns | transaction_type, channel, status |
| Avoid | On high-volatility columns | Columns updated frequently |

### Clustering Keys (Snowflake / Redshift)

```sql
-- Snowflake: Define clustering key for large fact tables
ALTER TABLE FACT_TRANSACTION
CLUSTER BY (transaction_date, account_sk);
```

For Snowflake, clustering is more impactful than indexing for very large fact tables. Choose columns that appear in WHERE clauses and JOIN conditions most frequently.

### DDL Standards and Naming Conventions

Establish and enforce naming conventions before writing a single DDL statement:

| Object | Convention | Example |
|--------|-----------|---------|
| Fact table | FACT_{domain}_{subject} | FACT_RETAIL_TRANSACTION |
| Dimension table | DIM_{subject} | DIM_CUSTOMER |
| Bridge table | BRIDGE_{subject1}_{subject2} | BRIDGE_CUSTOMER_ACCOUNT |
| Hub (DV) | HUB_{subject} | HUB_CUSTOMER |
| Satellite (DV) | SAT_{subject}_{descriptor} | SAT_CUSTOMER_KYC |
| Link (DV) | LNK_{subject1}_{subject2} | LNK_CUSTOMER_ACCOUNT |
| Staging table | STG_{source}_{subject} | STG_CBS_CUSTOMER |
| Column (PK) | {entity}_sk | customer_sk |
| Column (FK) | {entity}_sk | account_sk |
| Column (date) | {context}_date | transaction_date |
| Column (timestamp) | {context}_timestamp | created_timestamp |
| Index | IDX_{table}_{columns} | IDX_FACT_TXN_DATE_ACCT |

### Compression and Storage

| Data Category | Compression Approach |
|--------------|---------------------|
| Historical fact tables (> 1 year) | Maximum compression (ZSTD or GZIP) |
| Current-period fact tables | Low compression (faster write) |
| Dimension tables | Row-level compression |
| Staging tables | No compression (fast load, fast drop) |

### Data Retention and Archival

Define retention at the physical level:

| Data Category | Retention Period | Basis |
|--------------|-----------------|-------|
| Customer transaction records | 10 years | SAMA regulation |
| AML case records | 10 years (minimum) | FATF / SAMA AML guidelines |
| Customer identification data | Duration of relationship + 5 years | PDPL / AML |
| Regulatory reports | 7 years | SAMA |
| Audit logs | 7 years | SAMA |
| Marketing analytics | 2 years | PDPL (proportionality principle) |

### Inputs Required

- Logical Data Model from Phase 5
- Target platform selection
- Infrastructure sizing and cost constraints
- Data volume estimates from Phase 1

### Outputs / Deliverables

- **Physical ERD** — platform-specific model with data types, constraints, and indexes
- **DDL Scripts** — complete, runnable CREATE TABLE statements for all objects
- **Naming Convention Document** — enforced standard for all database objects
- **Partitioning & Indexing Strategy** — documented decision per table
- **Retention Policy** — table-by-table retention rules with regulatory basis

### Phase 6 Exit Checklist

- [ ] All tables have DDL scripts with correct platform data types
- [ ] Naming conventions are applied consistently
- [ ] Partitioning strategy is defined for all large tables
- [ ] Indexing strategy is defined
- [ ] Clustering or distribution keys are set (for columnar/MPP databases)
- [ ] Compression settings are defined
- [ ] Retention periods are documented with regulatory basis
- [ ] DDL scripts reviewed and approved by DBA team

---

## Phase 7 — Governance, Lineage & Compliance

### What You Do

Phase 7 is the **regulatory and governance wrapper** that transforms a technically correct data model into a **compliant, auditable, and trustworthy** data asset. In banking, this phase is not optional — it is a regulatory requirement under SAMA, PDPL, and international standards.

This phase runs **in parallel with Phases 5 and 6**, not strictly after them. Governance decisions influence physical design, and physical constraints influence governance feasibility.

---

### 7.1 Data Classification

Every data element must be classified. Classification drives access control, masking, encryption, and retention.

#### Classification Tiers

| Classification Level | Description | Banking Examples |
|---------------------|-------------|-----------------|
| **Strictly Confidential** | Highest sensitivity; regulatory or fiduciary obligation to protect | Customer NIC/Iqama number, account balances, transaction history, credit scores |
| **Confidential** | Sensitive business data; restricted to authorised roles | Customer name, address, contact details, product holdings |
| **Internal** | Not for public consumption but lower risk if disclosed | Branch performance metrics, product pricing, staff data |
| **Public** | Can be disclosed without harm | Exchange rates, product brochures, branch locations |

#### PII Categories Under PDPL (Saudi Arabia)

| PII Type | Examples | PDPL Requirement |
|----------|---------|-----------------|
| Direct Identifiers | Full name, NIC, passport number | Explicit consent or legal basis required |
| Financial PII | Account numbers, balances, transactions | Strict purpose limitation; cannot be used for marketing without consent |
| Sensitive PII | Health data, biometrics, political views | Heightened protection; explicit consent mandatory |
| Behavioural PII | Transaction patterns, location data | Purpose limitation; anonymisation preferred |

#### Implementation: Column-Level Classification

Apply classification in your data dictionary and enforce it in the database:

```sql
-- Example: Tag columns in Snowflake using column-level security
CREATE TAG governance.data_classification ALLOWED_VALUES 'STRICTLY_CONFIDENTIAL', 'CONFIDENTIAL', 'INTERNAL', 'PUBLIC';

ALTER TABLE DIM_CUSTOMER MODIFY COLUMN national_id SET TAG governance.data_classification = 'STRICTLY_CONFIDENTIAL';
ALTER TABLE DIM_CUSTOMER MODIFY COLUMN full_name SET TAG governance.data_classification = 'CONFIDENTIAL';
ALTER TABLE DIM_CUSTOMER MODIFY COLUMN customer_segment SET TAG governance.data_classification = 'INTERNAL';
```

---

### 7.2 Data Masking and Anonymisation

Classified data must be masked in non-production environments and for unauthorised roles in production.

#### Masking Techniques

| Technique | When to Use | Example |
|-----------|------------|---------|
| **Static Masking** | Non-production copies, development, testing | Replace NIC with randomly generated valid NIC |
| **Dynamic Masking** | Production; unauthorised roles see masked data | Analyst sees `XXXX-XXXX-1234` instead of full IBAN |
| **Tokenisation** | When the value must be consistent across systems | Replace account number with a token that maps back via a secure vault |
| **Pseudonymisation** | Analytics and ML use cases | Replace customer_id with a pseudonymous ID; mapping stored securely |
| **Anonymisation** | Public analytics or research | Aggregate or generalise — no re-identification possible |

**PDPL distinction:** Pseudonymised data is still personal data. Anonymised data is not. Design for true anonymisation where the use case allows it.

#### Example: Dynamic Masking in Snowflake

```sql
CREATE MASKING POLICY governance.mask_iban AS (val STRING) RETURNS STRING ->
  CASE
    WHEN CURRENT_ROLE() IN ('DBA_ROLE', 'COMPLIANCE_ROLE') THEN val
    ELSE CONCAT('SA**-****-****-****-', RIGHT(val, 4))
  END;

ALTER TABLE FACT_TRANSACTION MODIFY COLUMN iban SET MASKING POLICY governance.mask_iban;
```

---

### 7.3 Data Lineage

Data lineage answers the question: **"Where did this number come from?"** In banking, regulators ask this question frequently, and the inability to answer it is a finding — sometimes a significant one.

#### Lineage Must Cover

- **Source-to-target mapping** — which source system field maps to which warehouse column
- **Transformation logic** — any computation, aggregation, or enrichment applied
- **Load frequency and timing** — when data was loaded and from which snapshot
- **Business rule application** — which business rules were applied and when

#### Source-to-Target Mapping Document (STM)

| Target Table | Target Column | Source System | Source Table | Source Column | Transformation Logic | Load Type |
|-------------|--------------|--------------|-------------|--------------|---------------------|-----------|
| FACT_TRANSACTION | amount_sar | CBS | TXN_LEDGER | TXN_AMOUNT | `TXN_AMOUNT * FX_RATE_TO_SAR` | Incremental |
| FACT_TRANSACTION | transaction_type | CBS | TXN_LEDGER | DR_CR_IND | `CASE WHEN DR_CR_IND='D' THEN 'DEBIT' ELSE 'CREDIT' END` | Incremental |
| DIM_CUSTOMER | risk_rating | CRM | CUST_PROFILE | RISK_SCORE_BAND | Direct copy | Full refresh |
| DIM_CUSTOMER | nationality | CBS, CRM | CUST_MASTER | NATIONALITY_CODE | CBS is system of record; CRM supplements where CBS is null | Incremental |

#### Lineage Tooling

For enterprise banking warehouses, manual STM documents are insufficient at scale. Use lineage tooling:

- **Apache Atlas** — open-source, integrates with Hadoop ecosystem
- **Collibra** — enterprise data governance with built-in lineage
- **Alation** — data catalogue with automated lineage capture
- **DataHub (LinkedIn)** — open-source, excellent for modern data stacks
- **Snowflake Access History** — built-in lineage for Snowflake environments

---

### 7.4 Data Ownership

Every data domain must have an accountable owner. Ownership is a governance construct, not a technical one.

| Data Domain | Data Owner (Business) | Data Steward (Operational) | Technical Owner |
|------------|----------------------|--------------------------|-----------------|
| Customer & Party | Head of Retail Banking | Customer Data Manager | Core Banking DBA |
| Transaction History | COO / Operations Director | Operations Data Steward | DW Architect |
| Credit Exposure | Chief Risk Officer | Risk Data Steward | Risk Technology Lead |
| AML & Compliance | Chief Compliance Officer | Compliance Data Analyst | Compliance Technology |
| Product Reference | Head of Product | Product Data Manager | Reference Data Team |

**SAMA requirement:** SAMA's Data Management Framework requires each bank to designate a Chief Data Officer (CDO) and domain-level Data Owners. Your governance model must align with this structure.

---

### 7.5 Access Control and Role-Based Security

#### Role Design Principles

Design roles based on **data sensitivity and job function**, not on individuals:

```sql
-- Role hierarchy example
CREATE ROLE DW_READ_INTERNAL;       -- Can see Internal and Public data
CREATE ROLE DW_READ_CONFIDENTIAL;   -- Can see Confidential + below (inherits DW_READ_INTERNAL)
CREATE ROLE DW_READ_RESTRICTED;     -- Can see Strictly Confidential data (specific approvals required)
CREATE ROLE DW_ANALYST;             -- Business analysts: masked Confidential access
CREATE ROLE DW_COMPLIANCE;          -- Compliance team: unmasked Confidential + Restricted
CREATE ROLE DW_REGULATOR;           -- SAMA examination access: read-only, specific tables only

-- Grant hierarchy
GRANT DW_READ_INTERNAL TO DW_READ_CONFIDENTIAL;
GRANT DW_READ_CONFIDENTIAL TO DW_READ_RESTRICTED;
```

#### Row-Level Security

For multi-branch or multi-region warehouses, implement row-level security to restrict which rows each role can see:

```sql
-- Snowflake Row Access Policy: Branch managers see only their branch's data
CREATE ROW ACCESS POLICY governance.branch_access AS (branch_id VARCHAR) RETURNS BOOLEAN ->
  CURRENT_ROLE() IN ('DW_READ_RESTRICTED', 'DW_COMPLIANCE')
  OR EXISTS (
    SELECT 1 FROM USER_BRANCH_ACCESS
    WHERE user_name = CURRENT_USER()
    AND authorised_branch_id = branch_id
  );

ALTER TABLE FACT_TRANSACTION ADD ROW ACCESS POLICY governance.branch_access ON (branch_id);
```

---

### 7.6 Audit Logging

Every access to, and modification of, sensitive data must be logged. This is both a SAMA requirement and a sound security practice.

#### What Must Be Logged

| Event Type | Logged Fields | Retention |
|-----------|--------------|-----------|
| Data read (Strictly Confidential) | user, role, table, columns accessed, timestamp, row count | 7 years |
| Data modification (any) | user, role, table, old value, new value, timestamp | 7 years |
| Schema change | user, DDL statement, timestamp | 7 years |
| Permission grant/revoke | grantor, grantee, object, privilege, timestamp | 7 years |
| Failed login / access denied | user, attempted resource, timestamp | 3 years |
| Data export | user, table, row count, export format, timestamp | 7 years |

#### Audit Implementation Pattern

```sql
-- Audit log table structure
CREATE TABLE AUDIT.DATA_ACCESS_LOG (
    log_id              VARCHAR(36)     DEFAULT UUID_STRING() NOT NULL,
    event_timestamp     TIMESTAMP_TZ    DEFAULT CURRENT_TIMESTAMP() NOT NULL,
    event_type          VARCHAR(50)     NOT NULL,   -- READ, INSERT, UPDATE, DELETE, EXPORT
    user_name           VARCHAR(255)    NOT NULL,
    user_role           VARCHAR(255)    NOT NULL,
    database_name       VARCHAR(255)    NOT NULL,
    schema_name         VARCHAR(255)    NOT NULL,
    table_name          VARCHAR(255)    NOT NULL,
    column_names        VARIANT,                    -- Array of accessed columns
    row_count           NUMBER,
    session_id          VARCHAR(255),
    client_ip           VARCHAR(50),
    query_id            VARCHAR(255)                -- Platform query ID for forensic lookup
);
```

---

### 7.7 Data Quality Framework

Data governance without data quality is a governance framework built on sand. Define, measure, and enforce quality rules.

#### Data Quality Dimensions

| Dimension | Definition | Banking Example | Measurement |
|-----------|-----------|-----------------|-------------|
| **Completeness** | Are all required fields populated? | NIC is never null for retail customers | % of non-null values |
| **Accuracy** | Does the value correctly represent the real world? | Transaction amount matches source system | % matching source reconciliation |
| **Consistency** | Is the same fact represented the same way across systems? | Customer name matches between CBS and CRM | % of records with matching values across sources |
| **Timeliness** | Is data available when it is needed? | Yesterday's transactions loaded by 06:00 | Load latency vs SLA |
| **Validity** | Does the value conform to the defined domain? | Currency code is a valid ISO 4217 code | % of values in valid domain |
| **Uniqueness** | Is each record represented exactly once? | No duplicate transaction_id values | Duplicate count |

#### Implementing Quality Rules

```sql
-- Quality check: Completeness
SELECT
    COUNT(*) AS total_records,
    COUNT(national_id) AS national_id_populated,
    ROUND(COUNT(national_id) * 100.0 / COUNT(*), 2) AS completeness_pct
FROM DIM_CUSTOMER
WHERE customer_type = 'INDIVIDUAL';

-- Quality check: Referential integrity
SELECT COUNT(*) AS orphaned_transactions
FROM FACT_TRANSACTION ft
LEFT JOIN DIM_ACCOUNT da ON ft.account_sk = da.account_sk
WHERE da.account_sk IS NULL;

-- Quality check: Validity
SELECT COUNT(*) AS invalid_currency_codes
FROM FACT_TRANSACTION ft
LEFT JOIN DIM_CURRENCY dc ON ft.currency_code = dc.currency_code
WHERE dc.currency_code IS NULL;
```

---

### 7.8 SAMA Regulatory Alignment

The Saudi Central Bank (SAMA) issues specific requirements that directly affect data architecture:

| SAMA Requirement | Architectural Implication |
|-----------------|--------------------------|
| **Data Management Framework** | Formal data ownership, lineage, and quality documentation required |
| **Cyber Security Framework** | Encryption at rest and in transit; access logging; privileged access management |
| **Open Banking Framework** | API-accessible data with consent management; customer data portability |
| **AML/CFT Guidelines** | Transaction monitoring data retained 10 years; SAR (Suspicious Activity Report) data secured |
| **Cloud Computing Framework** | Data residency — customer data must remain within KSA unless SAMA pre-approval granted |
| **IFRS 9 ECL** | 5-year minimum historical transaction data for probability of default models |
| **Basel III** | Capital reporting requires granular exposure data at counterparty level |

---

### 7.9 PDPL Compliance Implementation

Saudi Arabia's Personal Data Protection Law (PDPL) applies to all data about individuals — including banking customers.

#### PDPL Implementation Checklist for Data Architects

| PDPL Requirement | Implementation in Warehouse |
|-----------------|----------------------------|
| **Lawful basis** | Document legal basis for each personal data attribute in the data dictionary |
| **Purpose limitation** | Tag each attribute with its approved processing purpose; enforce via role-based access |
| **Data minimisation** | Do not bring personal data into the warehouse unless the use case requires it |
| **Accuracy** | Implement quality checks; allow customer-initiated correction via data correction workflow |
| **Storage limitation** | Implement and enforce table-level retention policies with automated archival/deletion |
| **Subject access rights** | Build customer data lookup capability — ability to retrieve all data held about one individual |
| **Right to erasure** | Implement pseudonymisation or deletion workflow for PDPL erasure requests (note: banking regulatory retention may override erasure for financial records) |
| **Cross-border transfer** | Restrict data export to non-KSA systems unless SAMA/SDAIA approved |
| **Breach notification** | Implement alerting for unauthorised access; breach response documented |

---

### Inputs Required

- Physical Data Model from Phase 6
- Regulatory obligations register from Phase 1
- Bank's existing data governance policy (if any)
- PDPL legal opinion from compliance/legal team
- SAMA examination findings (if previous examinations have occurred)

### Outputs / Deliverables

- **Data Classification Register** — every table and sensitive column classified
- **Source-to-Target Mapping (STM)** — complete lineage documentation
- **Data Ownership Matrix** — business and technical owners per domain
- **Access Control Matrix** — roles, permissions, and masking policies
- **Audit Logging Design** — what is logged, where, and for how long
- **Data Quality Rule Catalogue** — all quality checks with thresholds
- **PDPL Compliance Register** — how each PDPL obligation is met
- **SAMA Alignment Document** — how the architecture meets SAMA requirements

### Phase 7 Exit Checklist

- [ ] All sensitive columns are classified
- [ ] Masking policies are implemented and tested
- [ ] Full source-to-target lineage is documented for all critical data paths
- [ ] Data owners are assigned for all domains
- [ ] RBAC roles are designed and reviewed by security team
- [ ] Row-level security is implemented where required
- [ ] Audit logging is operational and tested
- [ ] Data quality rules are implemented with baseline measurements
- [ ] PDPL obligations are mapped to implementation controls
- [ ] SAMA alignment is reviewed by compliance officer
- [ ] Data retention policies are implemented with automation

---

## Phase 8 — Validate Against Requirements

### What You Do

Return to Phase 1. Every business requirement you captured must now be traceable to a table, column, transformation, or report in your implemented model. If a requirement cannot be traced, something is missing.

### The Traceability Matrix

| Requirement ID | Requirement Description | Table(s) | Column(s) | Transformation | Report/Output | Status |
|---------------|------------------------|----------|-----------|----------------|---------------|--------|
| REQ-001 | Monthly transaction volume by product | FACT_TRANSACTION, DIM_PRODUCT | txn_count, product_name | GROUP BY product, MONTH | Retail Analytics Dashboard | ✅ Complete |
| REQ-002 | Net exposure by counterparty (regulatory) | FACT_CREDIT_EXPOSURE, DIM_PARTY | net_exposure_sar, party_name | SUM after netting rules | SAMA Exposure Report | ✅ Complete |
| REQ-003 | AML transaction monitoring feed | FACT_TRANSACTION | aml_flag, amount_sar, channel | Filter: amount > threshold OR cross-border | AML System Feed | ⚠️ Partial — threshold config needed |
| REQ-004 | Customer 360 view | DIM_CUSTOMER, FACT_TRANSACTION, FACT_LOAN | all key attributes | Join across domains | CRM Integration API | ❌ Not started |

### User Acceptance Testing (UAT) for Data

Data UAT is different from application UAT. It must validate:

1. **Completeness** — all historical data loaded correctly
2. **Accuracy** — spot-check values against source system
3. **Business logic** — confirm calculated fields match manual calculations
4. **Performance** — queries complete within SLA under expected load
5. **Access control** — each role sees exactly what it should see, nothing more
6. **Regulatory output** — regulatory reports produce values that reconcile with the source system

### Reconciliation

For each key fact in the model, produce a reconciliation report comparing the warehouse to the source:

```
Reconciliation: FACT_TRANSACTION vs CBS Transaction Ledger
Period: January 2025

                          CBS Source    DW (Warehouse)    Variance    %
Total Transaction Count:  4,287,341     4,287,341         0           0.00%
Total Credit Amount SAR:  892,341,209   892,341,209       0           0.00%
Total Debit Amount SAR:   887,654,112   887,654,112       0           0.00%
Unique Accounts:          127,456       127,456           0           0.00%

Status: PASSED ✅
```

### Phase 8 Exit Checklist

- [ ] Traceability matrix is complete — all requirements mapped
- [ ] UAT test plan is executed with documented results
- [ ] Reconciliation reports pass for all key facts
- [ ] Performance benchmarks are met under realistic load
- [ ] Access control testing confirms correct role behaviour
- [ ] Regulatory report outputs reviewed and approved by compliance
- [ ] Business stakeholder sign-off obtained in writing
- [ ] Known issues documented with remediation plan and owner

---

## Appendix A — Architecture Decision Record (ADR) Template

Use this template whenever you make a significant architectural decision. Store all ADRs in version control alongside your model artefacts.

```
ADR-{number}: {Short Decision Title}
Date: {YYYY-MM-DD}
Status: [Proposed | Accepted | Deprecated | Superseded by ADR-{n}]
Author: {Name}

Context
-------
{What is the situation or problem that requires a decision?}

Decision
--------
{What was decided?}

Rationale
---------
{Why was this option chosen over alternatives?}

Alternatives Considered
------------------------
1. {Option A} — Rejected because: {reason}
2. {Option B} — Rejected because: {reason}

Consequences
------------
Positive: {What gets better?}
Negative: {What gets worse or more complex?}
Risks: {What could go wrong?}

Regulatory Impact
-----------------
{Does this decision affect SAMA, PDPL, or other compliance obligations?}
```

---

## Appendix B — Regulatory Quick Reference (Saudi Banking)

| Regulation | Issuing Body | Key Data Architecture Implications |
|-----------|-------------|-----------------------------------|
| Data Management Framework | SAMA | Data ownership, lineage, quality, stewardship mandatory |
| Cyber Security Framework | SAMA | Encryption, access logging, privileged access management |
| Cloud Computing Framework | SAMA | Data residency in KSA; pre-approval for offshore processing |
| Open Banking Framework | SAMA | API-first data exposure; consent management; data portability |
| AML/CFT Regulations | SAMA / FATF | 10-year transaction retention; SAR data security; transaction monitoring |
| PDPL | SDAIA | Consent, purpose limitation, subject rights, breach notification |
| IFRS 9 | IASB / SOCPA | Historical data for ECL models; staging classification data |
| Basel III | BCBS | Capital reporting; exposure data at counterparty granularity |
| Vision 2030 Data Strategy | NDA / Government | National data interoperability standards |

---

## Appendix C — Deliverables Checklist by Phase

| Phase | Deliverable | Owner | Approver |
|-------|------------|-------|---------|
| 1 | Business Requirement Summary | BA / Architect | Business Sponsor |
| 1 | Use Case Register | Architect | Business Sponsor + Compliance |
| 1 | Assumption Log | Architect | Business Sponsor |
| 2 | Entity-Event-Fact Register | Architect | Lead Architect |
| 2 | Source System Map | Architect + DBA | Lead Architect |
| 2 | Data Gap Register | Architect | Business Sponsor |
| 3 | Conceptual ERD | Architect | Business Sponsor |
| 3 | Business Glossary | Architect + BA | Business Sponsor + CDO |
| 3 | Subject Area Map | Architect | Lead Architect |
| 4 | Modeling Approach Decision Document | Lead Architect | CTO / CDO |
| 4 | SCD Strategy | Architect | Lead Architect |
| 5 | Logical ERD | Architect | Lead Architect |
| 5 | Business Rule Register | Architect + BA | Business Sponsor |
| 5 | Attribute Dictionary | Architect | Lead Architect |
| 6 | Physical ERD | Architect + DBA | DBA Lead |
| 6 | DDL Scripts | DBA | DBA Lead |
| 6 | Partitioning & Indexing Strategy | DBA | Lead Architect + DBA Lead |
| 7 | Data Classification Register | Architect + Compliance | CDO + CISO |
| 7 | Source-to-Target Mapping | ETL / Architect | Lead Architect |
| 7 | Access Control Matrix | DBA + Security | CISO |
| 7 | PDPL Compliance Register | Architect + Legal | CDO + Legal |
| 7 | Data Quality Rule Catalogue | Data Engineer | Lead Architect |
| 8 | Traceability Matrix | Architect | Business Sponsor |
| 8 | UAT Results | QA + Business | Business Sponsor |
| 8 | Reconciliation Reports | DW Team | Business Sponsor + Compliance |

---

*Framework Version 1.0 | Applicable to: Banking & Financial Services Data Warehousing | Regulations: SAMA, PDPL, IFRS 9, Basel III*

---

## Part B — Domain Walkthroughs: Al-Noor Bank Case Study

> These walkthroughs apply the 8-phase framework to a real banking scenario.
> Al-Noor Bank is a Saudi digital retail bank building a new platform from scratch.
> Five domains. Each follows the identical process. Read Payments first — it establishes the method.
> The other four domains follow the same steps with domain-specific decisions.

---

### How to Approach an Architecture Problem

**The mistake almost everyone makes** is to start drawing. Someone opens a diagramming tool, creates a box labelled CUSTOMER, adds ACCOUNT, draws a line — and within ten minutes has fifteen boxes, no clear boundaries, and no way to explain why anything is where it is. This is decoration, not architecture.

**Architecture starts with questions, not boxes.**

The right starting order — for every domain, every time:

```
Step 1 — What problem does this domain exist to solve?  (one sentence)
Step 2 — What business questions must it answer every day?
Step 3 — What real-world things does it need to remember?  (entities)
Step 4 — How do those things relate to each other?
Step 5 — Draw the conceptual model  (boxes and lines only — no columns)
Step 6 — Add attributes  (logical model — types, constraints, PDPL, source)
Step 7 — Write the physical DDL  (indexes, partitioning, constraints, triggers)
Step 8 — Validate with a real business scenario  (trace every table read or written)
```

**Before designing any entity, answer these four regulatory questions:**

1. Does this entity contain personal data? → Every column needs a PDPL classification
2. Does this entity need an audit trail? → If it changes state, a history table is required
3. Does this entity have a retention obligation? → Transaction data: 10 years minimum
4. Does this entity feed a SAMA report? → The report is a design requirement, not an afterthought

**How to read a requirement for schema decisions:**

> *"All payments via SARIE for domestic SAR, SWIFT for international."*
> → The payment table needs a `payment_rail` column
> → SARIE and SWIFT are not interchangeable — they need separate reference columns (`sarie_uetr`, `swift_uetr`)
> → A generic `reference_no` cannot serve both

> *"Account balance queries in under 100ms."*
> → Index on `account_id`
> → A `balance_after` snapshot column avoids recalculating from full transaction history
> → This is a schema decision, not just infrastructure

---

## Domain 1 — Payments

**Domain purpose:** To record, route, track, and report every movement of money initiated through the Al-Noor platform — whether domestic via SARIE, bill payment via SADAD, or international via SWIFT.

**Domain boundary:** Payments does not own the customer or the account — those belong to the Customer Domain. Payments references them via foreign keys only.

---

### Payments — Entities

| Entity | Purpose |
|--------|---------|
| `PAYMENT` | Core entity. One row per payment instruction. |
| `PAYMENT_STATUS_HISTORY` | Append-only audit trail. Every status transition. Never updated. |
| `EXTERNAL_API_LOG` | Platform-level log of every call to SARIE, SADAD, OFAC, SWIFT. |

---

### Payments — Conceptual Model

<a name="payments--conceptual-model"></a>

```
┌─ CUSTOMER DOMAIN ────────────────────────┐
│   ┌────────────┐    ┌─────────────┐      │
│   │  CUSTOMER  │    │   ACCOUNT   │      │
│   └─────┬──────┘    └──────┬──────┘      │
└─────────┼──────────────────┼─────────────┘
          │ initiates        │ debited by
          ▼                  ▼
┌─ PAYMENTS DOMAIN ──────────────────────────────────────┐
│                    ┌─────────────┐                     │
│                    │   PAYMENT   │                     │
│                    └──────┬──────┘                     │
│              ┌────────────┴────────────┐               │
│              ▼                         ▼               │
│  ┌───────────────────────┐  ┌──────────────────────┐  │
│  │ PAYMENT_STATUS_HISTORY│  │  EXTERNAL_API_LOG    │  │
│  │ (append-only, immutable)  │ (SARIE/OFAC/SADAD) │  │
│  └───────────────────────┘  └──────────────────────┘  │
└────────────────────────────────────────────────────────┘

Payment rails (column values, not separate entities):
  SARIE → domestic SAR interbank
  SADAD → bill payments
  MADA  → card network
  SWIFT → international
  INTERNAL → within Al-Noor
```

---

### Payments — Logical Model

<a name="payments--logical-model"></a>

#### PAYMENT

| Attribute | Type | Constraint | PDPL | Decision Rationale |
|-----------|------|-----------|------|-------------------|
| `payment_id` | UUID | PK, NOT NULL | Internal | UUID not SERIAL — Open Banking TPPs generate IDs externally before submitting. Must be globally unique across all systems. |
| `payment_ref` | VARCHAR(50) | NOT NULL, UNIQUE | Internal | Human-readable business key (PMT-2025-0042). UUID is the system key. Both are needed — different audiences. |
| `payment_rail` | VARCHAR(15) | NOT NULL, CHECK(...) | Internal | CHECK constraint: SARIE/SADAD/MADA/SWIFT/INTERNAL/STCPAY/APPLEPAY. Any value outside this list is a system error. |
| `payment_type` | VARCHAR(20) | NOT NULL, CHECK(...) | Internal | TRANSFER/BILL_PAYMENT/SALARY/INTERNATIONAL/CARD_PAYMENT/REFUND |
| `initiator_customer_id` | CHAR(10) | NOT NULL, FK → customer | Internal | Cross-domain reference. Payments does not own this entity. |
| `debit_account_id` | CHAR(16) | NOT NULL, FK → account | Internal | Cross-domain reference. |
| `credit_account_id` | CHAR(16) | NULLABLE, FK → account | Internal | NULL for external payments — the credit account is not an Al-Noor account. |
| `beneficiary_name` | VARCHAR(200) | NULLABLE | **Confidential** | Third-party personal data under PDPL regardless of how received. Access restricted to authorised payment operations. |
| `beneficiary_iban` | VARCHAR(34) | NULLABLE | **Confidential** | |
| `amount_sar` | NUMERIC(18,2) | NOT NULL, > 0 | Internal | NUMERIC not FLOAT. Binary floating-point accumulates rounding errors across millions of records. NUMERIC stores exact decimals. |
| `foreign_currency` | CHAR(3) | NULLABLE | Internal | NULL for SAR domestic payments. Intentional — represents a real business distinction. |
| `foreign_amount` | NUMERIC(18,2) | NULLABLE | Internal | |
| `exchange_rate` | NUMERIC(10,6) | NULLABLE | Internal | |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'INITIATED', CHECK(...) | Internal | INITIATED/PENDING/PROCESSING/COMPLETED/FAILED/REJECTED/CANCELLED |
| `initiated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Internal | TIMESTAMPTZ not TIMESTAMP — stores absolute UTC moment regardless of server location. |
| `completed_at` | TIMESTAMPTZ | NULLABLE | Internal | |
| `sarie_uetr` | VARCHAR(50) | NULLABLE | Internal | SARIE payments only. A generic `reference_no` cannot distinguish SARIE from SWIFT references — different regulatory purposes. |
| `swift_uetr` | VARCHAR(50) | NULLABLE | Internal | SWIFT payments only. |
| `compliance_screened` | BOOLEAN | NOT NULL, DEFAULT FALSE | Internal | AML and sanctions are independent checks run by different systems. Two booleans, not one status column — one can pass while the other fails. |
| `sanctions_checked` | BOOLEAN | NOT NULL, DEFAULT FALSE | Internal | Both must be TRUE before status can be set to COMPLETED. |

#### PAYMENT_STATUS_HISTORY

| Attribute | Type | Constraint | Decision Rationale |
|-----------|------|-----------|-------------------|
| `history_id` | BIGSERIAL | PK, NOT NULL | Integer PK — high write volume, never exposed externally. Smaller and faster than UUID here. |
| `payment_id` | UUID | NOT NULL, FK → payment | |
| `old_status` | VARCHAR(20) | **NULLABLE** | NULL for the first row — records transition from nothing to INITIATED. Correctly represents "no prior state". |
| `new_status` | VARCHAR(20) | NOT NULL | |
| `changed_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | |
| `changed_by` | VARCHAR(100) | NOT NULL | Staff user ID or system name (e.g. `PAYMENT_ENGINE_v2`). Anonymous transitions are not acceptable in a regulated audit trail. |
| `change_reason` | VARCHAR(255) | NULLABLE | Routine transitions (INITIATED → PROCESSING) do not require a reason. Rejections must have one — enforced by application layer. |

> **Immutability rule:** No UPDATE or DELETE is ever permitted on this table. A trigger enforces this at the database level. A SAMA examiner must be able to trust that what they see is what actually happened.

#### EXTERNAL_API_LOG

| Attribute | Type | Decision Rationale |
|-----------|------|--------------------|
| `service_name` | VARCHAR(50), CHECK(...) | NAFATH/SIMAH/SARIE/SADAD/OFAC/ZATCA/SWIFT_GPI |
| `request_ref` | VARCHAR(100) | The payment_id or application_id that caused this API call. Without it, the log is disconnected from the business event. |
| `customer_id` | CHAR(10) | Reference only — not a PII store. PDPL data minimisation: store only what is needed to trace the call. Raw PII here would require the same restricted controls as the KYC system. |
| `http_status_code` | SMALLINT | Technical result of the API call. |
| `response_status` | VARCHAR(20) | Business result: SUCCESS/FAILED/TIMEOUT/PENDING. An HTTP 200 from SARIE can still mean the payment was rejected by their business rules. Both columns are needed — they are not redundant. |
| `error_message` | VARCHAR(500) | Must be PII-free. The application layer must strip any PII from error messages before writing here. |
| `response_time_ms` | INTEGER | SLA monitoring. If SARIE averages 6,000ms against a 2,000ms SLA, operations needs evidence — not anecdote. |

---

### Payments — Physical DDL

<a name="payments--physical-ddl"></a>

```sql
CREATE SCHEMA payments;

CREATE TABLE payments.payment (
    payment_id             UUID          NOT NULL DEFAULT gen_random_uuid(),
    payment_ref            VARCHAR(50)   NOT NULL,
    payment_rail           VARCHAR(15)   NOT NULL
        CHECK (payment_rail IN ('SARIE','SADAD','MADA','SWIFT','INTERNAL','STCPAY','APPLEPAY')),
    payment_type           VARCHAR(20)   NOT NULL
        CHECK (payment_type IN ('TRANSFER','BILL_PAYMENT','SALARY','INTERNATIONAL','CARD_PAYMENT','REFUND')),
    initiator_customer_id  CHAR(10)      NOT NULL,
    debit_account_id       CHAR(16)      NOT NULL,
    credit_account_id      CHAR(16),
    beneficiary_iban       VARCHAR(34),
    beneficiary_name       VARCHAR(200),       -- PDPL: Confidential
    beneficiary_bank_code  VARCHAR(20),
    amount_sar             NUMERIC(18,2) NOT NULL CHECK (amount_sar > 0),
    foreign_currency       CHAR(3),
    foreign_amount         NUMERIC(18,2),
    exchange_rate          NUMERIC(10,6),
    status                 VARCHAR(20)   NOT NULL DEFAULT 'INITIATED'
        CHECK (status IN ('INITIATED','PENDING','PROCESSING','COMPLETED','FAILED','REJECTED','CANCELLED')),
    initiated_at           TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at           TIMESTAMPTZ,
    sarie_uetr             VARCHAR(50),        -- SARIE payments only
    swift_uetr             VARCHAR(50),        -- SWIFT payments only
    compliance_screened    BOOLEAN       NOT NULL DEFAULT FALSE,
    sanctions_checked      BOOLEAN       NOT NULL DEFAULT FALSE,
    CONSTRAINT pk_payment PRIMARY KEY (payment_id),
    CONSTRAINT uq_payment_ref UNIQUE (payment_ref),
    CONSTRAINT fk_pmt_customer FOREIGN KEY (initiator_customer_id)
        REFERENCES retail.customer(customer_id),
    CONSTRAINT fk_pmt_debit_account FOREIGN KEY (debit_account_id)
        REFERENCES retail.account(account_id),
    CONSTRAINT fk_pmt_credit_account FOREIGN KEY (credit_account_id)
        REFERENCES retail.account(account_id)
);

-- Index 1: Operations morning report — "all failed SARIE payments yesterday"
CREATE INDEX idx_payment_rail_status
    ON payments.payment (payment_rail, status, initiated_at DESC);

-- Index 2: Customer 360 — all payments for a customer in last 90 days
CREATE INDEX idx_payment_customer
    ON payments.payment (initiator_customer_id, initiated_at DESC);

-- Index 3: Live ops dashboard — payments not yet completed (partial index)
CREATE INDEX idx_payment_active
    ON payments.payment (status, initiated_at DESC)
    WHERE status NOT IN ('COMPLETED', 'CANCELLED');

-- ─────────────────────────────────────────────────────────────
-- PAYMENT_STATUS_HISTORY — append-only, immutable audit trail
-- ─────────────────────────────────────────────────────────────
CREATE TABLE payments.payment_status_history (
    history_id     BIGSERIAL    NOT NULL,
    payment_id     UUID         NOT NULL,
    old_status     VARCHAR(20),            -- NULL for first transition
    new_status     VARCHAR(20)  NOT NULL,
    changed_at     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    changed_by     VARCHAR(100) NOT NULL,
    change_reason  VARCHAR(255),
    CONSTRAINT pk_payment_history PRIMARY KEY (history_id),
    CONSTRAINT fk_history_payment FOREIGN KEY (payment_id)
        REFERENCES payments.payment(payment_id)
);

CREATE INDEX idx_pmt_history_payment
    ON payments.payment_status_history (payment_id, changed_at DESC);

-- Immutability trigger — tamper-proof audit trail
CREATE OR REPLACE FUNCTION payments.prevent_history_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'payment_status_history is immutable — rows cannot be %d', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payment_history_immutable
    BEFORE UPDATE OR DELETE ON payments.payment_status_history
    FOR EACH ROW EXECUTE FUNCTION payments.prevent_history_modification();

-- ─────────────────────────────────────────────────────────────
-- EXTERNAL_API_LOG — platform-level, not payments-only
-- ─────────────────────────────────────────────────────────────
CREATE TABLE payments.external_api_log (
    log_id              BIGSERIAL    NOT NULL,
    service_name        VARCHAR(50)  NOT NULL
        CHECK (service_name IN ('NAFATH','SIMAH','SARIE','SADAD','OFAC','ZATCA','SWIFT_GPI')),
    endpoint            VARCHAR(200) NOT NULL,
    http_method         VARCHAR(10)  NOT NULL CHECK (http_method IN ('GET','POST','PUT','PATCH')),
    request_ref         VARCHAR(100),
    customer_id         CHAR(10),           -- reference only, not PII store
    request_timestamp   TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    response_timestamp  TIMESTAMPTZ,
    http_status_code    SMALLINT,
    response_status     VARCHAR(20)
        CHECK (response_status IN ('SUCCESS','FAILED','TIMEOUT','PENDING')),
    error_code          VARCHAR(50),
    error_message       VARCHAR(500),       -- must be PII-free
    response_time_ms    INTEGER,
    CONSTRAINT pk_api_log PRIMARY KEY (log_id)
);

CREATE INDEX idx_api_log_service_time
    ON payments.external_api_log (service_name, request_timestamp DESC);
CREATE INDEX idx_api_log_request_ref
    ON payments.external_api_log (request_ref, request_timestamp DESC);

-- ─────────────────────────────────────────────────────────────
-- REPORTING VIEWS
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW payments.v_daily_payment_summary AS
SELECT
    DATE(p.initiated_at)  AS payment_date,
    p.payment_rail,
    p.payment_type,
    p.status,
    COUNT(*)              AS payment_count,
    SUM(p.amount_sar)     AS total_amount_sar,
    AVG(p.amount_sar)     AS avg_amount_sar
FROM payments.payment p
WHERE p.initiated_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(p.initiated_at), p.payment_rail, p.payment_type, p.status
ORDER BY payment_date DESC, total_amount_sar DESC;

CREATE OR REPLACE VIEW payments.v_api_sla_monitor AS
SELECT
    service_name,
    COUNT(*)                                                   AS total_calls,
    COUNT(*) FILTER (WHERE response_status = 'SUCCESS')        AS successful_calls,
    COUNT(*) FILTER (WHERE response_status = 'FAILED')         AS failed_calls,
    COUNT(*) FILTER (WHERE response_status = 'TIMEOUT')        AS timeouts,
    ROUND(AVG(response_time_ms))                               AS avg_response_ms,
    MAX(response_time_ms)                                      AS max_response_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) AS p95_response_ms
FROM payments.external_api_log
WHERE request_timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY service_name
ORDER BY avg_response_ms DESC;
```

---

### Payments — Scenario Trace

<a name="payments--scenario-trace"></a>

**Scenario: A customer initiates a SAR 85,000 SARIE transfer.**

```
Step 1: WRITE → payments.payment
          status: INITIATED, compliance_screened: FALSE, sanctions_checked: FALSE

        WRITE → payments.payment_status_history
          old_status: NULL, new_status: INITIATED, changed_by: MOBILE_APP_v4.2

Step 2: AML screening (amount > SAR 60,000 — SAMA threshold)
        WRITE → payments.external_api_log  (service: OFAC, response: SUCCESS)
        UPDATE → payments.payment  (sanctions_checked: TRUE)
        WRITE → payments.payment_status_history  (INITIATED → PROCESSING)

Step 3: Compliance screening completes
        UPDATE → payments.payment  (compliance_screened: TRUE, status: PROCESSING)

Step 4: Payment submitted to SARIE
        WRITE → payments.external_api_log  (service: SARIE, response_time_ms: 1842)
        UPDATE → payments.payment
          (sarie_uetr: 'f47ac10b-...', status: COMPLETED, completed_at: NOW())
        WRITE → payments.payment_status_history  (PROCESSING → COMPLETED)

RESULT: Every step traced. No table missing. Schema is complete for this scenario.
```

**Alternative — OFAC sanctions match:**
```
Step 2 (alt): WRITE → external_api_log  (service: OFAC, response_status: SUCCESS ← API succeeded)
              UPDATE → payments.payment  (sanctions_checked: TRUE, status: REJECTED)
              WRITE → payment_status_history
                (old: INITIATED, new: REJECTED, reason: 'OFAC_SANCTIONS_MATCH — ref: OFX-847')
              → No further steps. Record permanent. Full trail visible to SAMA examiner.
```

---

## Domain 2 — Customer

**Domain purpose:** To be the single authoritative source of truth for who Al-Noor Bank's customers are — their identity, verification status, risk profile, consent to data processing, and relationship to the bank's products and accounts.

**Domain boundary:** Customer owns customer identity and relationships. It does not own what the customer has bought (Orders), how the customer pays (Payments), or what the customer can buy (Product). Every other domain references the Customer Domain.

---

### Customer — Entities

| Entity | Purpose |
|--------|---------|
| `CUSTOMER` | Abstract parent. Shared identity — KYC status, risk rating, PEP flag, onboarding channel. |
| `INDIVIDUAL_CUSTOMER` | Subtype for natural persons. NID, DOB, nationality, income, employment. |
| `CORPORATE_CUSTOMER` | Subtype for legal entities. CR number, VAT, GOSI, authorised signatory. |
| `KYC_RECORD` | One record per KYC review. Append-only. SAMA audit trail. |
| `CUSTOMER_CONTACT` | Phone, email, address. Separate — multiple per customer, different PDPL retention. |
| `CUSTOMER_DOCUMENT` | Identity document references. High PDPL sensitivity. |
| `CUSTOMER_CONSENT` | PDPL compliance entity. One row per processing purpose per customer. |

---

### Customer — Conceptual Model

<a name="customer--conceptual-model"></a>

```
┌─ CUSTOMER DOMAIN ──────────────────────────────────────────────────┐
│                    ┌─────────────┐                                 │
│                    │  CUSTOMER   │  ← abstract parent              │
│                    └──────┬──────┘                                 │
│              ┌────────────┴────────────┐                           │
│              │ 1:1                     │ 1:1                        │
│              ▼                         ▼                           │
│  ┌───────────────────┐   ┌───────────────────────┐                 │
│  │  INDIVIDUAL_      │   │  CORPORATE_           │                 │
│  │  CUSTOMER 🔒      │   │  CUSTOMER             │                 │
│  │  NID, DOB,        │   │  CR No, VAT, GOSI,   │                 │
│  │  nationality,     │   │  authorised signatory ──────N:1──┐      │
│  │  income           │   │                       │         │      │
│  └───────────────────┘   └───────────────────────┘         │      │
│                                                             ▼      │
│  Supporting entities (all 1:N per customer):          (references  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐   individual)  │
│  │ KYC_RECORD  │  │  CUSTOMER_   │  │ CUSTOMER_  │               │
│  │ (immutable) │  │  CONSENT     │  │ DOCUMENT 🔒│               │
│  └─────────────┘  └──────────────┘  └────────────┘               │
│                                                                    │
│  CUSTOMER ──── M:M (via customer_account bridge) ──── ACCOUNT      │
│  relationship: PRIMARY / JOINT / AUTHORISED_SIGNATORY / GUARDIAN   │
│                                                                    │
│  🔒 = Contains PDPL-restricted or confidential personal data       │
└────────────────────────────────────────────────────────────────────┘

Referenced by: Orders (application.customer_id), Payments (payment.initiator_customer_id)
```

---

### Customer — Logical Model

<a name="customer--logical-model"></a>

#### CUSTOMER (Parent)

| Attribute | Type | Constraint | Decision Rationale |
|-----------|------|-----------|-------------------|
| `customer_id` | CHAR(10) | PK, NOT NULL | CIF number from Core Banking — the natural key. It already exists in the source system, is stable, and is meaningful. SERIAL would create a second identifier with no business meaning. |
| `customer_type` | CHAR(1) | NOT NULL, CHECK('I','C') | Discriminator. CHECK prevents any value other than I (Individual) or C (Corporate). |
| `risk_rating` | CHAR(1) | NOT NULL, DEFAULT 'L', CHECK('H','M','L') | DEFAULT 'L' — safest default. A system failure in AML assessment cannot accidentally grant a new customer a HIGH rating. Default to conservative; upgrade with evidence. |
| `kyc_status` | VARCHAR(20) | NOT NULL, DEFAULT 'PENDING' | DEFAULT 'PENDING' not 'VERIFIED' — a customer who just arrived has not been verified. Prevents activation without completed verification. |
| `is_pep` | BOOLEAN | NOT NULL, DEFAULT FALSE | Boolean not a separate PEP entity — queried on every transaction and application. Must be a single column read, not a JOIN. |
| `is_sanctioned` | BOOLEAN | NOT NULL, DEFAULT FALSE | Same rationale. When TRUE, the system must immediately block all transactions. |
| `onboarding_channel` | VARCHAR(20) | NOT NULL, CHECK(BRANCH, DIGITAL, API, MIGRATION) | SAMA tracks digital vs branch onboarding separately. CHECK prevents any channel outside the list from entering the system. |

#### INDIVIDUAL_CUSTOMER (Subtype)

| Attribute | Type | PDPL | Decision Rationale |
|-----------|------|------|-------------------|
| `customer_id` | CHAR(10) | — | **Both PK and FK to customer parent.** This enforces the 1:1 relationship structurally. You cannot insert an individual row without a matching parent row. You cannot have two individual rows for one customer. |
| `national_id` | VARCHAR(15) | 🔒 Restricted | VARCHAR not INTEGER — Saudi NIDs have leading zeros that INTEGER silently drops. UNIQUE constraint ensures no two customers share the same NID. |
| `full_name_ar` | NVARCHAR(200) | Confidential | |
| `date_of_birth` | DATE | 🔒 Restricted | Combined with name and nationality, is sufficient to uniquely identify an individual. Requires encryption at rest. |
| `mobile_number` | VARCHAR(15) | 🔒 Restricted | More sensitive than a name — can be used to contact, track, or impersonate. |
| `email_address` | VARCHAR(200) | Confidential | **NULLABLE** — not all Saudi bank customers have email. Making it mandatory would exclude significant population segments. |
| `monthly_income_sar` | NUMERIC(15,2) | 🔒 Restricted | Under PDPL, data revealing financial circumstances is sensitive personal data. Restricted means encrypted at rest + access restricted to credit assessment roles only. |
| `employment_status` | VARCHAR(20) | — | CHECK(EMPLOYED, SELF_EMPLOYED, RETIRED, STUDENT, UNEMPLOYED) |

#### CORPORATE_CUSTOMER (Subtype)

| Attribute | Type | Decision Rationale |
|-----------|------|--------------------|
| `customer_id` | CHAR(10) | PK + FK to parent — same 1:1 subtype enforcement |
| `commercial_reg_no` | VARCHAR(20) | UNIQUE — no two corporate customers share the same CR number |
| `vat_number` | VARCHAR(15) | NULLABLE — not all corporate customers are VAT-registered |
| `authorised_signatory_id` | CHAR(10) | FK → `individual_customer` (not → `customer`). The signatory must be a natural person. A corporate entity cannot sign on behalf of another corporate. The FK to the subtype table enforces this structurally. |
| `annual_revenue_sar` | NUMERIC(15,2) | Confidential (not Restricted) — corporate financial data is commercially sensitive but is not personal data under PDPL, which applies to natural persons. |

#### CUSTOMER_CONSENT

| Attribute | Type | Decision Rationale |
|-----------|------|--------------------|
| `processing_purpose` | VARCHAR(50) | CHECK constraint — valid purposes are defined by PDPL policy. No new purpose can be added without a schema change requiring compliance review. |
| `legal_basis` | VARCHAR(30) | CHECK(CONSENT, CONTRACT, LEGAL_OBLIGATION, LEGITIMATE_INTEREST) — PDPL requires this to be queryable. "What is the legal basis for processing this customer's credit bureau data?" must be answered from the database. |
| `consent_given` | BOOLEAN | Stores FALSE rows explicitly — a refusal is as important as a consent. Absence of a row is ambiguous. A FALSE row is unambiguous. |
| `withdrawn_at` | TIMESTAMPTZ | Not a status column — captures the exact legal moment processing obligations changed. Any processing after this timestamp is a PDPL violation. |
| `consent_expiry` | DATE | NULLABLE — marketing consent may need renewal. System checks this before sending communications. |

---

### Customer — Physical DDL

<a name="customer--physical-ddl"></a>

```sql
CREATE SCHEMA retail;
CREATE SCHEMA compliance;

CREATE TABLE retail.customer (
    customer_id          CHAR(10)     NOT NULL,
    customer_type        CHAR(1)      NOT NULL CHECK (customer_type IN ('I','C')),
    customer_segment     VARCHAR(30)  NOT NULL,
    risk_rating          CHAR(1)      NOT NULL DEFAULT 'L' CHECK (risk_rating IN ('H','M','L')),
    kyc_status           VARCHAR(20)  NOT NULL DEFAULT 'PENDING'
        CHECK (kyc_status IN ('VERIFIED','EXPIRED','PENDING','REJECTED')),
    kyc_last_reviewed    DATE         NOT NULL,
    onboarding_channel   VARCHAR(20)  NOT NULL
        CHECK (onboarding_channel IN ('BRANCH','DIGITAL','API','MIGRATION')),
    onboarding_date      DATE         NOT NULL DEFAULT CURRENT_DATE,
    is_pep               BOOLEAN      NOT NULL DEFAULT FALSE,
    is_sanctioned        BOOLEAN      NOT NULL DEFAULT FALSE,
    is_deleted           BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at           TIMESTAMPTZ,
    legal_hold           BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_customer PRIMARY KEY (customer_id)
);

-- KYC expiry job — "all high-risk customers reviewed more than 12 months ago"
CREATE INDEX idx_customer_kyc_review
    ON retail.customer (risk_rating, kyc_last_reviewed);

-- PEP customers are a tiny minority — partial index on TRUE rows only
CREATE INDEX idx_customer_pep
    ON retail.customer (is_pep) WHERE is_pep = TRUE;

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
        CHECK (employment_status IN ('EMPLOYED','SELF_EMPLOYED','RETIRED','STUDENT','UNEMPLOYED')),
    employer_name        VARCHAR(200),
    nafath_verified      BOOLEAN       NOT NULL DEFAULT FALSE,
    nafath_verified_at   TIMESTAMPTZ,
    CONSTRAINT pk_individual_customer PRIMARY KEY (customer_id),
    CONSTRAINT fk_individual_parent FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id),
    CONSTRAINT uq_national_id UNIQUE (national_id)
);

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
    CONSTRAINT pk_corporate_customer PRIMARY KEY (customer_id),
    CONSTRAINT fk_corporate_parent FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id),
    CONSTRAINT uq_commercial_reg UNIQUE (commercial_reg_no),
    CONSTRAINT fk_signatory FOREIGN KEY (authorised_signatory_id)
        REFERENCES retail.individual_customer(customer_id)
);

CREATE TABLE compliance.kyc_record (
    kyc_id         SERIAL       NOT NULL,
    customer_id    CHAR(10)     NOT NULL,
    reviewed_date  DATE         NOT NULL,
    reviewer_id    VARCHAR(50)  NOT NULL,   -- officer ID or system name
    outcome        VARCHAR(20)  NOT NULL CHECK (outcome IN ('PASS','FAIL','PENDING','ESCALATED')),
    expiry_date    DATE         NOT NULL,   -- computed at write time from risk_rating
    notes          TEXT,
    CONSTRAINT pk_kyc_record PRIMARY KEY (kyc_id),
    CONSTRAINT fk_kyc_customer FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id)
);

CREATE INDEX idx_kyc_customer_date
    ON compliance.kyc_record (customer_id, reviewed_date DESC);

-- KYC records are permanent — immutability trigger
CREATE OR REPLACE FUNCTION compliance.prevent_kyc_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'kyc_record is immutable — rows cannot be %d', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_kyc_immutable
    BEFORE UPDATE OR DELETE ON compliance.kyc_record
    FOR EACH ROW EXECUTE FUNCTION compliance.prevent_kyc_modification();

CREATE TABLE compliance.customer_consent (
    consent_id           SERIAL       NOT NULL,
    customer_id          CHAR(10)     NOT NULL,
    processing_purpose   VARCHAR(50)  NOT NULL
        CHECK (processing_purpose IN (
            'ACCOUNT_OPERATIONS','MARKETING_COMMS','CREDIT_BUREAU_SHARE',
            'OPEN_BANKING_SHARE','ANALYTICS_PROFILING','AML_COMPLIANCE')),
    legal_basis          VARCHAR(30)  NOT NULL
        CHECK (legal_basis IN ('CONSENT','CONTRACT','LEGAL_OBLIGATION','LEGITIMATE_INTEREST')),
    consent_given        BOOLEAN      NOT NULL,
    consent_date         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    consent_expiry       DATE,
    consent_method       VARCHAR(20)  NOT NULL
        CHECK (consent_method IN ('APP','BRANCH_FORM','WEBSITE','IVR')),
    withdrawn_at         TIMESTAMPTZ,
    CONSTRAINT pk_consent PRIMARY KEY (consent_id),
    CONSTRAINT fk_consent_customer FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id),
    CONSTRAINT uq_consent_purpose UNIQUE (customer_id, processing_purpose)
);

-- KYC Expiry Dashboard view for compliance team
CREATE OR REPLACE VIEW compliance.v_kyc_expiry_dashboard AS
SELECT
    c.customer_id, ic.full_name_en, c.customer_segment, c.risk_rating, c.kyc_status,
    c.kyc_last_reviewed,
    CURRENT_DATE - c.kyc_last_reviewed AS days_since_review,
    CASE c.risk_rating
        WHEN 'H' THEN c.kyc_last_reviewed + INTERVAL '1 year'
        WHEN 'M' THEN c.kyc_last_reviewed + INTERVAL '2 years'
        WHEN 'L' THEN c.kyc_last_reviewed + INTERVAL '3 years'
    END AS review_deadline,
    CASE
        WHEN c.kyc_status = 'EXPIRED' THEN 'OVERDUE'
        WHEN (CASE c.risk_rating
                WHEN 'H' THEN c.kyc_last_reviewed + INTERVAL '1 year'
                WHEN 'M' THEN c.kyc_last_reviewed + INTERVAL '2 years'
                ELSE          c.kyc_last_reviewed + INTERVAL '3 years'
              END) <= CURRENT_DATE + INTERVAL '30 days' THEN 'DUE_SOON'
        ELSE 'CURRENT'
    END AS kyc_urgency
FROM retail.customer c
JOIN retail.individual_customer ic ON c.customer_id = ic.customer_id
WHERE c.is_deleted = FALSE AND c.customer_type = 'I'
ORDER BY kyc_urgency, review_deadline;
```

---

### Customer — Scenario Trace

<a name="customer--scenario-trace"></a>

**Scenario: A Saudi national applies digitally for a Tawarruq Account.**

```
Step 1: WRITE → retail.customer
          (customer_id: C000000005, kyc_status: PENDING, risk_rating: L, onboarding_channel: DIGITAL)
        WRITE → retail.individual_customer
          (national_id: 1122334455, nafath_verified: FALSE)

Step 2: Nafath eKYC
        WRITE → payments.external_api_log  (service: NAFATH, response: SUCCESS)
        UPDATE → retail.individual_customer  (nafath_verified: TRUE)

Step 3: KYC record created
        WRITE → compliance.kyc_record
          (outcome: PASS, reviewer_id: AUTO_NAFATH_VERIFY_v3, expiry_date: +3 years)
        UPDATE → retail.customer  (kyc_status: VERIFIED)

Step 4: PDPL consent recorded
        WRITE → compliance.customer_consent  (purpose: ACCOUNT_OPERATIONS, basis: CONTRACT, given: TRUE)
        WRITE → compliance.customer_consent  (purpose: AML_COMPLIANCE, basis: LEGAL_OBLIGATION, given: TRUE)
        WRITE → compliance.customer_consent  (purpose: MARKETING_COMMS, basis: CONSENT, given: FALSE)
          ↑ Omar declined marketing. The FALSE row is recorded — not just absent.

Step 5: Account opened
        WRITE → retail.account  (account_type: TAWARRUQ, status: ACTIVE)
        WRITE → retail.customer_account  (relationship: PRIMARY)
```

---

## Domain 3 — Product

**Domain purpose:** To define and govern every financial product Al-Noor Bank can offer — what it is called, what its terms are, what it costs, whether it is Sharia-compliant, and who has approved it.

**Domain boundary:** Product owns the definition of what can be sold. It does not own who applies (Orders), how many can be approved (Inventory), or the customer buying it (Customer). Other domains reference Product — Product does not reference them.

---

### Product — Entities

| Entity | Purpose |
|--------|---------|
| `PRODUCT_CATEGORY` | Grouping type. `is_islamic` flag at category level propagates Sharia requirements to all products in the category. |
| `PRODUCT` | The product itself. One row per product. `ssb_approval_ref` is mandatory for all Islamic products — enforced by CHECK. |
| `PRODUCT_TERMS` | Versioned commercial terms. Effective + expiry dates. Never overwritten — append only. |
| `PRODUCT_PRICING` | Rate per customer segment. PREMIUM vs STANDARD vs YOUTH — separate rows, not separate columns. |

---

### Product — Conceptual Model

<a name="product--conceptual-model"></a>

```
┌─ PRODUCT DOMAIN ─────────────────────────────────────────────────┐
│   ┌─────────────────────┐                                        │
│   │   PRODUCT_CATEGORY  │  is_islamic flag governs all products  │
│   └──────────┬──────────┘                                        │
│              │ 1:N                                               │
│              ▼                                                   │
│   ┌──────────────────────────────────────────────┐              │
│   │               PRODUCT                        │              │
│   │  🔑 ssb_approval_ref — mandatory if Islamic  │              │
│   │     enforced by CHECK at database level       │              │
│   └───────┬──────────────────────┬───────────────┘              │
│           │ 1:N versioned        │ 1:N by segment               │
│           ▼                      ▼                              │
│   ┌──────────────┐    ┌──────────────────────┐                 │
│   │ PRODUCT_TERMS│    │  PRODUCT_PRICING      │                 │
│   │ effective +  │    │  PREMIUM / STANDARD   │                 │
│   │ expiry dates │    │  YOUTH / CORPORATE    │                 │
│   └──────────────┘    └──────────────────────┘                 │
└──────────────────────────────────────────────────────────────────┘

Referenced by:
→ Orders Domain    (product_application.product_id)
→ Inventory Domain (product_quota.product_id)
```

---

### Product — Logical Model

<a name="product--logical-model"></a>

#### PRODUCT

| Attribute | Type | Decision Rationale |
|-----------|------|--------------------|
| `product_id` | VARCHAR(15) | Not SERIAL — `PROD_MRB_002` is immediately readable. Every table carrying this ID is self-documenting. SERIAL would produce `1234` — meaningless without a JOIN. |
| `product_name_ar` | VARCHAR(200) | SAMA regulatory submissions require Arabic names. Both stored — translation at runtime is fragile and produces inconsistencies across reports. |
| `product_code` | VARCHAR(20) | UNIQUE. Separate from product_id — business-facing code printed on contracts and SAMA submissions. If a product is reissued with a new internal ID, the customer-facing code may remain the same. |
| `is_sharia_compliant` | BOOLEAN | NOT NULL |
| `ssb_approval_ref` | VARCHAR(50) | **The most important constraint in the platform:** `CHECK (is_sharia_compliant = FALSE OR ssb_approval_ref IS NOT NULL)`. An Islamic product without SSB approval could invalidate every contract under it. Application code can be bypassed. The CHECK constraint cannot be bypassed by anything. |
| `min_age_years` | SMALLINT | DEFAULT 18. Stored at schema level — onboarding platform queries it rather than hardcoding eligibility rules in application code. |
| `max_exposure_sar` | NUMERIC(18,2) | NULLABLE — NULL means "no limit applies". Zero would mean "no exposure allowed" — which is wrong. |

#### PRODUCT_TERMS (Versioned)

| Attribute | Type | Decision Rationale |
|-----------|------|--------------------|
| `effective_date` | DATE | NOT NULL |
| `expiry_date` | DATE | NULLABLE — the current version has no expiry date (NULL = currently in effect). When a new version is created, the previous row's expiry_date is set to the new version's effective_date. |
| `profit_rate_pct` | NUMERIC(5,2) | NULLABLE — current accounts have no profit rate. NULL means "not applicable for this product type". |

> **Why versioned terms, not a single overwriteable row?**
> A customer's Murabaha contract must reference the terms active at the time of signing — not today's terms. If rates change after signing, the customer's contract uses the historical version. This point-in-time query is only possible with effective/expiry date versioning.

#### PRODUCT_PRICING

| Attribute | Type | Decision Rationale |
|-----------|------|--------------------|
| `customer_segment` | VARCHAR(30) | NOT NULL. Separate table — same product, different price per segment. A PREMIUM customer gets 3.99%; STANDARD gets 4.25%. Embedding this in PRODUCT requires a column per segment — which breaks when a new segment is created. A separate table requires one new row. |
| `profit_rate_pct` | NUMERIC(5,2) | NOT NULL. NUMERIC not FLOAT — 4.25% stored as FLOAT may be 4.249999... on a contract. |

---

### Product — Physical DDL

<a name="product--physical-ddl"></a>

```sql
CREATE SCHEMA product_domain;

CREATE TABLE product_domain.product_category (
    category_id   VARCHAR(10)  NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    is_islamic    BOOLEAN      NOT NULL DEFAULT FALSE,
    description   TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_product_category PRIMARY KEY (category_id)
);

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
    max_exposure_sar    NUMERIC(18,2),
    currency            CHAR(3)       NOT NULL DEFAULT 'SAR',
    is_sharia_compliant BOOLEAN       NOT NULL,
    ssb_approval_ref    VARCHAR(50),
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_product PRIMARY KEY (product_id),
    CONSTRAINT uq_product_code UNIQUE (product_code),
    CONSTRAINT fk_product_category FOREIGN KEY (category_id)
        REFERENCES product_domain.product_category(category_id),
    -- Islamic governance enforced at DB level — cannot be bypassed by application code
    CONSTRAINT chk_sharia_approval
        CHECK (is_sharia_compliant = FALSE OR ssb_approval_ref IS NOT NULL)
);

CREATE INDEX idx_product_active ON product_domain.product (is_active) WHERE is_active = TRUE;
CREATE INDEX idx_product_category ON product_domain.product (category_id, is_active);

CREATE TABLE product_domain.product_terms (
    terms_id          SERIAL        NOT NULL,
    product_id        VARCHAR(15)   NOT NULL,
    effective_date    DATE          NOT NULL,
    expiry_date       DATE,                     -- NULL = currently active
    profit_rate_pct   NUMERIC(5,2),
    min_tenure_months SMALLINT,
    max_tenure_months SMALLINT,
    min_amount_sar    NUMERIC(18,2),
    max_amount_sar    NUMERIC(18,2),
    early_settle_fee  NUMERIC(5,2),
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_product_terms PRIMARY KEY (terms_id),
    CONSTRAINT fk_terms_product FOREIGN KEY (product_id)
        REFERENCES product_domain.product(product_id),
    CONSTRAINT chk_terms_dates CHECK (expiry_date IS NULL OR expiry_date > effective_date)
);

CREATE INDEX idx_terms_product_date
    ON product_domain.product_terms (product_id, effective_date DESC);

CREATE TABLE product_domain.product_pricing (
    pricing_id       SERIAL        NOT NULL,
    product_id       VARCHAR(15)   NOT NULL,
    customer_segment VARCHAR(30)   NOT NULL,
    profit_rate_pct  NUMERIC(5,2)  NOT NULL,
    effective_date   DATE          NOT NULL,
    expiry_date      DATE,
    CONSTRAINT pk_pricing PRIMARY KEY (pricing_id),
    CONSTRAINT fk_pricing_product FOREIGN KEY (product_id)
        REFERENCES product_domain.product(product_id)
);

-- Active catalogue view — queried on every product page load
CREATE OR REPLACE VIEW product_domain.v_active_product_catalogue AS
SELECT
    p.product_id, p.product_name_en, p.product_name_ar, p.product_code,
    pc.category_name, pc.is_islamic, p.is_sharia_compliant, p.ssb_approval_ref,
    p.min_age_years, p.min_balance_sar,
    pt.profit_rate_pct AS current_profit_rate_pct,
    pt.min_tenure_months, pt.max_tenure_months, pt.min_amount_sar, pt.max_amount_sar
FROM product_domain.product p
JOIN product_domain.product_category pc ON p.category_id = pc.category_id
LEFT JOIN product_domain.product_terms pt
    ON p.product_id = pt.product_id
    AND pt.effective_date <= CURRENT_DATE
    AND (pt.expiry_date IS NULL OR pt.expiry_date > CURRENT_DATE)
WHERE p.is_active = TRUE;

-- Sample data
INSERT INTO product_domain.product_category VALUES
    ('CAT_DEP','Islamic Deposits', TRUE, 'SSB approval required'),
    ('CAT_FIN','Islamic Financing',TRUE, 'SSB approval required'),
    ('CAT_CRD','Cards',           FALSE,'Debit and credit cards');

INSERT INTO product_domain.product
    (product_id, category_id, product_name_en, product_name_ar, product_code,
     is_active, launch_date, is_sharia_compliant, ssb_approval_ref, max_exposure_sar)
VALUES
    ('PROD_MRB_001','CAT_FIN','Murabaha Personal Finance','تمويل شخصي مرابحة',
     'ALN-MRB-001',TRUE,'2024-01-01',TRUE,'SSB-2023-0044',500000),
    ('PROD_MRB_002','CAT_FIN','Murabaha Home Finance','تمويل عقاري مرابحة',
     'ALN-MRB-002',TRUE,'2024-01-01',TRUE,'SSB-2023-0044',5000000);
```

---

### Product — Scenario Trace

<a name="product--scenario-trace"></a>

**Scenario: PREMIUM customer applies for Murabaha Home Finance — platform shows eligibility and rate.**

```
Step 1: Platform loads available products
        READ → product_domain.v_active_product_catalogue
          WHERE is_active = TRUE AND is_sharia_compliant = TRUE AND min_age_years <= [customer age]
          → Returns PROD_MRB_002 with current terms

        READ → product_domain.product_pricing
          WHERE product_id = 'PROD_MRB_002' AND customer_segment = 'PREMIUM'
          → Returns profit_rate_pct = 3.99

Step 2: Application submitted — point-in-time terms snapshot
        READ → product_domain.product_terms
          WHERE product_id = 'PROD_MRB_002'
          AND effective_date <= application_date
          AND (expiry_date IS NULL OR expiry_date > application_date)
          → Terms at APPLICATION DATE used for contract — even if rates change later

Invalid attempt — Islamic product without SSB reference:
        INSERT INTO product_domain.product
          (is_sharia_compliant = TRUE, ssb_approval_ref = NULL)
        → ERROR: violates constraint chk_sharia_approval
        → Product cannot be created. No application can be taken.
        → Governance enforced at database level — not in application code.
```

---

## Domain 4 — Orders

**Domain purpose:** To manage the complete lifecycle of every product application — from the moment a customer submits to the moment the product becomes active — and to preserve an immutable record of every decision made along the way.

**Domain boundary:** Orders references Customer, Product, and Inventory. On FULFILLED it creates records in Customer Domain (account) and updates Inventory Domain (quota). The FULFILLED update must be in a single atomic transaction.

---

### Orders — Entities

| Entity | Purpose |
|--------|---------|
| `PRODUCT_APPLICATION` | Core entity. One per application. Contains all compliance gate results and the decision. |
| `APPLICATION_STATUS_HISTORY` | Append-only, immutable audit trail. Every status transition. BIGSERIAL PK. |
| `MURABAHA_CONTRACT` | Created on FULFILLED for financing applications. Terms are fixed at inception. |
| `MURABAHA_SCHEDULE` | One row per instalment. 240 rows for a 20-year contract. Drives SAMA NPF reporting. |

---

### Orders — Conceptual Model

<a name="orders--conceptual-model"></a>

```
┌─ CUSTOMER DOMAIN ──┐    ┌─ PRODUCT DOMAIN ──┐
│     CUSTOMER        │    │     PRODUCT        │
└────────┬────────────┘    └─────────┬──────────┘
         │ submits                   │ applied for
         ▼                           ▼
┌─ ORDERS DOMAIN ──────────────────────────────────────────────────┐
│          ┌──────────────────────────────────┐                   │
│          │       PRODUCT_APPLICATION         │                   │
│          │  AML · Nafath · SIMAH · Decision  │                   │
│          └───────────────┬──────────────────┘                   │
│          ┌───────────────┴──────────────┐                        │
│          │ has history                  │ results in (FULFILLED) │
│          ▼                              ▼                        │
│  ┌────────────────────┐   ┌─────────────────────────────┐       │
│  │ APPLICATION_STATUS │   │     MURABAHA_CONTRACT        │       │
│  │ _HISTORY           │   │  total = cost + profit        │       │
│  │ (immutable)        │   │  enforced by CHECK            │       │
│  └────────────────────┘   └──────────────┬──────────────┘       │
│                                          │ generates             │
│                                          ▼                       │
│                               ┌──────────────────────┐           │
│                               │   MURABAHA_SCHEDULE  │           │
│                               │  one row per month   │           │
│                               │  drives NPF query    │           │
│                               └──────────────────────┘           │
│                                                                  │
│  On FULFILLED (single atomic transaction):                        │
│  → CREATE retail.account       (Customer Domain)                  │
│  → CREATE retail.customer_account                                 │
│  → UPDATE inventory_domain.product_quota  (Inventory Domain)     │
└──────────────────────────────────────────────────────────────────┘
```

---

### Orders — Logical Model

<a name="orders--logical-model"></a>

#### PRODUCT_APPLICATION

| Attribute | Type | Decision Rationale |
|-----------|------|--------------------|
| `application_id` | VARCHAR(20) | Not UUID — human-readable format (APP-2025-0042). SAMA examiners and customers reference this in correspondence. UUID makes verbal reference impossible. |
| `status` | VARCHAR(20) | CHECK(SUBMITTED, UNDER_REVIEW, PENDING_DOCS, APPROVED, REJECTED, FULFILLED, WITHDRAWN). Seven specific states. CHECK makes `status = 'PROCESSING'` (a payment concept) impossible to store on an application. |
| `decision_by` | VARCHAR(100) | NULLABLE — populated on decision. Must identify either the officer (OFFICER_A42) or the automated system (AUTO_CREDIT_ENGINE_v3). Anonymous approvals are not acceptable. |
| `aml_check_status` | VARCHAR(15) | CHECK(CLEAR, FLAGGED, PENDING). Three states not a boolean — PENDING means "check has not completed yet". A boolean TRUE/FALSE cannot represent PENDING. NULL would be ambiguous. |
| `credit_bureau_score` | SMALLINT | CHECK(300-900). Saudi SIMAH scores run 300–900. Any value outside is a system error or data corruption. |
| `nafath_verified` | BOOLEAN | NOT NULL, DEFAULT FALSE |

#### APPLICATION_STATUS_HISTORY

| Attribute | Type | Decision Rationale |
|-----------|------|--------------------|
| `history_id` | BIGSERIAL | Not SERIAL — at 100K applications/month × 5–6 transitions each = ~6M rows/month. SERIAL overflows in ~17 years at this volume. BIGSERIAL never overflows. |
| `old_status` | VARCHAR(20) | NULLABLE — first row for any application has no prior status. NULL = "this is the first state". |
| `changed_by` | VARCHAR(100) | NOT NULL always. Never anonymous. |
| `changed_at` | TIMESTAMPTZ | Not TIMESTAMP — SAMA examinations reference timestamps. Naive timestamps shift when server timezone changes. TIMESTAMPTZ stores the absolute UTC moment. |

#### MURABAHA_CONTRACT

| Attribute | Type | Decision Rationale |
|-----------|------|--------------------|
| `asset_cost_sar` | NUMERIC(18,2) | 🔒 PDPL Restricted — reveals financial capacity of individual |
| `profit_amount_sar` | NUMERIC(18,2) | 🔒 Restricted |
| `total_sale_price` | NUMERIC(18,2) | **CHECK (total_sale_price = asset_cost_sar + profit_amount_sar)** — enforces the Islamic finance principle that profit is fixed and disclosed at inception. Application bugs cannot silently change the margin after signing. In Murabaha, the profit is disclosed and frozen. |
| `ssb_approval_ref` | VARCHAR(50) | NOT NULL — links this specific contract to the SSB approval. |

#### MURABAHA_SCHEDULE

| Attribute | Type | Decision Rationale |
|-----------|------|--------------------|
| `principal_portion` + `profit_portion` | NUMERIC(18,2) | Stored at generation time. SAMA examiners and customers can ask "of my SAR 2,437.50 payment, how much was principal vs profit?" Recalculating from contract terms at query time is expensive and error-prone across 5,000 active contracts. |
| CHECK constraint | — | `instalment_sar = principal_portion + profit_portion` — same principle as contract level. |
| `status` | VARCHAR(15) | CHECK(PENDING, PAID, OVERDUE, SETTLED_EARLY). Nightly job sets OVERDUE: `UPDATE WHERE status = 'PENDING' AND due_date < CURRENT_DATE`. SAMA NPF queries filter on `status = 'OVERDUE'`. |

---

### Orders — Physical DDL

<a name="orders--physical-ddl"></a>

```sql
CREATE SCHEMA orders_domain;

CREATE TABLE orders_domain.product_application (
    application_id           VARCHAR(20)   NOT NULL,
    customer_id              CHAR(10)      NOT NULL,
    product_id               VARCHAR(15)   NOT NULL,
    application_date         DATE          NOT NULL DEFAULT CURRENT_DATE,
    channel                  VARCHAR(20)   NOT NULL CHECK (channel IN ('MOBILE','WEB','BRANCH','API')),
    status                   VARCHAR(20)   NOT NULL DEFAULT 'SUBMITTED'
        CHECK (status IN ('SUBMITTED','UNDER_REVIEW','PENDING_DOCS','APPROVED','REJECTED','FULFILLED','WITHDRAWN')),
    requested_amount_sar     NUMERIC(18,2),
    requested_tenure_months  SMALLINT,
    purpose_of_finance       VARCHAR(100),
    decision_date            DATE,
    decision_by              VARCHAR(100),
    rejection_reason         VARCHAR(255),
    approved_amount_sar      NUMERIC(18,2),
    approved_profit_rate     NUMERIC(5,2),
    aml_check_status         VARCHAR(15)   CHECK (aml_check_status IN ('CLEAR','FLAGGED','PENDING')),
    credit_bureau_score      SMALLINT      CHECK (credit_bureau_score BETWEEN 300 AND 900),
    nafath_verified          BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at               TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_application PRIMARY KEY (application_id),
    CONSTRAINT fk_app_customer FOREIGN KEY (customer_id)
        REFERENCES retail.customer(customer_id),
    CONSTRAINT fk_app_product FOREIGN KEY (product_id)
        REFERENCES product_domain.product(product_id)
);

CREATE INDEX idx_app_status   ON orders_domain.product_application (status, application_date DESC);
CREATE INDEX idx_app_customer ON orders_domain.product_application (customer_id, application_date DESC);

CREATE TABLE orders_domain.application_status_history (
    history_id     BIGSERIAL    NOT NULL,
    application_id VARCHAR(20)  NOT NULL,
    old_status     VARCHAR(20),
    new_status     VARCHAR(20)  NOT NULL,
    changed_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    changed_by     VARCHAR(100) NOT NULL,
    change_reason  VARCHAR(255),
    CONSTRAINT pk_app_history PRIMARY KEY (history_id),
    CONSTRAINT fk_hist_application FOREIGN KEY (application_id)
        REFERENCES orders_domain.product_application(application_id)
);

CREATE INDEX idx_app_history_app
    ON orders_domain.application_status_history (application_id, changed_at DESC);

CREATE OR REPLACE FUNCTION orders_domain.prevent_history_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'application_status_history is immutable. Rows cannot be %d. application_id: %',
        TG_OP, OLD.application_id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_app_history_immutable
    BEFORE UPDATE OR DELETE ON orders_domain.application_status_history
    FOR EACH ROW EXECUTE FUNCTION orders_domain.prevent_history_modification();

CREATE TABLE orders_domain.murabaha_contract (
    contract_id        CHAR(15)      NOT NULL,
    application_id     VARCHAR(20),
    customer_id        CHAR(10)      NOT NULL,
    account_id         CHAR(16)      NOT NULL,
    asset_cost_sar     NUMERIC(18,2) NOT NULL,     -- PDPL: Restricted
    profit_amount_sar  NUMERIC(18,2) NOT NULL,     -- PDPL: Restricted
    total_sale_price   NUMERIC(18,2) NOT NULL,     -- PDPL: Restricted
    ssb_approval_ref   VARCHAR(50)   NOT NULL,
    disbursement_date  DATE          NOT NULL,
    maturity_date      DATE          NOT NULL,
    tenure_months      SMALLINT      NOT NULL,
    status             VARCHAR(15)   NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','SETTLED','DEFAULTED','SETTLED_EARLY')),
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_murabaha PRIMARY KEY (contract_id),
    CONSTRAINT fk_mrb_customer FOREIGN KEY (customer_id) REFERENCES retail.customer(customer_id),
    CONSTRAINT fk_mrb_account  FOREIGN KEY (account_id)  REFERENCES retail.account(account_id),
    -- Islamic finance: profit fixed and disclosed at inception — cannot drift
    CONSTRAINT chk_mrb_total CHECK (total_sale_price = asset_cost_sar + profit_amount_sar)
);

CREATE TABLE orders_domain.murabaha_schedule (
    schedule_id        SERIAL        NOT NULL,
    contract_id        CHAR(15)      NOT NULL,
    instalment_no      INTEGER       NOT NULL,
    due_date           DATE          NOT NULL,
    instalment_sar     NUMERIC(18,2) NOT NULL,
    principal_portion  NUMERIC(18,2) NOT NULL,
    profit_portion     NUMERIC(18,2) NOT NULL,
    paid_amount        NUMERIC(18,2),
    paid_date          DATE,
    status             VARCHAR(15)   NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','PAID','OVERDUE','SETTLED_EARLY')),
    CONSTRAINT pk_schedule PRIMARY KEY (schedule_id),
    CONSTRAINT fk_schedule_contract FOREIGN KEY (contract_id)
        REFERENCES orders_domain.murabaha_contract(contract_id),
    CONSTRAINT chk_schedule_sum CHECK (instalment_sar = principal_portion + profit_portion)
);

CREATE INDEX idx_schedule_due ON orders_domain.murabaha_schedule (due_date, status)
    WHERE status IN ('PENDING','OVERDUE');

-- SAMA NPF Reporting View — Non-Performing Finance > 90 days
CREATE OR REPLACE VIEW orders_domain.v_npf_exposure AS
SELECT
    mc.contract_id, mc.customer_id, mc.total_sale_price,
    COUNT(*) FILTER (WHERE ms.status = 'OVERDUE' AND ms.due_date < CURRENT_DATE - INTERVAL '90 days')
        AS instalments_overdue_90d,
    SUM(ms.instalment_sar) FILTER (WHERE ms.status = 'OVERDUE' AND ms.due_date < CURRENT_DATE - INTERVAL '90 days')
        AS overdue_amount_sar_90d
FROM orders_domain.murabaha_contract mc
JOIN orders_domain.murabaha_schedule ms ON mc.contract_id = ms.contract_id
WHERE mc.status = 'ACTIVE'
GROUP BY mc.contract_id, mc.customer_id, mc.total_sale_price
HAVING COUNT(*) FILTER (WHERE ms.status = 'OVERDUE' AND ms.due_date < CURRENT_DATE - INTERVAL '90 days') > 0;
```

---

### Orders — Scenario Trace

<a name="orders--scenario-trace"></a>

**Scenario: Murabaha Home Finance application — submitted → approved → fulfilled.**

```
Step 1: WRITE → orders_domain.product_application
          (status: SUBMITTED, nafath_verified: FALSE, aml_check_status: NULL)
        WRITE → orders_domain.application_status_history
          (old: NULL, new: SUBMITTED, changed_by: MOBILE_APP_v4.1)

Step 2: AML + Nafath + SIMAH
        WRITE → payments.external_api_log  ×3 (OFAC, NAFATH, SIMAH)
        UPDATE → product_application  (aml_check_status: CLEAR, nafath_verified: TRUE, credit_bureau_score: 720)
        WRITE → application_status_history  (SUBMITTED → UNDER_REVIEW)

Step 3: Officer approves
        UPDATE → product_application
          (status: APPROVED, approved_amount_sar: 500000, approved_profit_rate: 3.99, decision_by: OFFICER_A42)
        WRITE → application_status_history  (UNDER_REVIEW → APPROVED)

Step 4: FULFILLED — single atomic transaction across three domains
        BEGIN;
          UPDATE product_application → FULFILLED
          WRITE application_status_history  (APPROVED → FULFILLED)
          WRITE murabaha_contract
            (asset_cost: 500000, profit: 85000, total: 585000 ← CHECK: 500K + 85K = 585K ✓)
          WRITE murabaha_schedule × 240 rows
          WRITE retail.account  (Customer Domain)
          WRITE retail.customer_account
          UPDATE inventory_domain.product_quota  (approved_count +1, approved_amount +500000)
        COMMIT;
        ↑ All commits together or not at all. Quota update cannot succeed without application update.

Immutability test:
        UPDATE orders_domain.application_status_history SET changed_by = 'OFFICER_B99' WHERE history_id = 47;
        → ERROR: application_status_history is immutable. Rows cannot be UPDATEd.
        → The audit trail is permanent. SAMA sees exactly what happened.
```

---

## Domain 5 — Inventory

**Domain purpose:** To enforce limits on how many of each financial product the bank can approve — preventing over-approval that would breach SAMA capital adequacy requirements or exceed risk-approved capacity limits.

**Domain boundary:** Inventory owns the capacity rules. It references Product Domain and is updated by Orders Domain. It does not own products or applications.

---

### Inventory — Entities

| Entity | Purpose |
|--------|---------|
| `PRODUCT_QUOTA` | One row per product per period. Tracks approved limit (max) and consumption (approved_count, approved_amount_sar). Incremented atomically on every FULFILLED. |
| `v_product_availability` | View — not a table. Returns `availability_status: AVAILABLE / QUOTA_FULL / EXPOSURE_FULL / SUSPENDED`. Queried on every product page load. |

> **Why only one table?** Banking inventory is not physical goods. The only thing that needs tracking is: how many of this product can be approved this period, and how many have been? One table. One row per product per period.

---

### Inventory — Conceptual Model

<a name="inventory--conceptual-model"></a>

```
┌─ PRODUCT DOMAIN ───────────────────────────────┐
│   PRODUCT  — defines what can be sold           │
└────────────────┬───────────────────────────────┘
                 │ capacity controlled by
                 ▼
┌─ INVENTORY DOMAIN ──────────────────────────────────────────────┐
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                   PRODUCT_QUOTA                         │   │
│   │  max_applications  ──►  approved_count                  │   │
│   │  max_exposure_sar  ──►  approved_amount_sar             │   │
│   │  SELECT FOR UPDATE prevents concurrent over-approval    │   │
│   └──────────────────────────┬──────────────────────────────┘   │
│                              │ drives                           │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │         v_product_availability  (view)                   │   │
│   │  AVAILABLE / QUOTA_FULL / EXPOSURE_FULL / SUSPENDED     │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Updated by Orders Domain atomically on every FULFILLED         │
│  (not a FK — a transactional consequence inside BEGIN/COMMIT)   │
└─────────────────────────────────────────────────────────────────┘
```

---

### Inventory — Logical Model

<a name="inventory--logical-model"></a>

#### PRODUCT_QUOTA

| Attribute | Type | Decision Rationale |
|-----------|------|--------------------|
| `quota_period` | VARCHAR(10) | CHECK(MONTHLY, QUARTERLY, ANNUAL). QUARTERLY quotas align with SAMA capital reporting periods. Period type drives grouping in reports. |
| `period_start` / `period_end` | DATE | Explicit dates — not computed from quota_period. Hijri quarters do not align with Gregorian quarters. SAMA uses both calendars. Explicit dates are always unambiguous. |
| `max_applications` | INTEGER | NULLABLE — NULL means "no count limit". Zero would mean "no applications allowed" — wrong. |
| `max_exposure_sar` | NUMERIC(18,2) | NULLABLE — same rationale. |
| `approved_count` | INTEGER | NOT NULL, DEFAULT 0. A pre-computed counter — not a COUNT(*) query. At scale, a COUNT across 100K+ applications on every page load is expensive. The counter is incremented atomically inside the FULFILLED transaction. |
| `status` | VARCHAR(10) | CHECK(OPEN, CLOSED, SUSPENDED). SUSPENDED = manually halted by Risk Management during a credit policy review. A system with only OPEN/CLOSED cannot represent a temporary suspension without closing the period entirely. |

**The atomicity requirement — why SELECT FOR UPDATE matters:**

```
Without FOR UPDATE:
  Transaction A: reads approved_count = 199  (one below max)
  Transaction B: reads approved_count = 199  (same read, same moment)
  Transaction A: increments to 200 → commits
  Transaction B: increments to 200 → commits  ← WRONG — 201st approval happened
  Result: SAMA capital limit breached

With FOR UPDATE:
  Transaction A: reads approved_count = 199 FOR UPDATE  → locks row
  Transaction B: reads → WAITS
  Transaction A: checks 199 < 200 → increments to 200 → commits
  Transaction B: lock released → reads 200 → 200 >= 200 → QUOTA_FULL → blocked
  Result: Exactly 200 approvals. No breach.
```

---

### Inventory — Physical DDL

<a name="inventory--physical-ddl"></a>

```sql
CREATE SCHEMA inventory_domain;

CREATE TABLE inventory_domain.product_quota (
    quota_id             SERIAL        NOT NULL,
    product_id           VARCHAR(15)   NOT NULL,
    quota_period         VARCHAR(10)   NOT NULL CHECK (quota_period IN ('MONTHLY','QUARTERLY','ANNUAL')),
    period_start         DATE          NOT NULL,
    period_end           DATE          NOT NULL,
    max_applications     INTEGER,                   -- NULL = unlimited
    max_exposure_sar     NUMERIC(18,2),             -- NULL = unlimited
    approved_count       INTEGER       NOT NULL DEFAULT 0,
    approved_amount_sar  NUMERIC(18,2) NOT NULL DEFAULT 0,
    status               VARCHAR(10)   NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN','CLOSED','SUSPENDED')),
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_quota PRIMARY KEY (quota_id),
    CONSTRAINT fk_quota_product FOREIGN KEY (product_id)
        REFERENCES product_domain.product(product_id),
    CONSTRAINT chk_quota_dates CHECK (period_end > period_start),
    CONSTRAINT chk_quota_non_negative CHECK (approved_count >= 0 AND approved_amount_sar >= 0)
);

CREATE INDEX idx_quota_product_period
    ON inventory_domain.product_quota (product_id, period_start, period_end)
    WHERE status = 'OPEN';

-- Availability view — queried on every product page load
CREATE OR REPLACE VIEW inventory_domain.v_product_availability AS
SELECT
    p.product_id, p.product_name_en, p.product_code, p.is_sharia_compliant,
    pq.quota_id, pq.quota_period, pq.period_start, pq.period_end,
    pq.max_applications, pq.approved_count,
    CASE WHEN pq.max_applications IS NULL THEN NULL
         ELSE pq.max_applications - pq.approved_count END AS remaining_applications,
    pq.max_exposure_sar, pq.approved_amount_sar,
    CASE WHEN pq.max_exposure_sar IS NULL THEN NULL
         ELSE pq.max_exposure_sar - pq.approved_amount_sar END AS remaining_exposure_sar,
    CASE
        WHEN p.is_active = FALSE                            THEN 'UNAVAILABLE'
        WHEN pq.status   = 'SUSPENDED'                     THEN 'SUSPENDED'
        WHEN pq.max_applications IS NOT NULL
         AND pq.approved_count >= pq.max_applications      THEN 'QUOTA_FULL'
        WHEN pq.max_exposure_sar IS NOT NULL
         AND pq.approved_amount_sar >= pq.max_exposure_sar THEN 'EXPOSURE_FULL'
        ELSE 'AVAILABLE'
    END AS availability_status
FROM product_domain.product p
LEFT JOIN inventory_domain.product_quota pq
    ON p.product_id   = pq.product_id
    AND pq.period_start <= CURRENT_DATE
    AND pq.period_end   >= CURRENT_DATE
    AND pq.status        = 'OPEN'
WHERE p.is_active = TRUE;

-- Atomic quota update pattern (used inside Orders Domain FULFILLED transaction)
-- Step 1: Lock the row
-- SELECT quota_id, approved_count, max_applications, approved_amount_sar, max_exposure_sar
-- FROM   inventory_domain.product_quota
-- WHERE  product_id = 'PROD_MRB_002' AND status = 'OPEN'
-- AND    CURRENT_DATE BETWEEN period_start AND period_end
-- FOR UPDATE;
--
-- Step 2: Application checks result — if within limits:
-- UPDATE inventory_domain.product_quota
-- SET    approved_count      = approved_count + 1,
--        approved_amount_sar = approved_amount_sar + :approved_amount
-- WHERE  quota_id = :quota_id;
-- (committed together with the FULFILLED application update)

INSERT INTO inventory_domain.product_quota
    (product_id, quota_period, period_start, period_end, max_applications, max_exposure_sar, status)
VALUES
    ('PROD_MRB_001','QUARTERLY','2025-01-01','2025-03-31', 500,  50000000, 'OPEN'),
    ('PROD_MRB_002','QUARTERLY','2025-01-01','2025-03-31', 200, 200000000, 'OPEN'),
    ('PROD_TAW_001','ANNUAL',   '2025-01-01','2025-12-31', NULL,      NULL,'OPEN');
```

---

### Inventory — Scenario Trace

<a name="inventory--scenario-trace"></a>

**Scenario: The 200th Murabaha Home Finance approval (last slot) and the 201st attempt.**

```
Case A — Application 200 (last available slot):
  READ  → v_product_availability
    → approved_count = 199, max = 200, remaining = 1, status = AVAILABLE ✓
  On FULFILLED (inside BEGIN/COMMIT):
    SELECT … FOR UPDATE  → row locked
    Check: 199 < 200  → proceed
    UPDATE approved_count = 200, approved_amount_sar += 500000
  COMMIT → Quota = full

Case B — Application 201:
  READ  → v_product_availability
    → approved_count = 200, max = 200, remaining = 0, status = QUOTA_FULL
  → Product page hidden from customer. Application never created.

Race condition — two simultaneous applications at count 199:
  Transaction A: SELECT … FOR UPDATE → locks row
  Transaction B: SELECT … FOR UPDATE → WAITS
  Transaction A: 199 < 200 → increments to 200 → COMMITS
  Transaction B: lock released → reads 200 → 200 >= 200 → QUOTA_FULL → blocked
  → Exactly 200 approvals. No breach. No race condition.

Suspend mid-quarter (risk policy hold):
  UPDATE product_quota SET status = 'SUSPENDED' WHERE product_id = 'PROD_MRB_002';
  → v_product_availability immediately returns availability_status = 'SUSPENDED'
  → Product hidden. No new applications possible.
  → Existing UNDER_REVIEW applications unaffected.
  → When hold lifted: UPDATE status = 'OPEN' → resumes with counts intact.
```

---

*Al-Noor Bank Case Study | SNB Data Management Capability Programme*