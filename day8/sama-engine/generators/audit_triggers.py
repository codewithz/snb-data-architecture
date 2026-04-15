"""Audit Trigger Generator — produces complete SAMA audit infrastructure.

Outputs (all dialect-aware):
  audit_tables.sql       — CREATE TABLE for every {table}_audit_log
  audit_triggers.sql     — Trigger functions + CREATE TRIGGER for every table
  setup_session.sql      — Session variable helper + set_audit_context procedure
  trace_transaction.sql  — v_audit_trace UNION ALL view + forensic query helpers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from parser.ddl_parser import TableModel, SchemaModel

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_HEADER = """\
-- ================================================================
-- SAMA/PDPL Compliance Engine — Audit Infrastructure
-- File    : {filename}
-- Dialect : {dialect}
-- Tables  : {table_count}
-- Generated: {timestamp}
-- ⚠  Review before executing. Test on non-production first.
-- ================================================================

"""


@dataclass
class AuditOutput:
    """All four output files produced by the generator."""
    dialect: str
    audit_tables_sql: str = ""
    audit_triggers_sql: str = ""
    setup_session_sql: str = ""
    trace_transaction_sql: str = ""
    audited_tables: list[str] = field(default_factory=list)

    def write_to_dir(self, output_dir: str | Path) -> dict[str, Path]:
        """Write all four files to output_dir and return path map."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        files = {
            "audit_tables.sql":      self.audit_tables_sql,
            "audit_triggers.sql":    self.audit_triggers_sql,
            "setup_session.sql":     self.setup_session_sql,
            "trace_transaction.sql": self.trace_transaction_sql,
        }
        written: dict[str, Path] = {}
        for name, content in files.items():
            p = out / name
            p.write_text(content, encoding="utf-8")
            written[name] = p
        return written


