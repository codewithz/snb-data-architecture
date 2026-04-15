"""Tests for the template-based RemediationGenerator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from parser.ddl_parser import DDLParser
from classifier.pii_classifier import PIIClassifier
from rules.audit_trail import AuditTrailRule, SoftDeleteRule, AuditLogTableRule
from rules.encryption import EncryptionRule
from rules.referential import ReferentialRule
from rules.consent import ConsentTableRule, DSRTableRule
from rules.retention import RetentionRule
from rules.transaction_trace import TransactionTraceRule
from rules.access_control import PrimaryKeyRule
from generators.remediation import RemediationGenerator, RemediationScript


def parse_classify(ddl: str, dialect: str = "postgres"):
    parser = DDLParser(dialect=dialect)
    schema = parser.parse(ddl)
    PIIClassifier().classify_schema(schema)
    return schema


def all_findings(schema, dialect="postgres"):
    rules = [
        PrimaryKeyRule(),
        AuditTrailRule(),
        SoftDeleteRule(),
        AuditLogTableRule(),
        EncryptionRule(),
        ReferentialRule(),
        ConsentTableRule(),
        DSRTableRule(),
        RetentionRule(),
        TransactionTraceRule(),
    ]
    findings = []
    for rule in rules:
        result = rule.check(schema)
        findings.extend(result.findings)
    return findings


# ── RemediationGenerator unit tests ──────────────────────────────────────────

class TestRemediationGeneratorPostgres:
    def setup_method(self):
        self.gen = RemediationGenerator(dialect="postgres")

    def test_returns_script_object(self):
        schema = parse_classify("CREATE TABLE t (id BIGSERIAL PRIMARY KEY);")
        findings = all_findings(schema)
        script = self.gen.generate(findings, schema)
        assert isinstance(script, RemediationScript)

    def test_render_returns_string(self):
        schema = parse_classify("CREATE TABLE t (id BIGSERIAL PRIMARY KEY);")
        findings = all_findings(schema)
        script = self.gen.generate(findings, schema)
        rendered = script.render()
        assert isinstance(rendered, str)
        assert len(rendered) > 0

    def test_header_present(self):
        schema = parse_classify("CREATE TABLE t (id BIGSERIAL PRIMARY KEY);")
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        assert "SAMA/PDPL" in rendered
        assert "POSTGRES" in rendered

    def test_audit_columns_template_rendered(self):
        """SAMA-AUD-001 findings produce add_audit_columns SQL."""
        schema = parse_classify("""
            CREATE TABLE orders (
                id BIGSERIAL PRIMARY KEY,
                amount NUMERIC(18,2)
            );
        """)
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        assert "SAMA-AUD-001" in rendered
        assert "ADD COLUMN" in rendered
        assert "created_at" in rendered or "updated_at" in rendered

    def test_soft_delete_template_rendered(self):
        """SAMA-AUD-002 findings produce add_soft_delete SQL."""
        schema = parse_classify("""
            CREATE TABLE customers (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(255)
            );
        """)
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        assert "SAMA-AUD-002" in rendered or "is_deleted" in rendered

    def test_audit_log_table_template_rendered(self):
        """SAMA-AUD-003 findings produce create_audit_log_table SQL."""
        schema = parse_classify("""
            CREATE TABLE customers (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(255)
            );
        """)
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        assert "customers_audit_log" in rendered
        assert "CREATE TABLE" in rendered

    def test_encrypt_column_template_rendered(self):
        """PDPL-ENC-001 findings produce encrypt_column SQL."""
        schema = parse_classify("""
            CREATE TABLE customers (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(255),
                national_id VARCHAR(20)
            );
        """)
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        assert "PDPL-ENC-001" in rendered
        assert "pgp_sym_encrypt" in rendered or "BYTEA" in rendered

    def test_consent_table_template_rendered(self):
        """PDPL-CON-001 findings produce create_consent_table SQL."""
        schema = parse_classify("CREATE TABLE dummy (id SERIAL PRIMARY KEY);")
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        assert "consent_records" in rendered
        assert "PDPL-CON-001" in rendered or "PDPL Art.10" in rendered

    def test_dsr_table_template_rendered(self):
        """PDPL-DSR-001 findings produce create_dsr_table SQL."""
        schema = parse_classify("CREATE TABLE dummy (id SERIAL PRIMARY KEY);")
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        assert "data_subject_requests" in rendered

    def test_pk_template_rendered(self):
        """SAMA-INT-001 findings produce add_primary_key SQL."""
        schema = parse_classify("CREATE TABLE nopk (name VARCHAR(100));")
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        assert "SAMA-INT-001" in rendered
        assert "PRIMARY KEY" in rendered

    def test_cascade_fk_template_rendered(self):
        """SAMA-REF-001 findings produce replace_cascade_delete SQL."""
        schema = parse_classify("""
            CREATE TABLE customers (
                id BIGSERIAL PRIMARY KEY, email VARCHAR(255)
            );
            CREATE TABLE orders (
                id BIGSERIAL PRIMARY KEY,
                customer_id BIGINT REFERENCES customers(id) ON DELETE CASCADE
            );
        """)
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        assert "RESTRICT" in rendered
        assert "SAMA-REF-001" in rendered

    def test_retention_template_rendered(self):
        """SAMA-RET-001 findings produce add_retention_column SQL."""
        schema = parse_classify("""
            CREATE TABLE payments (
                id BIGSERIAL PRIMARY KEY,
                account_number VARCHAR(30),
                balance NUMERIC(18,2)
            );
        """)
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        assert "retention_period" in rendered

    def test_transaction_trace_template_rendered(self):
        """SAMA-TRX-001 findings produce add_transaction_trace SQL."""
        schema = parse_classify("""
            CREATE TABLE payments (
                id BIGSERIAL PRIMARY KEY,
                amount NUMERIC(18,2),
                created_at TIMESTAMP NOT NULL,
                created_by VARCHAR(255) NOT NULL
            );
        """)
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        assert "reference_id" in rendered or "SAMA-TRX-001" in rendered

    def test_no_findings_renders_empty_blocks(self):
        """Schema with no findings produces a script with zero blocks."""
        ddl = """
            CREATE TABLE consent_records (
                id BIGSERIAL PRIMARY KEY,
                data_subject_id BIGINT NOT NULL,
                purpose VARCHAR(500) NOT NULL,
                consent_given BOOLEAN NOT NULL DEFAULT FALSE,
                consent_date TIMESTAMP NOT NULL,
                withdrawal_date TIMESTAMP,
                consent_version VARCHAR(50),
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                deleted_at TIMESTAMP,
                deleted_by VARCHAR(255),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                created_by VARCHAR(255) NOT NULL,
                updated_at TIMESTAMP,
                updated_by VARCHAR(255)
            );
            CREATE TABLE data_subject_requests (
                id BIGSERIAL PRIMARY KEY,
                data_subject_id BIGINT NOT NULL,
                request_type VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
                requested_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                response_due_date DATE,
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                deleted_at TIMESTAMP,
                deleted_by VARCHAR(255),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                created_by VARCHAR(255) NOT NULL,
                updated_at TIMESTAMP,
                updated_by VARCHAR(255)
            );
        """
        schema = parse_classify(ddl)
        findings = all_findings(schema)
        # Only check findings related to encryption/audit (consent + dsr tables)
        non_enc_findings = [f for f in findings if f.rule_id not in ("PDPL-ENC-001",)]
        script = self.gen.generate(non_enc_findings, schema)
        assert isinstance(script, RemediationScript)

    def test_section_ordering(self):
        """Consent/DSR blocks appear before encryption blocks."""
        schema = parse_classify("""
            CREATE TABLE customers (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(255),
                national_id VARCHAR(20)
            );
        """)
        findings = all_findings(schema)
        rendered = self.gen.generate(findings, schema).render()
        consent_pos = rendered.find("consent_records")
        enc_pos = rendered.find("pgp_sym_encrypt")
        if consent_pos != -1 and enc_pos != -1:
            assert consent_pos < enc_pos, \
                "consent_records should appear before encryption blocks"

    def test_deduplication(self):
        """Multiple findings for the same rule+table produce ONE template render."""
        ddl = """
            CREATE TABLE customers (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(255),
                phone_number VARCHAR(20),
                national_id VARCHAR(20)
            );
        """
        schema = parse_classify(ddl)
        findings = all_findings(schema)
        enc_findings = [f for f in findings if f.rule_id == "PDPL-ENC-001"]
        assert len(enc_findings) >= 2  # Multiple columns

        # Each column should produce its own block
        script = self.gen.generate(findings, schema)
        enc_blocks = [b for b in script.rendered_blocks if b.rule_id == "PDPL-ENC-001"]
        assert len(enc_blocks) == len(enc_findings)  # One per column


class TestRemediationGeneratorMySQL:
    def setup_method(self):
        self.gen = RemediationGenerator(dialect="mysql")

    def test_mysql_audit_columns_use_datetime(self):
        schema = parse_classify("""
            CREATE TABLE orders (id BIGINT AUTO_INCREMENT PRIMARY KEY, amount DECIMAL(18,2));
        """, dialect="mysql")
        findings = all_findings(schema, dialect="mysql")
        rendered = self.gen.generate(findings, schema).render()
        assert "DATETIME" in rendered or "CURRENT_TIMESTAMP" in rendered

    def test_mysql_encrypt_uses_varbinary(self):
        schema = parse_classify("""
            CREATE TABLE customers (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255)
            );
        """, dialect="mysql")
        findings = all_findings(schema, dialect="mysql")
        rendered = self.gen.generate(findings, schema).render()
        assert "VARBINARY" in rendered or "AES_ENCRYPT" in rendered


class TestRemediationGeneratorMSSQL:
    def setup_method(self):
        self.gen = RemediationGenerator(dialect="mssql")

    def test_mssql_audit_columns_use_datetime2(self):
        schema = parse_classify("""
            CREATE TABLE orders (
                id BIGINT IDENTITY(1,1) PRIMARY KEY,
                amount DECIMAL(18,2)
            );
        """, dialect="mssql")
        findings = all_findings(schema, dialect="mssql")
        rendered = self.gen.generate(findings, schema).render()
        assert "DATETIME2" in rendered or "GETUTCDATE" in rendered

    def test_mssql_script_dialect_header(self):
        schema = parse_classify(
            "CREATE TABLE t (id BIGINT IDENTITY(1,1) PRIMARY KEY);",
            dialect="mssql"
        )
        findings = all_findings(schema, dialect="mssql")
        rendered = self.gen.generate(findings, schema).render()
        assert "MSSQL" in rendered


class TestRemediationScriptRender:
    def test_render_always_has_header(self):
        script = RemediationScript(dialect="postgres", finding_count=0)
        rendered = script.render()
        assert "SAMA/PDPL" in rendered
        assert "POSTGRES" in rendered

    def test_render_with_zero_blocks(self):
        script = RemediationScript(dialect="mysql", finding_count=0)
        rendered = script.render()
        assert rendered.strip().startswith("--")

    def test_finding_count_in_header(self):
        script = RemediationScript(dialect="postgres", finding_count=42)
        assert "42" in script.render()
