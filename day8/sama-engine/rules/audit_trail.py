"""SAMA-AUD-001 / SAMA-AUD-002 / SAMA-AUD-003 — Audit trail, soft-delete, and audit log rules."""

from __future__ import annotations

from parser.ddl_parser import SchemaModel, TableModel
from .base_rule import BaseRule, Finding, RuleResult, Severity

# Column type buckets used for loose matching
_TIMESTAMP_TYPES = frozenset(
    ["timestamp", "timestamptz", "timestamp with time zone",
     "timestamp without time zone", "datetime", "datetime2",
     "smalldatetime", "date"]
)
_STRING_TYPES = frozenset(
    ["varchar", "nvarchar", "char", "nchar", "text", "uuid",
     "character varying", "sysname"]
)
_INT_TYPES = frozenset(["int", "integer", "bigint", "smallint", "tinyint"])
_BOOL_TYPES = frozenset(["boolean", "bool", "bit", "tinyint"])


def _has_col(table: TableModel, name: str) -> bool:
    return name.lower() in table.column_names


def _col_type_ok(table: TableModel, name: str, allowed: frozenset[str]) -> bool:
    col = table.get_column(name)
    if col is None:
        return False
    return col.data_type.lower() in allowed


class AuditTrailRule(BaseRule):
    """SAMA-AUD-001: Every table must have created_at, created_by, updated_at, updated_by."""

    rule_id = "SAMA-AUD-001"
    rule_name = "Audit Trail Columns"
    severity = Severity.HIGH
    tags = ["SAMA", "audit", "CSF-3.3.5"]
    description = (
        "Every table must have created_at, created_by, updated_at, updated_by "
        "columns to maintain a complete audit trail per SAMA CSF §3.3.5."
    )

    REQUIRED = [
        ("created_at", _TIMESTAMP_TYPES),
        ("created_by", _STRING_TYPES | _INT_TYPES),
        ("updated_at", _TIMESTAMP_TYPES),
        ("updated_by", _STRING_TYPES | _INT_TYPES),
    ]

    def check(self, schema: SchemaModel) -> RuleResult:
        findings: list[Finding] = []
        for table in schema.tables:
            if self.is_exempt(table):
                continue
            for col_name, allowed_types in self.REQUIRED:
                if not _has_col(table, col_name):
                    findings.append(
                        self._finding(
                            table=table.name,
                            column=col_name,
                            message=f"Missing required audit column '{col_name}'",
                            detail=(
                                f"Table '{table.name}' does not have a '{col_name}' column. "
                                "SAMA CSF §3.3.5 requires full audit trail metadata on all tables."
                            ),
                            remediation=(
                                f"ALTER TABLE {table.name} ADD COLUMN {col_name} "
                                + ("TIMESTAMP NOT NULL DEFAULT NOW();"
                                   if "at" in col_name else "VARCHAR(255);")
                            ),
                        )
                    )
                elif not _col_type_ok(table, col_name, allowed_types):
                    col = table.get_column(col_name)
                    findings.append(
                        self._finding(
                            table=table.name,
                            column=col_name,
                            message=(
                                f"Column '{col_name}' has unexpected type '{col.data_type}'"
                            ),
                            detail=(
                                f"Expected one of: {sorted(allowed_types)}. "
                                "Incorrect types may cause audit trail failures."
                            ),
                            severity=Severity.MEDIUM,
                        )
                    )

        return self._fail(findings) if findings else self._pass()


