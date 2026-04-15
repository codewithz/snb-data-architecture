"""PDPL-ENC-001 — Encryption of Tier 1 and Tier 4 columns."""

from __future__ import annotations

from parser.ddl_parser import SchemaModel, TableModel, ColumnModel
from parser.dialect import ENCRYPTED_TYPES
from .base_rule import BaseRule, Finding, RuleResult, Severity


class EncryptionRule(BaseRule):
    """PDPL-ENC-001: Tier 1 and Tier 4 columns must use encrypted storage types."""

    rule_id = "PDPL-ENC-001"
    rule_name = "PII Column Encryption"
    severity = Severity.CRITICAL
    tags = ["PDPL", "encryption", "Art.8"]
    description = (
        "Tier 1 (directly identifying) and Tier 4 (PDPL Art.3 sensitive) columns "
        "must be stored as BYTEA (PostgreSQL) or VARBINARY (MySQL/MSSQL) to indicate "
        "at-rest encryption, per PDPL Article 8."
    )

    APPLIES_TO_TIERS = {1, 4}

    def check(self, schema: SchemaModel) -> RuleResult:
        dialect = schema.dialect
        encrypted_types = ENCRYPTED_TYPES.get(dialect, set())
        findings: list[Finding] = []

        for table in schema.tables:
            if self.is_exempt(table):
                continue
            for col in table.columns:
                if col.pii_tier not in self.APPLIES_TO_TIERS:
                    continue
                if col.data_type.lower() not in encrypted_types:
                    findings.append(
                        self._finding(
                            table=table.name,
                            column=col.name,
                            message=(
                                f"Tier {col.pii_tier} column '{col.name}' "
                                f"is not stored as an encrypted type "
                                f"(current: '{col.data_type}')"
                            ),
                            detail=(
                                f"Column '{table.name}.{col.name}' is classified as "
                                f"Tier {col.pii_tier} ({col.pii_label}). "
                                f"For {dialect}, encrypted storage types are: "
                                f"{sorted(encrypted_types)}. "
                                "PDPL Article 8 requires sensitive personal data to be encrypted at rest."
                            ),
                            remediation=self._remediation(
                                table.name, col.name, col.data_type, dialect
                            ),
                        )
                    )

        return self._fail(findings) if findings else self._pass()

    @staticmethod
    def _remediation(table: str, column: str, current_type: str, dialect: str) -> str:
        if dialect == "postgres":
            return (
                f"-- Migrate {table}.{column} to encrypted storage:\n"
                f"ALTER TABLE {table} ADD COLUMN {column}_encrypted BYTEA;\n"
                f"UPDATE {table} SET {column}_encrypted = pgp_sym_encrypt({column}::TEXT, current_setting('app.encryption_key'));\n"
                f"ALTER TABLE {table} DROP COLUMN {column};\n"
                f"ALTER TABLE {table} RENAME COLUMN {column}_encrypted TO {column};"
            )
        if dialect == "mysql":
            return (
                f"-- Migrate {table}.{column} to encrypted storage:\n"
                f"ALTER TABLE {table} ADD COLUMN {column}_encrypted VARBINARY(512);\n"
                f"UPDATE {table} SET {column}_encrypted = AES_ENCRYPT({column}, @encryption_key);\n"
                f"ALTER TABLE {table} DROP COLUMN {column};\n"
                f"ALTER TABLE {table} CHANGE {column}_encrypted {column} VARBINARY(512);"
            )
        # mssql
        return (
            f"-- Migrate {table}.{column} to encrypted storage (Always Encrypted):\n"
            f"-- Use SQL Server Management Studio or PowerShell to enable Always Encrypted\n"
            f"-- on column {table}.{column} with a Column Encryption Key.\n"
            f"ALTER TABLE {table} ALTER COLUMN {column} VARBINARY(MAX);"
        )
