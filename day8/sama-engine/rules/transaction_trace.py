"""SAMA-TRX-001 — Transaction traceability for payment/transfer tables."""

from __future__ import annotations

import re

from parser.ddl_parser import SchemaModel, TableModel
from .base_rule import BaseRule, Finding, RuleResult, Severity

_TRANSACTION_PATTERNS = re.compile(
    r"(^|_)(transaction|payment|transfer|settlement|ledger|journal|remittance|disbursement)s?(_|$)",
    re.IGNORECASE,
)

_TRACE_COLUMNS = ["transaction_id", "reference_id", "correlation_id"]
_STATUS_COLUMNS = ["status", "transaction_status", "payment_status", "state"]


def _is_transaction_table(table: TableModel) -> bool:
    return bool(_TRANSACTION_PATTERNS.search(table.name))


class TransactionTraceRule(BaseRule):
    """SAMA-TRX-001: Transaction tables must have traceability and status columns."""

    rule_id = "SAMA-TRX-001"
    rule_name = "Transaction Traceability"
    severity = Severity.HIGH
    tags = ["SAMA", "traceability", "payments", "open-banking"]
    description = (
        "Transaction, payment, and transfer tables must have at least one of "
        "transaction_id / reference_id / correlation_id for end-to-end traceability, "
        "and a status column, as required by SAMA Open Banking and Payments frameworks."
    )

    def check(self, schema: SchemaModel) -> RuleResult:
        findings: list[Finding] = []

        for table in schema.tables:
            if self.is_exempt(table):
                continue
            if not _is_transaction_table(table):
                continue

            # Check trace ID columns — at least one must exist
            has_trace = any(c in table.column_names for c in _TRACE_COLUMNS)
            if not has_trace:
                findings.append(
                    self._finding(
                        table=table.name,
                        message=(
                            f"Transaction table '{table.name}' missing a trace ID column "
                            f"({', '.join(_TRACE_COLUMNS)})"
                        ),
                        detail=(
                            "SAMA Open Banking Framework requires end-to-end traceability "
                            "for all financial transactions. At least one of "
                            f"{_TRACE_COLUMNS} must be present."
                        ),
                        remediation=(
                            f"ALTER TABLE {table.name} ADD COLUMN reference_id VARCHAR(100) UNIQUE NOT NULL;"
                        ),
                    )
                )

            # Check status column
            has_status = any(c in table.column_names for c in _STATUS_COLUMNS)
            if not has_status:
                findings.append(
                    self._finding(
                        table=table.name,
                        message=f"Transaction table '{table.name}' missing a status column",
                        detail=(
                            "A status column is required to track transaction lifecycle "
                            "(PENDING → PROCESSING → COMPLETED/FAILED) for SAMA compliance."
                        ),
                        remediation=(
                            f"ALTER TABLE {table.name} ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'PENDING';"
                        ),
                        severity=Severity.MEDIUM,
                    )
                )

        return self._fail(findings) if findings else self._pass()
