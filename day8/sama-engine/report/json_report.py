"""JSON compliance report generator."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from rules.base_rule import Finding, RuleResult, Severity

if TYPE_CHECKING:
    from parser.ddl_parser import SchemaModel

_SAMA_RULES = frozenset({
    "SAMA-AUD-001", "SAMA-AUD-002", "SAMA-AUD-003",
    "SAMA-REF-001", "SAMA-RET-001", "SAMA-INT-001", "SAMA-TRX-001",
})
_PDPL_RULES = frozenset({
    "PDPL-ENC-001", "PDPL-CON-001", "PDPL-DSR-001",
})


def build_tables_data(schema: "SchemaModel", classification_results: list, all_findings: list) -> list[dict]:
    """Build per-table breakdown dict used by JSON and HTML reporters.

    Args:
        schema: Parsed SchemaModel.
        classification_results: List of ClassificationResult from PIIClassifier.
        all_findings: Flat list of Finding objects from all rule results.
    """
    cls_by_table: dict[str, list] = {}
    for r in classification_results:
        cls_by_table.setdefault(r.table_name, []).append(r)

    findings_by_table: dict[str, list[Finding]] = {}
    for f in all_findings:
        findings_by_table.setdefault(f.table, []).append(f)

    tables = []
    for table in schema.tables:
        cls_list = cls_by_table.get(table.name, [])
        sensitive = [c for c in cls_list if c.is_sensitive]
        t_findings = findings_by_table.get(table.name, [])

        tables.append({
            "name": table.name,
            "column_count": len(table.columns),
            "has_sensitive_data": table.has_sensitive_data,
            "sensitive_column_count": len(sensitive),
            "finding_count": len(t_findings),
            "columns": [
                {
                    "name": col.name,
                    "type": col.data_type,
                    "nullable": col.nullable,
                    "is_primary_key": col.is_primary_key,
                }
                for col in table.columns
            ],
            "pii_classifications": [
                {
                    "column": c.column_name,
                    "tier": c.tier.value if c.tier else None,
                    "label": c.label or "—",
                    "pattern": c.matched_pattern or "—",
                }
                for c in sensitive
            ],
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity.value,
                    "severity_weight": f.severity.weight,
                    "column": f.column,
                    "message": f.message,
                    "remediation": f.remediation,
                }
                for f in sorted(t_findings, key=lambda x: -x.severity.weight)
            ],
        })

    return tables


@dataclass
class ComplianceReport:
    dialect: str
    ddl_source: str
    scan_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    rule_results: list[RuleResult] = field(default_factory=list)
    schema_summary: dict[str, Any] = field(default_factory=dict)
    # Per-table breakdown — populated by build_tables_data() after construction
    tables: list[dict] = field(default_factory=list)

    @property
    def all_findings(self) -> list[Finding]:
        findings: list[Finding] = []
        for r in self.rule_results:
            findings.extend(r.findings)
        return findings

    @property
    def passed(self) -> bool:
        return all(r.passed or r.skipped for r in self.rule_results)

    @property
    def score(self) -> float:
        """Compliance score 0–100 based on weighted severity of findings."""
        penalty = sum(f.severity.weight for f in self.all_findings)
        return max(0.0, round(100.0 - penalty, 1))

    def severity_summary(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for f in self.all_findings:
            counts[f.severity.value] += 1
        return counts

    def findings_by_regulation(self) -> dict[str, int]:
        sama = sum(1 for f in self.all_findings if f.rule_id in _SAMA_RULES)
        pdpl = sum(1 for f in self.all_findings if f.rule_id in _PDPL_RULES)
        return {"SAMA": sama, "PDPL": pdpl}

    def to_dict(self) -> dict[str, Any]:
        sev = self.severity_summary()
        reg = self.findings_by_regulation()
        ss = self.schema_summary
        all_f = self.all_findings
        flat_findings = [
            {**f.to_dict(), "severity_weight": f.severity.weight}
            for f in sorted(all_f, key=lambda x: -x.severity.weight)
        ]
        return {
            # Canonical keys (Phase 4+)
            "generated_at": self.scan_timestamp,
            "dialect": self.dialect,
            "ddl_source": self.ddl_source,
            "score": self.score,
            "passed": self.passed,
            "summary": {
                "total_tables": ss.get("table_count", 0),
                "total_columns": ss.get("total_columns", 0),
                "pii_columns": ss.get("sensitive_columns", 0),
                "compliance_score": self.score,
                "findings_by_severity": {
                    "critical": sev.get("CRITICAL", 0),
                    "high":     sev.get("HIGH", 0),
                    "medium":   sev.get("MEDIUM", 0),
                    "low":      sev.get("LOW", 0),
                    "info":     sev.get("INFO", 0),
                },
                "findings_by_regulation": reg,
                "total_findings": len(all_f),
                "rules_run":     len(self.rule_results),
                "rules_passed":  sum(1 for r in self.rule_results if r.passed),
                "rules_failed":  sum(1 for r in self.rule_results if not r.passed and not r.skipped),
                "rules_skipped": sum(1 for r in self.rule_results if r.skipped),
            },
            "tables":    self.tables,
            "findings":  flat_findings,
            "rule_results": [r.to_dict() for r in self.rule_results],
            # Backward-compat aliases
            "scan_timestamp": self.scan_timestamp,
            "compliance_score": self.score,
            "schema_summary": ss,
        }


class JSONReporter:
    """Serialize a ComplianceReport to JSON."""

    def __init__(self, indent: int = 2) -> None:
        self.indent = indent

    def render(self, report: ComplianceReport) -> str:
        return json.dumps(report.to_dict(), indent=self.indent, ensure_ascii=False)

    def write(self, report: ComplianceReport, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.render(report))
