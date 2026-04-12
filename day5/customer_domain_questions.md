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