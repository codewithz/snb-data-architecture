"""Remediation DDL Generator — template-based fix-it SQL from compliance findings."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from rules.base_rule import Finding, Severity

# Template directory
_TEMPLATE_DIR = Path(__file__).parent / "templates"

# ── Audit column definitions per dialect ─────────────────────────────────────
_AUDIT_COLS: dict[str, list[dict]] = {
    "postgres": [
        {"name": "created_at",  "ddl": "TIMESTAMPTZ  NOT NULL DEFAULT NOW()",           "drop_default": False, "ddl_no_default": "TIMESTAMPTZ NOT NULL"},
        {"name": "created_by",  "ddl": "VARCHAR(255) NOT NULL DEFAULT 'MIGRATION'",     "drop_default": True,  "ddl_no_default": "VARCHAR(255) NOT NULL"},
        {"name": "updated_at",  "ddl": "TIMESTAMPTZ  NULL",                             "drop_default": False, "ddl_no_default": "TIMESTAMPTZ NULL"},
        {"name": "updated_by",  "ddl": "VARCHAR(255) NULL",                             "drop_default": False, "ddl_no_default": "VARCHAR(255) NULL"},
    ],
    "mysql": [
        {"name": "created_at",  "ddl": "DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP", "drop_default": False, "ddl_no_default": "DATETIME NOT NULL"},
        {"name": "created_by",  "ddl": "VARCHAR(255) NOT NULL DEFAULT 'MIGRATION'",       "drop_default": True,  "ddl_no_default": "VARCHAR(255) NOT NULL"},
        {"name": "updated_at",  "ddl": "DATETIME     NULL ON UPDATE CURRENT_TIMESTAMP",   "drop_default": False, "ddl_no_default": "DATETIME NULL"},
        {"name": "updated_by",  "ddl": "VARCHAR(255) NULL",                               "drop_default": False, "ddl_no_default": "VARCHAR(255) NULL"},
    ],
    "mssql": [
        {"name": "created_at",  "ddl": "DATETIME2    NOT NULL DEFAULT GETUTCDATE()",     "drop_default": False, "ddl_no_default": "DATETIME2 NOT NULL"},
        {"name": "created_by",  "ddl": "NVARCHAR(255) NOT NULL DEFAULT 'MIGRATION'",     "drop_default": True,  "ddl_no_default": "NVARCHAR(255) NOT NULL"},
        {"name": "updated_at",  "ddl": "DATETIME2    NULL",                              "drop_default": False, "ddl_no_default": "DATETIME2 NULL"},
        {"name": "updated_by",  "ddl": "NVARCHAR(255) NULL",                             "drop_default": False, "ddl_no_default": "NVARCHAR(255) NULL"},
    ],
}

# ── Rule → template file mapping ──────────────────────────────────────────────
_RULE_TEMPLATE: dict[str, str] = {
    "SAMA-AUD-001": "add_audit_columns.sql.j2",
    "SAMA-AUD-002": "add_soft_delete.sql.j2",
    "SAMA-AUD-003": "create_audit_log_table.sql.j2",
    "SAMA-INT-001": "add_primary_key.sql.j2",
    "SAMA-RET-001": "add_retention_column.sql.j2",
    "SAMA-REF-001": "replace_cascade_delete.sql.j2",
    "SAMA-TRX-001": "add_transaction_trace.sql.j2",
    "PDPL-ENC-001": "encrypt_column.sql.j2",
    "PDPL-CON-001": "create_consent_table.sql.j2",
    "PDPL-DSR-001": "create_dsr_table.sql.j2",
}

# Tier labels for context
_TIER_LABELS = {1: "Directly Identifying", 2: "Indirectly Identifying",
                3: "Financial/Regulated",  4: "PDPL Art.3 Sensitive"}

# Transaction trace columns
_TRACE_COLS = {"transaction_id", "reference_id", "correlation_id"}
_STATUS_COLS = {"status", "transaction_status", "payment_status", "state"}

# Section ordering: render these sections in dependency-safe order
_SECTION_ORDER = [
    ("PDPL-CON-001", "Schema Prerequisites"),
    ("PDPL-DSR-001", "Schema Prerequisites"),
    ("SAMA-INT-001",  "Structural Integrity"),
    ("SAMA-AUD-003", "Audit Infrastructure"),
    ("SAMA-AUD-001", "Audit Trail Columns"),
    ("SAMA-AUD-002", "Soft Delete Columns"),
    ("SAMA-RET-001",  "Data Retention"),
    ("SAMA-REF-001", "Referential Integrity"),
    ("SAMA-TRX-001", "Transaction Traceability"),
    ("PDPL-ENC-001", "Column Encryption"),
]


@dataclass
class RenderedBlock:
    rule_id: str
    section: str
    table: Optional[str]
    sql: str
    severity: Severity


@dataclass
class RemediationScript:
    dialect: str
    finding_count: int
    rendered_blocks: list[RenderedBlock] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def render(self) -> str:
        lines: list[str] = [
            "-- ================================================================",
            "-- SAMA/PDPL Compliance Engine — Remediation Script",
            f"-- Dialect  : {self.dialect.upper()}",
            f"-- Generated: {self.timestamp}",
            f"-- Findings : {self.finding_count}",
            f"-- Blocks   : {len(self.rendered_blocks)}",
            "--",
            "-- ⚠  REVIEW BEFORE EXECUTING. Test on a non-production database.",
            "-- ================================================================",
            "",
        ]

        current_section = ""
        for block in self.rendered_blocks:
            if block.section != current_section:
                current_section = block.section
                lines += [
                    "",
                    f"-- ── {current_section} {'─' * (60 - len(current_section))}",
                    "",
                ]
            lines.append(block.sql.strip())
            lines.append("")

        return "\n".join(lines)


class RemediationGenerator:
    """Generate a complete dialect-specific remediation SQL script from findings.

    Usage::

        gen = RemediationGenerator(dialect="postgres")
        script = gen.generate(findings, schema)
        print(script.render())
    """

    def __init__(self, dialect: str) -> None:
        from parser.dialect import normalize_dialect
        self.dialect = normalize_dialect(dialect)
        template_path = _TEMPLATE_DIR / self.dialect
        if template_path.exists():
            self._env = Environment(
                loader=FileSystemLoader(str(template_path)),
                autoescape=select_autoescape([]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self._env = None

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self, findings: list[Finding], schema=None) -> RemediationScript:
        """Render all findings into a RemediationScript."""
        script = RemediationScript(
            dialect=self.dialect,
            finding_count=len(findings),
        )

        # Group findings so we render once per (rule_id, table) for table-level
        # rules and once per (rule_id, table, column) for column-level rules.
        blocks = self._build_blocks(findings, schema)

        # Apply section ordering
        ordered: list[RenderedBlock] = []
        seen_rule_ids = {b.rule_id for b in blocks}
        for rule_id, section in _SECTION_ORDER:
            if rule_id not in seen_rule_ids:
                continue
            for block in blocks:
                if block.rule_id == rule_id:
                    block.section = section
                    ordered.append(block)

        # Append any blocks whose rule_id isn't in _SECTION_ORDER
        known = {r for r, _ in _SECTION_ORDER}
        for block in blocks:
            if block.rule_id not in known:
                block.section = "Other Fixes"
                ordered.append(block)

        script.rendered_blocks = ordered
        return script

    # ── Internal ─────────────────────────────────────────────────────────────

    def _build_blocks(
        self, findings: list[Finding], schema
    ) -> list[RenderedBlock]:
        blocks: list[RenderedBlock] = []

        # Deduplicate: (rule_id, table, column_or_none)
        seen: set[tuple] = set()

        # Schema-level rules — render once regardless of table
        for rule_id in ("PDPL-CON-001", "PDPL-DSR-001"):
            matching = [f for f in findings if f.rule_id == rule_id]
            if matching and ("schema", rule_id) not in seen:
                seen.add(("schema", rule_id))
                sql = self._render_schema_rule(rule_id, matching[0])
                if sql:
                    blocks.append(RenderedBlock(
                        rule_id=rule_id, section="", table=None,
                        sql=sql, severity=matching[0].severity,
                    ))

        # Table-level rules — one render per (rule_id, table)
        for rule_id in ("SAMA-INT-001", "SAMA-AUD-003", "SAMA-AUD-002",
                         "SAMA-RET-001", "SAMA-TRX-001"):
            by_table: dict[str, list[Finding]] = {}
            for f in findings:
                if f.rule_id == rule_id:
                    by_table.setdefault(f.table, []).append(f)
            for table, table_findings in by_table.items():
                key = (rule_id, table)
                if key in seen:
                    continue
                seen.add(key)
                sql = self._render_table_rule(rule_id, table, table_findings, schema)
                if sql:
                    blocks.append(RenderedBlock(
                        rule_id=rule_id, section="", table=table,
                        sql=sql, severity=table_findings[0].severity,
                    ))

        # SAMA-AUD-001 — group all missing columns per table into one render
        audit_by_table: dict[str, list[Finding]] = {}
        for f in findings:
            if f.rule_id == "SAMA-AUD-001" and f.column:
                audit_by_table.setdefault(f.table, []).append(f)
        for table, table_findings in audit_by_table.items():
            key = ("SAMA-AUD-001", table)
            if key in seen:
                continue
            seen.add(key)
            sql = self._render_audit_columns(table, table_findings)
            if sql:
                blocks.append(RenderedBlock(
                    rule_id="SAMA-AUD-001", section="", table=table,
                    sql=sql, severity=table_findings[0].severity,
                ))

        # SAMA-REF-001 — one render per FK violation
        for f in findings:
            if f.rule_id != "SAMA-REF-001":
                continue
            key = ("SAMA-REF-001", f.table, f.column or "")
            if key in seen:
                continue
            seen.add(key)
            sql = self._render_fk_fix(f, schema)
            if sql:
                blocks.append(RenderedBlock(
                    rule_id="SAMA-REF-001", section="", table=f.table,
                    sql=sql, severity=f.severity,
                ))

        # PDPL-ENC-001 — one render per (table, column)
        for f in findings:
            if f.rule_id != "PDPL-ENC-001" or not f.column:
                continue
            key = ("PDPL-ENC-001", f.table, f.column)
            if key in seen:
                continue
            seen.add(key)
            sql = self._render_encrypt_column(f, schema)
            if sql:
                blocks.append(RenderedBlock(
                    rule_id="PDPL-ENC-001", section="", table=f.table,
                    sql=sql, severity=f.severity,
                ))

        return blocks

    # ── Template rendering helpers ────────────────────────────────────────────

    def _render(self, template_name: str, ctx: dict) -> Optional[str]:
        """Render a Jinja2 template; fall back to None if template missing."""
        if self._env is None:
            return None
        try:
            tmpl = self._env.get_template(template_name)
            return tmpl.render(**ctx)
        except TemplateNotFound:
            return None
        except Exception as exc:
            return f"-- Template error ({template_name}): {exc}\n"

    def _render_schema_rule(self, rule_id: str, finding: Finding) -> Optional[str]:
        template = _RULE_TEMPLATE.get(rule_id)
        if not template:
            return finding.remediation or None
        return self._render(template, {})

    def _render_table_rule(
        self,
        rule_id: str,
        table: str,
        findings: list[Finding],
        schema,
    ) -> Optional[str]:
        template = _RULE_TEMPLATE.get(rule_id)
        if not template:
            return findings[0].remediation if findings else None

        ctx: dict = {"table": table}

        if rule_id == "SAMA-AUD-003":
            # Need pk_col and column list from schema
            pk_col = "id"
            columns: list[str] = []
            if schema:
                tbl = schema.get_table(table)
                if tbl:
                    columns = [c.name for c in tbl.columns]
                    for col in tbl.columns:
                        if col.is_primary_key:
                            pk_col = col.name
                            break
            ctx["pk_col"] = pk_col
            ctx["columns"] = columns

        elif rule_id == "SAMA-TRX-001":
            missing_trace: list[str] = []
            has_status = False
            if schema:
                tbl = schema.get_table(table)
                if tbl:
                    if not any(c in tbl.column_names for c in _TRACE_COLS):
                        missing_trace.append("reference_id")
                        missing_trace.append("correlation_id")
                    if not any(c in tbl.column_names for c in _STATUS_COLS):
                        missing_trace.append("status")
            ctx["missing_trace"] = missing_trace

        return self._render(template, ctx)

    def _render_audit_columns(
        self, table: str, findings: list[Finding]
    ) -> Optional[str]:
        missing_names = {f.column.lower() for f in findings if f.column}
        all_defs = _AUDIT_COLS.get(self.dialect, _AUDIT_COLS["postgres"])
        missing_cols = [c for c in all_defs if c["name"] in missing_names]
        if not missing_cols:
            return None
        return self._render("add_audit_columns.sql.j2", {
            "table": table,
            "missing_columns": missing_cols,
        })

    def _render_fk_fix(self, finding: Finding, schema) -> Optional[str]:
        fk_columns = [c.strip() for c in (finding.column or "").split(",") if c.strip()]
        ref_table = ""
        ref_columns = ["id"]

        # Extract FK details from schema
        if schema and fk_columns:
            tbl = schema.get_table(finding.table)
            if tbl:
                for fk in tbl.get_foreign_keys():
                    if set(fk.columns) == set(fk_columns) and fk.on_delete == "CASCADE":
                        ref_table = fk.ref_table or ref_table
                        ref_columns = fk.ref_columns or ref_columns
                        break

        if not ref_table:
            # Parse from finding detail text as fallback
            m = re.search(r"→\s*['\"]?(\w+)['\"]?", finding.message)
            if m:
                ref_table = m.group(1)
            else:
                ref_table = "???"

        return self._render("replace_cascade_delete.sql.j2", {
            "table": finding.table,
            "fk_columns": fk_columns or ["id"],
            "ref_table": ref_table,
            "ref_columns": ref_columns,
        })

    def _render_encrypt_column(self, finding: Finding, schema) -> Optional[str]:
        col_name = finding.column or ""
        original_type = "VARCHAR(255)"
        tier = 1
        tier_label = _TIER_LABELS[1]

        if schema:
            tbl = schema.get_table(finding.table)
            if tbl:
                col = tbl.get_column(col_name)
                if col:
                    original_type = col.raw_type or col.data_type
                    tier = col.pii_tier or 1
                    tier_label = _TIER_LABELS.get(tier, "Sensitive")

        return self._render("encrypt_column.sql.j2", {
            "table": finding.table,
            "column": col_name,
            "original_type": original_type,
            "tier": tier,
            "tier_label": tier_label,
        })
