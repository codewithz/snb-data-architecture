"""Tests for compliance rules."""

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
from rules.base_rule import Severity


def parse_and_classify(ddl: str, dialect: str = "postgres"):
    parser = DDLParser(dialect=dialect)
    schema = parser.parse(ddl)
    PIIClassifier().classify_schema(schema)
    return schema


class TestAuditTrailRule:
    def test_missing_audit_cols_fails(self):
        schema = parse_and_classify("""
            CREATE TABLE orders (
                id BIGSERIAL PRIMARY KEY,
                amount NUMERIC(18,2)
            );
        """)
        result = AuditTrailRule().check(schema)
        assert not result.passed
        missing = {f.column for f in result.findings if f.column}
        assert "created_at" in missing

    def test_all_audit_cols_present_passes(self):
        schema = parse_and_classify("""
            CREATE TABLE orders (
                id BIGSERIAL PRIMARY KEY,
                amount NUMERIC(18,2),
                created_at TIMESTAMP NOT NULL,
                created_by VARCHAR(255) NOT NULL,
                updated_at TIMESTAMP,
                updated_by VARCHAR(255)
            );
        """)
        result = AuditTrailRule().check(schema)
        assert result.passed

    def test_audit_log_table_exempt(self):
        schema = parse_and_classify("""
            CREATE TABLE orders_audit_log (
                id BIGSERIAL PRIMARY KEY,
                record_id BIGINT
            );
        """)
        result = AuditTrailRule().check(schema)
        assert result.passed


class TestSoftDeleteRule:
    def test_sensitive_table_without_soft_delete_fails(self):
        schema = parse_and_classify("""
            CREATE TABLE users (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(255),
                created_at TIMESTAMP NOT NULL,
                created_by VARCHAR(255) NOT NULL,
                updated_at TIMESTAMP,
                updated_by VARCHAR(255)
            );
        """)
        result = SoftDeleteRule().check(schema)
        assert not result.passed
        missing = {f.message for f in result.findings}
        assert any("is_deleted" in m for m in missing)

    def test_non_sensitive_table_passes(self):
        schema = parse_and_classify("""
            CREATE TABLE country_codes (
                id SERIAL PRIMARY KEY,
                code CHAR(2),
                name VARCHAR(100)
            );
        """)
        result = SoftDeleteRule().check(schema)
        assert result.passed

    def test_soft_delete_present_passes(self):
        schema = parse_and_classify("""
            CREATE TABLE users (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(255),
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                deleted_at TIMESTAMP,
                deleted_by VARCHAR(255),
                created_at TIMESTAMP NOT NULL,
                created_by VARCHAR(255) NOT NULL,
                updated_at TIMESTAMP,
                updated_by VARCHAR(255)
            );
        """)
        result = SoftDeleteRule().check(schema)
        assert result.passed


class TestEncryptionRule:
    def test_tier1_varchar_fails(self):
        schema = parse_and_classify("""
            CREATE TABLE customers (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(255),
                national_id VARCHAR(20)
            );
        """)
        result = EncryptionRule().check(schema)
        assert not result.passed
        cols = {f.column for f in result.findings}
        assert "email" in cols
        assert "national_id" in cols

    def test_tier1_bytea_passes(self):
        schema = parse_and_classify("""
            CREATE TABLE customers (
                id BIGSERIAL PRIMARY KEY,
                email BYTEA,
                national_id BYTEA
            );
        """)
        result = EncryptionRule().check(schema)
        assert result.passed

    def test_tier4_not_encrypted_fails(self):
        schema = parse_and_classify("""
            CREATE TABLE health (
                id BIGSERIAL PRIMARY KEY,
                diagnosis TEXT,
                religion VARCHAR(100)
            );
        """)
        result = EncryptionRule().check(schema)
        assert not result.passed

    def test_tier2_not_checked_for_encryption(self):
        schema = parse_and_classify("""
            CREATE TABLE sessions (
                id BIGSERIAL PRIMARY KEY,
                ip_address VARCHAR(45),
                session_id VARCHAR(100)
            );
        """)
        result = EncryptionRule().check(schema)
        assert result.passed  # Tier 2 not in scope for PDPL-ENC-001


