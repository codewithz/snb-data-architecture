    CREATE TABLE IF NOT EXISTS dim_customer (
    dim_customer_sk   NUMBER AUTOINCREMENT,
    customer_id       VARCHAR(10)  NOT NULL,   -- Natural key from CBS
    full_name_en      VARCHAR(200),
    customer_segment  VARCHAR(30),             -- RETAIL, PREMIUM, PRIVATE, CORPORATE
    risk_rating       CHAR(1),                 -- A, B, C, D (SAMA capital adequacy)
    kyc_status        VARCHAR(20),             -- VERIFIED, PENDING, EXPIRED
    nationality       CHAR(3),                 -- ISO 3166-1 alpha-3 (SAU, EGY, IND, etc.)
    branch_id         VARCHAR(10),
    branch_name       VARCHAR(100),
    region            VARCHAR(50),

    -- SCD Type 2 tracking columns
    effective_from    DATE         NOT NULL,
    effective_to      DATE,                    -- NULL means this is the current active record
    is_current        BOOLEAN      NOT NULL DEFAULT TRUE,

    -- Clustering: most common query pattern is "find current record for customer X"
    CONSTRAINT pk_dim_customer PRIMARY KEY (dim_customer_sk)
) CLUSTER BY (customer_id, is_current);
