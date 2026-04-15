#!/usr/bin/env python3
"""SAMA & PDPL Database Compliance Engine — CLI entry point."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text

# Ensure project root is on path when running as script
sys.path.insert(0, str(Path(__file__).parent))

from parser.ddl_parser import DDLParser
from parser.dialect import normalize_dialect, SUPPORTED_DIALECTS
from classifier.pii_classifier import PIIClassifier
from rules.base_rule import Severity
from rules.audit_trail import AuditTrailRule, SoftDeleteRule, AuditLogTableRule
from rules.encryption import EncryptionRule
from rules.referential import ReferentialRule
from rules.consent import ConsentTableRule, DSRTableRule
from rules.retention import RetentionRule
from rules.transaction_trace import TransactionTraceRule
from rules.access_control import PrimaryKeyRule
from generators.remediation import RemediationGenerator
from generators.audit_triggers import AuditTriggerGenerator
from report.json_report import JSONReporter, ComplianceReport
from report.html_report import HTMLReporter

app = typer.Typer(
    name="sama-compliance",
    help="SAMA & PDPL Database Compliance Engine",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console(stderr=False)

_SEVERITY_COLORS = {
    "CRITICAL": "bold red",
    "HIGH": "bold yellow",
    "MEDIUM": "yellow",
    "LOW": "cyan",
    "INFO": "green",
}


def _run_fix(
    findings: list,
    report,
    schema,
    dialect: str,
    output_dir: Optional[Path],
    quiet: bool,
) -> None:
    """Generate template-based remediation SQL and write to output_dir."""
    import json as _json

    out = output_dir or Path("remediation")
    out.mkdir(parents=True, exist_ok=True)

    # 1. Template-based remediation SQL
    gen = RemediationGenerator(dialect=dialect)
    script = gen.generate(findings, schema)
    sql_path = out / "remediation_report.sql"
    sql_path.write_text(script.render(), encoding="utf-8")

    # 2. Findings JSON
    json_path = out / "findings.json"
    json_path.write_text(
        _json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if not quiet:
        console.print(
            Panel(
                f"[bold green]--fix outputs written to:[/] {out}/\n"
                f"  [cyan]remediation_report.sql[/]  — {len(script.rendered_blocks)} fix block(s) "
                f"across {len({b.table for b in script.rendered_blocks if b.table})} table(s)\n"
                f"  [cyan]findings.json[/]            — {len(findings)} finding(s)",
                title="Fix Output",
                border_style="green",
                box=box.ROUNDED,
            )
        )


def _build_rule_set(config: dict) -> list:
    return [
        PrimaryKeyRule(config),
        AuditTrailRule(config),
        SoftDeleteRule(config),
        AuditLogTableRule(config),
        EncryptionRule(config),
        ReferentialRule(config),
        ConsentTableRule(config),
        DSRTableRule(config),
        RetentionRule(config),
        TransactionTraceRule(config),
    ]


@app.command()
def scan(
    ddl: Path = typer.Option(
        ...,
        "--ddl", "-d",
        help="Path to the SQL DDL file to scan",
        exists=True,
        file_okay=True,
        readable=True,
    ),
    db: str = typer.Option(
        "postgres",
        "--db",
        help=f"Database dialect: {', '.join(sorted(SUPPORTED_DIALECTS))}",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Write JSON report to this file",
    ),
    html: Optional[Path] = typer.Option(
        None,
        "--html",
        help="Write HTML report to this file",
    ),
    remediation_sql: Optional[Path] = typer.Option(
        None,
        "--remediation",
        help="Write remediation SQL script to this file",
    ),
    audit_triggers: Optional[Path] = typer.Option(
        None,
        "--audit-triggers",
        help="Write audit trigger SQL to this file",
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Generate template-based remediation SQL and write to --output-dir",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        help="Directory to write remediation_report.sql + findings.json when --fix is set",
    ),
    fail_on: str = typer.Option(
        "CRITICAL",
        "--fail-on",
        help="Exit with code 1 if findings of this severity or higher exist",
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress console output"),
) -> None:
    """Scan a SQL DDL file for SAMA and PDPL compliance issues."""

    try:
        dialect = normalize_dialect(db)
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(2)

    ddl_text = ddl.read_text(encoding="utf-8")

    if not quiet:
        console.print(
            Panel(
                f"[bold cyan]SAMA & PDPL Compliance Engine[/]\n"
                f"File: [white]{ddl}[/]  Dialect: [white]{dialect.upper()}[/]",
                box=box.ROUNDED,
                border_style="blue",
            )
        )

    # ── Parse ────────────────────────────────────────────────────────────────
    parser = DDLParser(dialect=dialect)
    schema = parser.parse(ddl_text)

    if schema.parse_errors and not quiet:
        for err in schema.parse_errors:
            console.print(f"[yellow]Parse warning:[/] {err}")

    if not schema.tables:
        console.print("[bold red]No tables found in DDL.[/]")
        raise typer.Exit(2)

    if not quiet:
        console.print(f"\n[green]Parsed {len(schema.tables)} table(s):[/] "
                      + ", ".join(t.name for t in schema.tables))

    # ── Classify ─────────────────────────────────────────────────────────────
    classifier = PIIClassifier()
    classification_results = classifier.classify_schema(schema)
    sensitive_cols = [r for r in classification_results if r.is_sensitive]

    if not quiet and sensitive_cols:
        console.print(
            f"\n[cyan]PII Classification:[/] {len(sensitive_cols)} sensitive column(s) found"
        )
        cls_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        cls_table.add_column("Table", style="white")
        cls_table.add_column("Column", style="white")
        cls_table.add_column("Tier", justify="center")
        cls_table.add_column("Classification", style="cyan")
        for r in sensitive_cols:
            tier_color = {1: "red", 2: "yellow", 3: "magenta", 4: "bold red"}.get(r.tier.value, "white")
            cls_table.add_row(
                r.table_name, r.column_name,
                f"[{tier_color}]Tier {r.tier.value}[/]",
                r.label,
            )
        console.print(cls_table)

    # ── Run rules ────────────────────────────────────────────────────────────
    rules = _build_rule_set({})
    results = []
    for rule in rules:
        result = rule.check(schema)
        results.append(result)

    # ── Build report ─────────────────────────────────────────────────────────
    report = ComplianceReport(
        dialect=dialect,
        ddl_source=str(ddl),
        rule_results=results,
        schema_summary={
            "table_count": len(schema.tables),
            "tables": [t.name for t in schema.tables],
            "sensitive_columns": len(sensitive_cols),
            "parse_errors": len(schema.parse_errors),
        },
    )

    all_findings = report.all_findings
    sev_summary = report.severity_summary()

    # ── Console output ───────────────────────────────────────────────────────
    if not quiet:
        if all_findings:
            console.print(f"\n[bold]Findings ({len(all_findings)} total):[/]")
            findings_table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold dim")
            findings_table.add_column("Severity", width=10)
            findings_table.add_column("Rule ID", width=16)
            findings_table.add_column("Table", width=28)
            findings_table.add_column("Column", width=22)
            findings_table.add_column("Message")

            for f in sorted(all_findings, key=lambda x: -x.severity.weight):
                color = _SEVERITY_COLORS.get(f.severity.value, "white")
                findings_table.add_row(
                    f"[{color}]{f.severity.value}[/]",
                    f"[cyan]{f.rule_id}[/]",
                    f.table,
                    f.column or "—",
                    f.message,
                )
            console.print(findings_table)
        else:
            console.print("\n[bold green]✓ No findings — schema is compliant![/]")

        # Score panel
        score = report.score
        if score >= 80:
            score_style = "green"
            verdict = "COMPLIANT"
        elif score >= 50:
            score_style = "yellow"
            verdict = "NEEDS ATTENTION"
        else:
            score_style = "red"
            verdict = "NON-COMPLIANT"

        console.print(
            Panel(
                f"[bold {score_style}]Score: {score}/100  {verdict}[/]\n"
                f"CRITICAL: [red]{sev_summary['CRITICAL']}[/]  "
                f"HIGH: [yellow]{sev_summary['HIGH']}[/]  "
                f"MEDIUM: [yellow]{sev_summary['MEDIUM']}[/]  "
                f"LOW: [cyan]{sev_summary['LOW']}[/]",
                title="Compliance Score",
                border_style=score_style,
                box=box.ROUNDED,
            )
        )

    # ── Write outputs ─────────────────────────────────────────────────────────
    if output:
        JSONReporter().write(report, str(output))
        if not quiet:
            console.print(f"[green]JSON report written to:[/] {output}")

    if html:
        HTMLReporter().write(report, str(html))
        if not quiet:
            console.print(f"[green]HTML report written to:[/] {html}")

    if remediation_sql:
        gen = RemediationGenerator(dialect=dialect)
        script = gen.generate(all_findings, schema)
        remediation_sql.write_text(script.render(), encoding="utf-8")
        if not quiet:
            console.print(f"[green]Remediation SQL written to:[/] {remediation_sql}")

    if fix:
        _run_fix(
            findings=all_findings,
            report=report,
            schema=schema,
            dialect=dialect,
            output_dir=output_dir,
            quiet=quiet,
        )

    if audit_triggers:
        gen = AuditTriggerGenerator(dialect=dialect)
        trigger_sql = gen.generate_for_schema(schema)
        audit_triggers.write_text(trigger_sql, encoding="utf-8")
        if not quiet:
            console.print(f"[green]Audit triggers written to:[/] {audit_triggers}")

    # ── Exit code ─────────────────────────────────────────────────────────────
    try:
        fail_threshold = Severity(fail_on.upper())
    except ValueError:
        fail_threshold = Severity.CRITICAL

    threshold_weight = fail_threshold.weight
    blocking = [f for f in all_findings if f.severity.weight >= threshold_weight]
    if blocking:
        raise typer.Exit(1)


@app.command()
def classify(
    ddl: Path = typer.Option(
        ..., "--ddl", "-d",
        help="Path to DDL file",
        exists=True, file_okay=True, readable=True,
    ),
    db: str = typer.Option("postgres", "--db", help="Database dialect"),
) -> None:
    """Show PII classification results for all columns in the DDL."""
    dialect = normalize_dialect(db)
    ddl_text = ddl.read_text(encoding="utf-8")
    parser = DDLParser(dialect=dialect)
    schema = parser.parse(ddl_text)
    classifier = PIIClassifier()
    results = classifier.classify_schema(schema)

    tbl = Table(title="PII Classification Results", box=box.ROUNDED)
    tbl.add_column("Table")
    tbl.add_column("Column")
    tbl.add_column("Tier", justify="center")
    tbl.add_column("Label")
    tbl.add_column("Pattern")

    tier_colors = {1: "red", 2: "yellow", 3: "magenta", 4: "bold red"}
    for r in results:
        tier_str = f"[{tier_colors.get(r.tier.value,'white')}]Tier {r.tier.value}[/]" if r.tier else "[dim]—[/]"
        tbl.add_row(
            r.table_name, r.column_name,
            tier_str,
            r.label or "—",
            r.matched_pattern or "—",
        )
    console.print(tbl)


@app.command()
def generate_triggers(
    ddl: Path = typer.Option(
        ..., "--ddl", "-d",
        help="Path to DDL file",
        exists=True, file_okay=True, readable=True,
    ),
    db: str = typer.Option("postgres", "--db"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
) -> None:
    """Generate audit log tables and triggers for sensitive tables."""
    dialect = normalize_dialect(db)
    ddl_text = ddl.read_text(encoding="utf-8")
    parser = DDLParser(dialect=dialect)
    schema = parser.parse(ddl_text)
    classifier = PIIClassifier()
    classifier.classify_schema(schema)

    gen = AuditTriggerGenerator(dialect=dialect)
    sql = gen.generate_for_schema(schema)

    if output:
        output.write_text(sql, encoding="utf-8")
        console.print(f"[green]Audit triggers written to:[/] {output}")
    else:
        console.print(sql)


@app.command(name="audit-trail")
def audit_trail(
    ddl: Path = typer.Option(
        ..., "--ddl", "-d",
        help="Path to the SQL DDL file",
        exists=True, file_okay=True, readable=True,
    ),
    db: str = typer.Option(
        "postgres", "--db",
        help=f"Database dialect: {', '.join(sorted(SUPPORTED_DIALECTS))}",
    ),
    output_dir: Path = typer.Option(
        Path("audit"),
        "--output-dir",
        help="Directory to write the 4 audit output files",
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress console output"),
) -> None:
    """Generate complete SAMA audit trail infrastructure for all sensitive tables.

    Produces 4 files in --output-dir:\n
      audit_tables.sql       — CREATE TABLE for every _audit_log table\n
      audit_triggers.sql     — Trigger functions + CREATE TRIGGER\n
      setup_session.sql      — Session variable helpers + set_audit_context()\n
      trace_transaction.sql  — v_audit_trace UNION ALL view + forensic helpers
    """
    try:
        dialect = normalize_dialect(db)
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(2)

    ddl_text = ddl.read_text(encoding="utf-8")

    # Parse + classify
    parser_obj = DDLParser(dialect=dialect)
    schema = parser_obj.parse(ddl_text)
    if schema.parse_errors and not quiet:
        for err in schema.parse_errors:
            console.print(f"[yellow]Parse warning:[/] {err}")

    PIIClassifier().classify_schema(schema)

    audited = [t for t in schema.tables if t.has_sensitive_data]
    if not audited:
        console.print(
            "[yellow]No sensitive tables found — "
            "run 'classify' to see PII classification results.[/]"
        )
        raise typer.Exit(0)

    if not quiet:
        console.print(
            Panel(
                f"[bold cyan]SAMA Audit Trail Generator[/]\n"
                f"File: [white]{ddl}[/]  Dialect: [white]{dialect.upper()}[/]\n"
                f"Auditing [bold]{len(audited)}[/] sensitive table(s): "
                + ", ".join(t.name for t in audited),
                box=box.ROUNDED,
                border_style="blue",
            )
        )

    # Generate all four output files
    gen = AuditTriggerGenerator(dialect=dialect)
    audit_output = gen.generate(schema)
    written = audit_output.write_to_dir(output_dir)

    if not quiet:
        file_tbl = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
        file_tbl.add_column("File", style="cyan")
        file_tbl.add_column("Description")
        file_tbl.add_column("Size", justify="right", style="dim")
        descriptions = {
            "audit_tables.sql":      "CREATE TABLE DDL for every _audit_log table",
            "audit_triggers.sql":    "Trigger functions + CREATE TRIGGER per table",
            "setup_session.sql":     "set_audit_context() helper + usage examples",
            "trace_transaction.sql": "v_audit_trace UNION view + forensic queries",
        }
        for name, path in written.items():
            size = f"{path.stat().st_size:,} bytes"
            file_tbl.add_row(name, descriptions.get(name, ""), size)
        console.print(file_tbl)

        console.print(
            Panel(
                f"[bold green]Audit infrastructure written to:[/] {output_dir}/\n\n"
                f"[dim]Next steps:[/]\n"
                f"  1. Execute [cyan]audit_tables.sql[/] to create log tables\n"
                f"  2. Execute [cyan]audit_triggers.sql[/] to install triggers\n"
                f"  3. Integrate [cyan]setup_session.sql[/] into your app layer\n"
                f"  4. Use [cyan]trace_transaction.sql[/] view for incident forensics",
                border_style="green",
                box=box.ROUNDED,
            )
        )


@app.command(name="serve")
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (dev mode)"),
) -> None:
    """Launch the SAMA compliance web UI server.

    Opens a browser-based UI at http://<host>:<port>/ for interactive scanning.
    """
    try:
        import uvicorn
    except ImportError:
        console.print("[bold red]Error:[/] uvicorn is not installed. Run: pip install uvicorn")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold cyan]SAMA & PDPL Compliance Engine — Web UI[/]\n"
            f"Listening at [bold green]http://{host}:{port}/[/]\n"
            f"[dim]Press Ctrl+C to stop[/]",
            border_style="blue",
            box=box.ROUNDED,
        )
    )
    uvicorn.run(
        "web.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    app()
