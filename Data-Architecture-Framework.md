# Data Architect's Framework: Business Requirement to Database Implementation
### A Practical Playbook for Banking & Financial Services

> *"A requirement without a model is just a wish. A model without a requirement is just art."*
> — Every battle-scarred Data Architect, ever.

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