class AuditTriggerGenerator:
    """Generate complete audit trail infrastructure for all sensitive tables.

    Usage::

        gen = AuditTriggerGenerator(dialect="postgres")
        output = gen.generate(schema)
        output.write_to_dir("./audit/")
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

    def generate(self, schema: SchemaModel) -> AuditOutput:
        """Generate all audit output for every sensitive table in the schema."""
        # Only audit tables that contain PII or financial data
        audited = [t for t in schema.tables if t.has_sensitive_data]

        timestamp = datetime.now(timezone.utc).isoformat()
        table_count = len(audited)

        output = AuditOutput(
            dialect=self.dialect,
            audited_tables=[t.name for t in audited],
        )

        output.audit_tables_sql = self._header("audit_tables.sql", table_count, timestamp) \
            + self.generate_tables_sql(audited)

        output.audit_triggers_sql = self._header("audit_triggers.sql", table_count, timestamp) \
            + self.generate_triggers_sql(audited)

        output.setup_session_sql = self._header("setup_session.sql", table_count, timestamp) \
            + self.generate_session_setup_sql([t.name for t in audited])

        output.trace_transaction_sql = self._header("trace_transaction.sql", table_count, timestamp) \
            + self.generate_trace_view_sql([t.name for t in audited])

        return output

    def generate_tables_sql(self, tables: list[TableModel]) -> str:
        """Render audit log CREATE TABLE DDL for each table."""
        parts: list[str] = []
        for table in tables:
            sql = self._render("audit_log_table.sql.j2", {"table": table.name})
            if sql:
                parts.append(sql.strip())
        return "\n\n".join(parts) + "\n"

    def generate_triggers_sql(self, tables: list[TableModel]) -> str:
        """Render trigger function + CREATE TRIGGER for each table."""
        parts: list[str] = []
        for table in tables:
            pk_col = self._get_pk_col(table)
            columns = [c.name for c in table.columns]
            sql = self._render("audit_trigger.sql.j2", {
                "table": table.name,
                "pk_col": pk_col,
                "columns": columns,
            })
            if sql:
                parts.append(sql.strip())
        return "\n\n".join(parts) + "\n"

    def generate_session_setup_sql(self, table_names: list[str]) -> str:
        """Render session variable setup helper script."""
        sql = self._render("setup_session.sql.j2", {"audited_tables": table_names})
        return (sql or self._fallback_session_setup()).strip() + "\n"

    def generate_trace_view_sql(self, table_names: list[str]) -> str:
        """Render cross-table correlation_id trace view."""
        if not table_names:
            return "-- No audited tables found.\n"
        sql = self._render("trace_transaction.sql.j2", {"audited_tables": table_names})
        return (sql or self._fallback_trace(table_names)).strip() + "\n"

    # ── Legacy / convenience methods (backward compat) ────────────────────────

    def generate_for_schema(self, schema: SchemaModel) -> str:
        """Return tables + triggers combined (original API, backward compat)."""
        audited = [t for t in schema.tables if t.has_sensitive_data]
        tables_sql = self.generate_tables_sql(audited)
        triggers_sql = self.generate_triggers_sql(audited)
        return tables_sql + "\n" + triggers_sql

    def generate_for_table(self, table: TableModel) -> str:
        """Return table DDL + trigger for a single table (backward compat)."""
        tables_sql = self.generate_tables_sql([table])
        triggers_sql = self.generate_triggers_sql([table])
        return tables_sql + "\n" + triggers_sql

    # ── Internal ─────────────────────────────────────────────────────────────

    def _render(self, template_name: str, ctx: dict) -> Optional[str]:
        if self._env is None:
            return None
        try:
            return self._env.get_template(template_name).render(**ctx)
        except TemplateNotFound:
            return None
        except Exception as exc:
            return f"-- Template error ({template_name}): {exc}\n"

    @staticmethod
    def _get_pk_col(table: TableModel) -> str:
        for col in table.columns:
            if col.is_primary_key:
                return col.name
        # Check table-level constraints
        for c in table.constraints:
            if c.type == "PRIMARY_KEY" and c.columns:
                return c.columns[0]
        return "id"

    @staticmethod
    def _header(filename: str, table_count: int, timestamp: str) -> str:
        return _HEADER.format(
            filename=filename,
            dialect="UNKNOWN",  # overridden by subclass context
            table_count=table_count,
            timestamp=timestamp,
        )

    def _header(self, filename: str, table_count: int, timestamp: str) -> str:  # noqa: F811
        return _HEADER.format(
            filename=filename,
            dialect=self.dialect.upper(),
            table_count=table_count,
            timestamp=timestamp,
        )

    # ── Plain-text fallbacks if templates directory is missing ────────────────

    def _fallback_session_setup(self) -> str:
        if self.dialect == "postgres":
            return (
                "-- Set before any DML in your transaction:\n"
                "SET LOCAL app.current_user   = 'user@example.com';\n"
                "SET LOCAL app.correlation_id = gen_random_uuid()::TEXT;\n"
                "SET LOCAL app.application_id = 'my-service';\n"
            )
        if self.dialect == "mysql":
            return (
                "SET @app_current_user   = 'user@example.com';\n"
                "SET @app_correlation_id = UUID();\n"
                "SET @app_application_id = 'my-service';\n"
            )
        return (
            "EXEC sp_set_session_context 'current_user_id', N'user@example.com';\n"
            "EXEC sp_set_session_context 'correlation_id',  NEWID();\n"
            "EXEC sp_set_session_context 'application_id',  N'my-service';\n"
        )

    def _fallback_trace(self, table_names: list[str]) -> str:
        if self.dialect == "postgres":
            unions = "\nUNION ALL\n".join(
                f"SELECT '{t}' AS source_table, audit_id, record_id, operation, "
                f"performed_by, performed_at, correlation_id, old_values, new_values "
                f"FROM {t}_audit_log"
                for t in table_names
            )
            return f"CREATE OR REPLACE VIEW v_audit_trace AS\n{unions}\nORDER BY performed_at;\n"
        return "-- Trace view: see templates/trace_transaction.sql.j2\n"
