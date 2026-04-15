"""Abstract base rule interface for all compliance rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from parser.ddl_parser import SchemaModel, TableModel


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    @property
    def weight(self) -> int:
        return {"CRITICAL": 10, "HIGH": 5, "MEDIUM": 2, "LOW": 1, "INFO": 0}[self.value]


@dataclass
class Finding:
    rule_id: str
    rule_name: str
    severity: Severity
    table: str
    column: Optional[str] = None
    message: str = ""
    detail: str = ""
    remediation: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "table": self.table,
            "column": self.column,
            "message": self.message,
            "detail": self.detail,
            "remediation": self.remediation,
            "tags": self.tags,
        }

    def __repr__(self) -> str:
        loc = f"{self.table}.{self.column}" if self.column else self.table
        return f"[{self.severity.value}] {self.rule_id} @ {loc}: {self.message}"


@dataclass
class RuleResult:
    rule_id: str
    rule_name: str
    passed: bool
    findings: list[Finding] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "passed": self.passed,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "findings": [f.to_dict() for f in self.findings],
        }


class BaseRule(ABC):
    """Abstract base class for all compliance rules.

    Subclasses must implement `check()` which receives the full SchemaModel
    and returns a RuleResult.
    """

    rule_id: str = ""
    rule_name: str = ""
    severity: Severity = Severity.MEDIUM
    description: str = ""
    tags: list[str] = []

    # Patterns for tables that are exempt from this rule
    EXEMPT_PATTERNS: list[str] = [
        "_audit_log",
        "_history",
        "flyway_schema_history",
        "schema_migrations",
        "alembic_version",
        "django_migrations",
    ]

    def __init__(self, config: Optional[dict] = None) -> None:
        self.config = config or {}

    @abstractmethod
    def check(self, schema: SchemaModel) -> RuleResult:
        """Run the rule against the full schema and return findings."""

    def is_exempt(self, table: TableModel) -> bool:
        """Return True if the table should be skipped by this rule."""
        name_lower = table.name.lower()
        return any(name_lower.endswith(p) or name_lower == p.strip("_")
                   for p in self.EXEMPT_PATTERNS)

    def _pass(self) -> RuleResult:
        return RuleResult(rule_id=self.rule_id, rule_name=self.rule_name, passed=True)

    def _fail(self, findings: list[Finding]) -> RuleResult:
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            passed=False,
            findings=findings,
        )

    def _skip(self, reason: str) -> RuleResult:
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            passed=True,
            skipped=True,
            skip_reason=reason,
        )

    def _finding(
        self,
        table: str,
        message: str,
        column: Optional[str] = None,
        detail: str = "",
        remediation: str = "",
        severity: Optional[Severity] = None,
    ) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            severity=severity or self.severity,
            table=table,
            column=column,
            message=message,
            detail=detail,
            remediation=remediation,
            tags=list(self.tags),
        )
