"""SAMA-REF-001 — No CASCADE DELETE on PII/financial tables."""

from __future__ import annotations

from parser.ddl_parser import SchemaModel, TableModel, ConstraintModel
from .base_rule import BaseRule, Finding, RuleResult, Severity


class ReferentialRule(BaseRule):
    """SAMA-REF-001: No CASCADE DELETE on foreign keys referencing PII/financial tables."""

    rule_id = "SAMA-REF-001"
    rule_name = "No Cascade Delete on Sensitive Tables"
    severity = Severity.CRITICAL
    tags = ["SAMA", "referential", "FK", "cascade"]
    description = (
        "Foreign keys that reference PII or financial tables (Tier 1, 3, 4) must not "
        "use CASCADE DELETE, as this can cause unintended bulk erasure of regulated records."
    )

    APPLIES_TO_TIERS = {1, 3, 4}
    FORBIDDEN_ACTIONS = {"CASCADE"}

    def check(self, schema: SchemaModel) -> RuleResult:
        findings: list[Finding] = []
        # Build a set of sensitive table names
        sensitive_tables: set[str] = {
            t.name.lower()
            for t in schema.tables
            if t.sensitivity_tiers & self.APPLIES_TO_TIERS
        }

        for table in schema.tables:
            if self.is_exempt(table):
                continue
            for fk in table.get_foreign_keys():
                if fk.ref_table and fk.ref_table.lower() in sensitive_tables:
                    if fk.on_delete and fk.on_delete.upper() in self.FORBIDDEN_ACTIONS:
                        col_str = ", ".join(fk.columns)
                        findings.append(
                            self._finding(
                                table=table.name,
                                column=col_str or None,
                                message=(
                                    f"FK from '{table.name}({col_str})' "
                                    f"→ '{fk.ref_table}' uses CASCADE DELETE"
                                ),
                                detail=(
                                    f"Table '{fk.ref_table}' contains Tier "
                                    f"{sorted(schema.get_table(fk.ref_table).sensitivity_tiers & self.APPLIES_TO_TIERS) if schema.get_table(fk.ref_table) else '?'} "
                                    "data. CASCADE DELETE would permanently erase regulated records "
                                    "and violates SAMA data retention requirements."
                                ),
                                remediation=(
                                    f"-- Change ON DELETE CASCADE to ON DELETE RESTRICT:\n"
                                    f"-- Drop and recreate the FK constraint on {table.name}({col_str})\n"
                                    f"-- to reference {fk.ref_table} with ON DELETE RESTRICT."
                                ),
                            )
                        )

        return self._fail(findings) if findings else self._pass()