class TestReferentialRule:
    def test_cascade_on_sensitive_table_fails(self):
        schema = parse_and_classify("""
            CREATE TABLE customers (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(255)
            );
            CREATE TABLE orders (
                id BIGSERIAL PRIMARY KEY,
                customer_id BIGINT REFERENCES customers(id) ON DELETE CASCADE
            );
        """)
        result = ReferentialRule().check(schema)
        assert not result.passed
        assert any("CASCADE" in f.message for f in result.findings)

    def test_restrict_on_sensitive_table_passes(self):
        schema = parse_and_classify("""
            CREATE TABLE customers (
                id BIGSERIAL PRIMARY KEY,
                email VARCHAR(255)
            );
            CREATE TABLE orders (
                id BIGSERIAL PRIMARY KEY,
                customer_id BIGINT REFERENCES customers(id) ON DELETE RESTRICT
            );
        """)
        result = ReferentialRule().check(schema)
        assert result.passed


class TestConsentRules:
    def test_missing_consent_table_fails(self):
        schema = parse_and_classify("CREATE TABLE products (id SERIAL PRIMARY KEY);")
        result = ConsentTableRule().check(schema)
        assert not result.passed
        assert result.findings[0].severity == Severity.CRITICAL

    def test_consent_table_present_passes(self):
        schema = parse_and_classify("""
            CREATE TABLE consent_records (
                id BIGSERIAL PRIMARY KEY,
                data_subject_id BIGINT NOT NULL,
                purpose VARCHAR(500) NOT NULL,
                consent_given BOOLEAN NOT NULL,
                consent_date TIMESTAMP NOT NULL,
                withdrawal_date TIMESTAMP,
                consent_version VARCHAR(50)
            );
        """)
        result = ConsentTableRule().check(schema)
        assert result.passed

    def test_missing_dsr_table_fails(self):
        schema = parse_and_classify("CREATE TABLE products (id SERIAL PRIMARY KEY);")
        result = DSRTableRule().check(schema)
        assert not result.passed


class TestRetentionRule:
    def test_financial_table_missing_retention_fails(self):
        schema = parse_and_classify("""
            CREATE TABLE transactions (
                id BIGSERIAL PRIMARY KEY,
                account_number VARCHAR(30),
                balance NUMERIC(18,2)
            );
        """)
        result = RetentionRule().check(schema)
        assert not result.passed

    def test_financial_table_with_retention_passes(self):
        schema = parse_and_classify("""
            CREATE TABLE transactions (
                id BIGSERIAL PRIMARY KEY,
                account_number VARCHAR(30),
                balance NUMERIC(18,2),
                retention_period SMALLINT,
                data_category VARCHAR(100)
            );
        """)
        result = RetentionRule().check(schema)
        assert result.passed


class TestTransactionTraceRule:
    def test_payment_without_reference_id_fails(self):
        schema = parse_and_classify("""
            CREATE TABLE payments (
                id BIGSERIAL PRIMARY KEY,
                amount NUMERIC(18,2),
                payment_date TIMESTAMP,
                created_at TIMESTAMP,
                created_by VARCHAR(255)
            );
        """)
        result = TransactionTraceRule().check(schema)
        assert not result.passed
        assert any("trace ID" in f.message for f in result.findings)

    def test_payment_with_reference_id_passes(self):
        schema = parse_and_classify("""
            CREATE TABLE payments (
                id BIGSERIAL PRIMARY KEY,
                reference_id VARCHAR(100) UNIQUE NOT NULL,
                amount NUMERIC(18,2),
                status VARCHAR(50) NOT NULL,
                payment_date TIMESTAMP
            );
        """)
        result = TransactionTraceRule().check(schema)
        assert result.passed

    def test_non_transaction_table_ignored(self):
        schema = parse_and_classify("""
            CREATE TABLE products (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(255)
            );
        """)
        result = TransactionTraceRule().check(schema)
        assert result.passed


class TestPrimaryKeyRule:
    def test_table_without_pk_fails(self):
        schema = parse_and_classify("""
            CREATE TABLE nopk (name VARCHAR(100), value TEXT);
        """)
        result = PrimaryKeyRule().check(schema)
        assert not result.passed
        assert result.findings[0].severity == Severity.HIGH

    def test_table_with_pk_passes(self):
        schema = parse_and_classify("""
            CREATE TABLE with_pk (id BIGSERIAL PRIMARY KEY, name VARCHAR(100));
        """)
        result = PrimaryKeyRule().check(schema)
        assert result.passed
