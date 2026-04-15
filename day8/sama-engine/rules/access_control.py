"""SAMA-INT-001 — Primary key required on all tables."""

from __future__ import annotations

from parser.ddl_parser import SchemaModel
from .base_rule import BaseRule, Finding, RuleResult, Severity


class PrimaryKeyRule(BaseRule):
    """SAMA-INT-001: Every table must have a primary key."""

    rule_id = "SAMA-INT-001"
    rule_name = "Primary Key Required"
    severity = Severity.HIGH
    tags = ["SAMA", "integrity", "primary-key"]
    description = (
        "Every table must have a primary key to ensure record uniqueness "
        "and enable reliable audit trail referencing."
    )

    def check(self, schema: SchemaModel) -> RuleResult:
        findings: list[Finding] = []

        for table in schema.tables:
            if self.is_exempt(table):
                continue
            if not table.has_primary_key:
                findings.append(
                    self._finding(
                        table=table.name,
                        message=f"Table '{table.name}' has no primary key",
                        detail=(
                            "A primary key is required for row-level uniqueness, "
                            "audit log referencing (record_id FK), and reliable "
                            "replication/CDC pipelines."
                        ),
                        remediation=(
                            f"ALTER TABLE {table.name} ADD COLUMN id "
                            + ("BIGSERIAL PRIMARY KEY;" if schema.dialect == "postgres"
                               else "BIGINT AUTO_INCREMENT PRIMARY KEY;" if schema.dialect == "mysql"
                               else "BIGINT IDENTITY(1,1) PRIMARY KEY;")
                        ),
                    )
                )

        return self._fail(findings) if findings else self._pass()
