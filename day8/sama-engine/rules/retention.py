"""SAMA-RET-001 — Data retention metadata on financial tables."""

from __future__ import annotations

from parser.ddl_parser import SchemaModel
from .base_rule import BaseRule, Finding, RuleResult, Severity


class RetentionRule(BaseRule):
    """SAMA-RET-001: Financial tables must include retention metadata columns."""

    rule_id = "SAMA-RET-001"
    rule_name = "Data Retention Metadata"
    severity = Severity.MEDIUM
    tags = ["SAMA", "retention", "financial"]
    description = (
        "Financial and transaction tables must include retention metadata columns "
        "(retention_period, data_category) to enforce SAMA-mandated minimum "
        "5-year retention for financial records."
    )

    APPLIES_TO_TIERS = {3}  # Financial/regulated tier
    RECOMMENDED_COLS = ["retention_period", "data_category"]

    def check(self, schema: SchemaModel) -> RuleResult:
        findings: list[Finding] = []

        for table in schema.tables:
            if self.is_exempt(table):
                continue
            if not (table.sensitivity_tiers & self.APPLIES_TO_TIERS):
                continue

            for col_name in self.RECOMMENDED_COLS:
                if col_name not in table.column_names:
                    findings.append(
                        self._finding(
                            table=table.name,
                            message=(
                                f"Financial table '{table.name}' missing "
                                f"retention column '{col_name}'"
                            ),
                            detail=(
                                f"Table '{table.name}' contains Tier 3 (Financial/Regulated) data. "
                                "SAMA requires financial records to be retained for a minimum of 5 years. "
                                f"Adding '{col_name}' enables per-record retention policy enforcement."
                            ),
                            remediation=self._remediation(table.name, col_name, schema.dialect),
                        )
                    )

        return self._fail(findings) if findings else self._pass()

    @staticmethod
    def _remediation(table: str, col: str, dialect: str) -> str:
        if col == "retention_period":
            if dialect == "mssql":
                return f"ALTER TABLE {table} ADD retention_period SMALLINT NULL DEFAULT 60; -- months"
            return f"ALTER TABLE {table} ADD COLUMN retention_period SMALLINT NULL DEFAULT 60; -- months"
        if col == "data_category":
            if dialect == "mssql":
                return f"ALTER TABLE {table} ADD data_category NVARCHAR(100) NULL;"
            if dialect == "mysql":
                return f"ALTER TABLE {table} ADD COLUMN data_category VARCHAR(100) NULL;"
            return f"ALTER TABLE {table} ADD COLUMN data_category VARCHAR(100) NULL;"
        return ""