class SoftDeleteRule(BaseRule):
    """SAMA-AUD-002: Tables must support soft-delete (is_deleted, deleted_at, deleted_by)."""

    rule_id = "SAMA-AUD-002"
    rule_name = "Soft Delete Pattern"
    severity = Severity.HIGH
    tags = ["SAMA", "soft-delete", "CSF-3.3.7"]
    description = (
        "PII and financial tables must support logical deletion via is_deleted, "
        "deleted_at, deleted_by. Hard deletes on regulated data violate SAMA CSF §3.3.7."
    )

    REQUIRED_ON_SENSITIVE = [
        ("is_deleted", _BOOL_TYPES),
        ("deleted_at", _TIMESTAMP_TYPES),
        ("deleted_by", _STRING_TYPES | _INT_TYPES),
    ]

    def check(self, schema: SchemaModel) -> RuleResult:
        findings: list[Finding] = []
        for table in schema.tables:
            if self.is_exempt(table):
                continue
            # Apply to all tables that contain sensitive data (tiers 1-4)
            if not table.has_sensitive_data:
                continue
            for col_name, allowed_types in self.REQUIRED_ON_SENSITIVE:
                if not _has_col(table, col_name):
                    findings.append(
                        self._finding(
                            table=table.name,
                            message=f"Sensitive table missing soft-delete column '{col_name}'",
                            detail=(
                                f"Table '{table.name}' contains sensitive data (tiers: "
                                f"{sorted(table.sensitivity_tiers)}) but lacks '{col_name}'. "
                                "SAMA CSF §3.3.7 prohibits hard-deletes on regulated data."
                            ),
                            remediation=self._remediation(table.name, col_name),
                        )
                    )

        return self._fail(findings) if findings else self._pass()

    @staticmethod
    def _remediation(table: str, col: str) -> str:
        if col == "is_deleted":
            return f"ALTER TABLE {table} ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;"
        if col == "deleted_at":
            return f"ALTER TABLE {table} ADD COLUMN deleted_at TIMESTAMP NULL;"
        if col == "deleted_by":
            return f"ALTER TABLE {table} ADD COLUMN deleted_by VARCHAR(255) NULL;"
        return ""


class AuditLogTableRule(BaseRule):
    """SAMA-AUD-003: PII/financial tables must have a corresponding _audit_log table."""

    rule_id = "SAMA-AUD-003"
    rule_name = "Audit Log Table Required"
    severity = Severity.CRITICAL
    tags = ["SAMA", "audit-log", "CSF-3.3.5"]
    description = (
        "Tables containing Tier 1 (directly identifying) or Tier 3 (financial) data "
        "must have a corresponding <table>_audit_log table in the schema."
    )

    APPLIES_TO_TIERS = {1, 3, 4}
    REQUIRED_AUDIT_COLS = {
        "operation", "changed_at", "changed_by", "old_values", "new_values", "record_id"
    }

    def check(self, schema: SchemaModel) -> RuleResult:
        findings: list[Finding] = []
        table_names = schema.table_names

        for table in schema.tables:
            if self.is_exempt(table):
                continue
            if not (table.sensitivity_tiers & self.APPLIES_TO_TIERS):
                continue

            expected_audit = f"{table.name.lower()}_audit_log"
            if expected_audit not in table_names:
                findings.append(
                    self._finding(
                        table=table.name,
                        message=f"No audit log table found for '{table.name}'",
                        detail=(
                            f"Table '{table.name}' contains Tier "
                            f"{sorted(table.sensitivity_tiers & self.APPLIES_TO_TIERS)} data "
                            f"but '{expected_audit}' does not exist in the schema."
                        ),
                        remediation=self._gen_audit_log_ddl(table, schema.dialect),
                    )
                )
            else:
                # Validate audit log table has required columns
                audit_table = schema.get_table(expected_audit)
                if audit_table:
                    missing = self.REQUIRED_AUDIT_COLS - audit_table.column_names
                    if missing:
                        findings.append(
                            self._finding(
                                table=expected_audit,
                                message=f"Audit log table missing required columns: {sorted(missing)}",
                                severity=Severity.HIGH,
                            )
                        )

        return self._fail(findings) if findings else self._pass()

    @staticmethod
    def _gen_audit_log_ddl(table: TableModel, dialect: str) -> str:
        if dialect == "postgres":
            return f"""CREATE TABLE {table.name}_audit_log (
    id BIGSERIAL PRIMARY KEY,
    record_id BIGINT NOT NULL,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT','UPDATE','DELETE')),
    changed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    changed_by VARCHAR(255) NOT NULL,
    old_values JSONB,
    new_values JSONB
);"""
        if dialect == "mysql":
            return f"""CREATE TABLE {table.name}_audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    record_id BIGINT NOT NULL,
    operation VARCHAR(10) NOT NULL,
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(255) NOT NULL,
    old_values JSON,
    new_values JSON
);"""
        # mssql
        return f"""CREATE TABLE {table.name}_audit_log (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    record_id BIGINT NOT NULL,
    operation NVARCHAR(10) NOT NULL,
    changed_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    changed_by NVARCHAR(255) NOT NULL,
    old_values NVARCHAR(MAX),
    new_values NVARCHAR(MAX)
);"""
