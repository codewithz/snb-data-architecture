"""SAMA & PDPL Compliance Engine — FastAPI Web Application."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Ensure project root is importable when running from any working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from classifier.pii_classifier import PIIClassifier
from generators.audit_triggers import AuditTriggerGenerator
from generators.remediation import RemediationGenerator
from parser.ddl_parser import DDLParser
from parser.dialect import SUPPORTED_DIALECTS, normalize_dialect
from report.html_report import HTMLReporter
from report.json_report import ComplianceReport, build_tables_data
from rules.access_control import PrimaryKeyRule
from rules.audit_trail import AuditLogTableRule, AuditTrailRule, SoftDeleteRule
from rules.consent import ConsentTableRule, DSRTableRule
from rules.encryption import EncryptionRule
from rules.referential import ReferentialRule
from rules.retention import RetentionRule
from rules.transaction_trace import TransactionTraceRule

_WEB_DIR = Path(__file__).parent

app = FastAPI(
    title="SAMA & PDPL Compliance Engine",
    description="Scan SQL DDL files for SAMA and PDPL compliance issues",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS — allow any origin so external React / other frontends can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(_WEB_DIR / "static")), name="static")
_templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))


# ── Pydantic models ────────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    ddl: str
    dialect: str = "postgres"
    generate_fix: bool = False
    generate_audit: bool = False


# ── Internal helpers ───────────────────────────────────────────────────────────

def _build_rules() -> list:
    return [
        PrimaryKeyRule({}),
        AuditTrailRule({}),
        SoftDeleteRule({}),
        AuditLogTableRule({}),
        EncryptionRule({}),
        ReferentialRule({}),
        ConsentTableRule({}),
        DSRTableRule({}),
        RetentionRule({}),
        TransactionTraceRule({}),
    ]


def _run_scan(req: ScanRequest):
    """Parse, classify, run rules, and return (report, schema, classification_results)."""
    try:
        dialect = normalize_dialect(req.dialect)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not req.ddl.strip():
        raise HTTPException(status_code=422, detail="DDL text is required")

    parser = DDLParser(dialect=dialect)
    schema = parser.parse(req.ddl)
    if not schema.tables:
        raise HTTPException(
            status_code=422,
            detail="No tables found in DDL — check dialect and SQL syntax",
        )

    classifier = PIIClassifier()
    cls_results = classifier.classify_schema(schema)

    rule_results = [rule.check(schema) for rule in _build_rules()]
    sensitive_cols = [r for r in cls_results if r.is_sensitive]

    report = ComplianceReport(
        dialect=dialect,
        ddl_source="<web-upload>",
        rule_results=rule_results,
        schema_summary={
            "table_count": len(schema.tables),
            "tables": [t.name for t in schema.tables],
            "sensitive_columns": len(sensitive_cols),
            "parse_errors": len(schema.parse_errors),
        },
    )
    # Populate per-table breakdown
    report.tables = build_tables_data(schema, cls_results, report.all_findings)

    return report, schema, cls_results


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(request, "index.html")


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "engine": "SAMA & PDPL Compliance Engine",
        "version": "1.0.0",
        "supported_dialects": sorted(SUPPORTED_DIALECTS),
    }


@app.post("/api/scan")
async def scan(req: ScanRequest) -> dict:
    """Full compliance scan — returns JSON report with all details."""
    report, schema, cls_results = _run_scan(req)
    dialect = report.dialect

    response = report.to_dict()

    # Classification details for the UI
    response["classification"] = [
        {
            "table":        r.table_name,
            "column":       r.column_name,
            "tier":         r.tier.value if r.tier else None,
            "label":        r.label or "—",
            "pattern":      r.matched_pattern or "—",
            "is_sensitive": r.is_sensitive,
        }
        for r in cls_results
    ]
    response["parse_warnings"] = schema.parse_errors

    if req.generate_fix:
        rem_gen = RemediationGenerator(dialect=dialect)
        script = rem_gen.generate(report.all_findings, schema)
        response["remediation_sql"] = script.render()
    else:
        response["remediation_sql"] = None

    if req.generate_audit:
        audit_gen = AuditTriggerGenerator(dialect=dialect)
        ao = audit_gen.generate(schema)
        response["audit_trail"] = {
            "audited_tables":       ao.audited_tables,
            "audit_tables_sql":     ao.audit_tables_sql,
            "audit_triggers_sql":   ao.audit_triggers_sql,
            "setup_session_sql":    ao.setup_session_sql,
            "trace_transaction_sql": ao.trace_transaction_sql,
        }
    else:
        response["audit_trail"] = None

    return response


@app.post("/api/scan/html", response_class=HTMLResponse)
async def scan_html(req: ScanRequest) -> HTMLResponse:
    """Full compliance scan — returns a downloadable self-contained HTML report."""
    report, schema, cls_results = _run_scan(req)
    # HTML reporter uses report.tables (already populated by _run_scan)
    html = HTMLReporter().render(report)
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": 'attachment; filename="compliance_report.html"'},
    )


@app.post("/api/remediation", response_class=PlainTextResponse)
async def remediation(req: ScanRequest) -> PlainTextResponse:
    """Return just the remediation SQL for all findings."""
    report, schema, _ = _run_scan(req)
    gen = RemediationGenerator(dialect=report.dialect)
    script = gen.generate(report.all_findings, schema)
    return PlainTextResponse(
        content=script.render(),
        headers={"Content-Disposition": 'attachment; filename="remediation_report.sql"'},
    )


@app.post("/api/audit-trail")
async def audit_trail(req: ScanRequest) -> dict:
    """Return just the audit trail SQL for all sensitive tables."""
    report, schema, _ = _run_scan(req)
    gen = AuditTriggerGenerator(dialect=report.dialect)
    ao = gen.generate(schema)
    return {
        "audited_tables":        ao.audited_tables,
        "audit_tables_sql":      ao.audit_tables_sql,
        "audit_triggers_sql":    ao.audit_triggers_sql,
        "setup_session_sql":     ao.setup_session_sql,
        "trace_transaction_sql": ao.trace_transaction_sql,
    }
