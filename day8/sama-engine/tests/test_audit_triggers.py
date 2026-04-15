"""Tests for the AuditTriggerGenerator — Phase 3."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from parser.ddl_parser import DDLParser
from classifier.pii_classifier import PIIClassifier
from generators.audit_triggers import AuditTriggerGenerator, AuditOutput


def parse_and_classify(ddl: str, dialect: str = "postgres"):
    schema = DDLParser(dialect=dialect).parse(ddl)
    PIIClassifier().classify_schema(schema)
    return schema


SENSITIVE_PG = """
CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255),
    national_id VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL
);
CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    account_number VARCHAR(30),
    balance NUMERIC(18,2),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL
);
"""

NON_SENSITIVE_PG = """
CREATE TABLE country_codes (
    id SERIAL PRIMARY KEY,
    code CHAR(2),
    name VARCHAR(100)
);
"""


# ── AuditOutput ──────────────────────────────────────────────────────────────

class TestAuditOutput:
    def test_write_to_dir_creates_four_files(self):
        output = AuditOutput(
            dialect="postgres",
            audit_tables_sql="-- tables\n",
            audit_triggers_sql="-- triggers\n",
            setup_session_sql="-- session\n",
            trace_transaction_sql="-- trace\n",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            written = output.write_to_dir(tmpdir)
            assert len(written) == 4
            for name in ("audit_tables.sql", "audit_triggers.sql",
                         "setup_session.sql", "trace_transaction.sql"):
                assert (Path(tmpdir) / name).exists()

    def test_write_creates_output_dir_if_missing(self):
        output = AuditOutput(dialect="postgres", audit_tables_sql="-- x\n")
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "deep" / "nested"
            output.write_to_dir(new_dir)
            assert new_dir.exists()


# ── PostgreSQL generator ──────────────────────────────────────────────────────

class TestAuditTriggerGeneratorPostgres:
    def setup_method(self):
        self.gen = AuditTriggerGenerator(dialect="postgres")

    def test_generate_returns_audit_output(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert isinstance(result, AuditOutput)

    def test_only_sensitive_tables_audited(self):
        ddl = SENSITIVE_PG + NON_SENSITIVE_PG
        schema = parse_and_classify(ddl)
        result = self.gen.generate(schema)
        assert "customers" in result.audited_tables
        assert "transactions" in result.audited_tables
        assert "country_codes" not in result.audited_tables

    def test_audit_tables_sql_has_create_table(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert "CREATE TABLE" in result.audit_tables_sql
        assert "customers_audit_log" in result.audit_tables_sql

    def test_audit_tables_sql_has_indexes(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert "CREATE INDEX" in result.audit_tables_sql
        assert "correlation_id" in result.audit_tables_sql

    def test_audit_triggers_sql_has_trigger_function(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert "fn_customers_audit" in result.audit_triggers_sql
        assert "RETURNS TRIGGER" in result.audit_triggers_sql

    def test_audit_triggers_sql_has_all_operations(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        for op in ("INSERT", "UPDATE", "DELETE"):
            assert op in result.audit_triggers_sql

    def test_audit_triggers_uses_row_to_json(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert "row_to_json" in result.audit_triggers_sql

    def test_audit_triggers_includes_correlation_id(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert "correlation_id" in result.audit_triggers_sql

    def test_audit_triggers_includes_application_id(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert "application_id" in result.audit_triggers_sql

    def test_audit_trigger_create_trigger_statement(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert "CREATE TRIGGER" in result.audit_triggers_sql
        assert "customers_audit_trigger" in result.audit_triggers_sql

    def test_setup_session_sql_has_set_config(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert "app.current_user" in result.setup_session_sql \
            or "set_audit_context" in result.setup_session_sql

    def test_setup_session_sql_lists_audited_tables(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert "customers" in result.setup_session_sql

    def test_trace_view_has_union_all(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert "UNION ALL" in result.trace_transaction_sql

    def test_trace_view_covers_all_audited_tables(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        for table in result.audited_tables:
            assert f"{table}_audit_log" in result.trace_transaction_sql

    def test_trace_view_name(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert "v_audit_trace" in result.trace_transaction_sql

    def test_all_outputs_have_header(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        for attr in ("audit_tables_sql", "audit_triggers_sql",
                     "setup_session_sql", "trace_transaction_sql"):
            sql = getattr(result, attr)
            assert "SAMA" in sql or "Audit" in sql, \
                f"{attr} missing header content"

    def test_no_sensitive_tables_returns_empty_audited(self):
        schema = parse_and_classify(NON_SENSITIVE_PG)
        result = self.gen.generate(schema)
        assert result.audited_tables == []

    def test_write_to_dir_round_trip(self):
        schema = parse_and_classify(SENSITIVE_PG)
        result = self.gen.generate(schema)
        with tempfile.TemporaryDirectory() as tmpdir:
            written = result.write_to_dir(tmpdir)
            for name, path in written.items():
                content = path.read_text(encoding="utf-8")
                assert len(content) > 0, f"{name} should not be empty"

    def test_pk_col_correctly_inferred(self):
        """Trigger should reference the actual PK column, not always 'id'."""
        schema = parse_and_classify("""
            CREATE TABLE orders (
                order_uuid VARCHAR(36) PRIMARY KEY,
                email VARCHAR(255),
                total NUMERIC(18,2)
            );
        """)
        result = self.gen.generate(schema)
        assert "order_uuid" in result.audit_triggers_sql


# ── MySQL generator ────────────────────────────────────────────────────────────

class TestAuditTriggerGeneratorMySQL:
    def setup_method(self):
        self.gen = AuditTriggerGenerator(dialect="mysql")

    def test_mysql_uses_three_triggers_per_table(self):
        """MySQL requires separate INSERT / UPDATE / DELETE triggers."""
        schema = parse_and_classify("""
            CREATE TABLE users (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255)
            );
        """, dialect="mysql")
        result = self.gen.generate(schema)
        trigger_sql = result.audit_triggers_sql
        assert "users_audit_insert" in trigger_sql
        assert "users_audit_update" in trigger_sql
        assert "users_audit_delete" in trigger_sql

    def test_mysql_uses_json_object(self):
        schema = parse_and_classify("""
            CREATE TABLE users (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255)
            );
        """, dialect="mysql")
        result = self.gen.generate(schema)
        assert "JSON_OBJECT" in result.audit_triggers_sql

    def test_mysql_uses_session_variables(self):
        schema = parse_and_classify("""
            CREATE TABLE users (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255)
            );
        """, dialect="mysql")
        result = self.gen.generate(schema)
        assert "@app_current_user" in result.audit_triggers_sql \
            or "@app_correlation_id" in result.audit_triggers_sql

    def test_mysql_audit_table_uses_datetime(self):
        schema = parse_and_classify("""
            CREATE TABLE users (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255)
            );
        """, dialect="mysql")
        result = self.gen.generate(schema)
        assert "DATETIME" in result.audit_tables_sql \
            or "AUTO_INCREMENT" in result.audit_tables_sql

    def test_mysql_setup_session_has_procedure(self):
        schema = parse_and_classify("""
            CREATE TABLE users (
                id BIGINT AUTO_INCREMENT PRIMARY KEY, email VARCHAR(255)
            );
        """, dialect="mysql")
        result = self.gen.generate(schema)
        assert "set_audit_context" in result.setup_session_sql \
            or "@app_" in result.setup_session_sql


# ── MSSQL generator ────────────────────────────────────────────────────────────

class TestAuditTriggerGeneratorMSSQL:
    def setup_method(self):
        self.gen = AuditTriggerGenerator(dialect="mssql")

    def test_mssql_uses_for_json(self):
        schema = parse_and_classify("""
            CREATE TABLE customers (
                id BIGINT IDENTITY(1,1) PRIMARY KEY,
                email NVARCHAR(255)
            );
        """, dialect="mssql")
        result = self.gen.generate(schema)
        assert "FOR JSON" in result.audit_triggers_sql

    def test_mssql_uses_inserted_deleted_tables(self):
        schema = parse_and_classify("""
            CREATE TABLE customers (
                id BIGINT IDENTITY(1,1) PRIMARY KEY,
                email NVARCHAR(255)
            );
        """, dialect="mssql")
        result = self.gen.generate(schema)
        assert "inserted" in result.audit_triggers_sql.lower()
        assert "deleted"  in result.audit_triggers_sql.lower()

    def test_mssql_uses_session_context(self):
        schema = parse_and_classify("""
            CREATE TABLE customers (
                id BIGINT IDENTITY(1,1) PRIMARY KEY,
                email NVARCHAR(255)
            );
        """, dialect="mssql")
        result = self.gen.generate(schema)
        assert "SESSION_CONTEXT" in result.audit_triggers_sql \
            or "SESSION_CONTEXT" in result.setup_session_sql

    def test_mssql_audit_table_uses_datetime2(self):
        schema = parse_and_classify("""
            CREATE TABLE customers (
                id BIGINT IDENTITY(1,1) PRIMARY KEY,
                email NVARCHAR(255)
            );
        """, dialect="mssql")
        result = self.gen.generate(schema)
        assert "DATETIME2" in result.audit_tables_sql

    def test_mssql_uses_uniqueidentifier_for_correlation(self):
        schema = parse_and_classify("""
            CREATE TABLE customers (
                id BIGINT IDENTITY(1,1) PRIMARY KEY,
                email NVARCHAR(255)
            );
        """, dialect="mssql")
        result = self.gen.generate(schema)
        assert "UNIQUEIDENTIFIER" in result.audit_tables_sql


# ── Backward compatibility ────────────────────────────────────────────────────

class TestBackwardCompatibility:
    def test_generate_for_schema_returns_string(self):
        gen = AuditTriggerGenerator(dialect="postgres")
        schema = parse_and_classify(SENSITIVE_PG)
        result = gen.generate_for_schema(schema)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_for_table_returns_string(self):
        gen = AuditTriggerGenerator(dialect="postgres")
        schema = parse_and_classify(SENSITIVE_PG)
        table = schema.get_table("customers")
        result = gen.generate_for_table(table)
        assert isinstance(result, str)
        assert "customers" in result
