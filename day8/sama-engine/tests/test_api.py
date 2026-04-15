"""Tests for the FastAPI web endpoints — Phase 5."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from web.app import app

client = TestClient(app)

_PG_DDL = """
CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255),
    national_id VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL
);
"""

_MYSQL_DDL = """
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255),
    phone_number VARCHAR(20)
);
"""


# ── Health ─────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "supported_dialects" in body
        assert "postgres" in body["supported_dialects"]

    def test_root_returns_html(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "SAMA" in r.text


# ── POST /api/scan ─────────────────────────────────────────────────────────────

class TestScanEndpoint:
    def test_scan_returns_200(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        assert r.status_code == 200

    def test_scan_has_score(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        body = r.json()
        assert "score" in body
        assert 0 <= body["score"] <= 100

    def test_scan_has_findings_array(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        body = r.json()
        assert "findings" in body
        assert isinstance(body["findings"], list)

    def test_scan_has_summary(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        body = r.json()
        assert "summary" in body
        assert "total_tables" in body["summary"]
        assert "findings_by_severity" in body["summary"]
        assert "findings_by_regulation" in body["summary"]

    def test_scan_has_classification(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        body = r.json()
        assert "classification" in body
        sensitive = [c for c in body["classification"] if c["is_sensitive"]]
        # email and national_id should be classified as sensitive
        assert any(c["column"] == "email" for c in sensitive)

    def test_scan_has_tables_breakdown(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        body = r.json()
        assert "tables" in body
        assert isinstance(body["tables"], list)
        assert any(t["name"] == "customers" for t in body["tables"])

    def test_scan_has_rule_results(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        body = r.json()
        assert "rule_results" in body
        assert len(body["rule_results"]) > 0

    def test_scan_generates_fix(self):
        r = client.post("/api/scan", json={
            "ddl": _PG_DDL, "dialect": "postgres", "generate_fix": True
        })
        body = r.json()
        assert body["remediation_sql"] is not None
        assert "ALTER TABLE" in body["remediation_sql"] or "CREATE" in body["remediation_sql"]

    def test_scan_no_fix_by_default(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        assert r.json()["remediation_sql"] is None

    def test_scan_generates_audit(self):
        r = client.post("/api/scan", json={
            "ddl": _PG_DDL, "dialect": "postgres", "generate_audit": True
        })
        body = r.json()
        at = body["audit_trail"]
        assert at is not None
        assert "customers" in at["audited_tables"]
        assert "CREATE TABLE" in at["audit_tables_sql"]

    def test_scan_no_audit_by_default(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        assert r.json()["audit_trail"] is None

    def test_scan_mysql_dialect(self):
        r = client.post("/api/scan", json={"ddl": _MYSQL_DDL, "dialect": "mysql"})
        assert r.status_code == 200
        assert r.json()["dialect"] == "mysql"

    def test_scan_invalid_dialect(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "oracle"})
        assert r.status_code == 400

    def test_scan_empty_ddl(self):
        r = client.post("/api/scan", json={"ddl": "", "dialect": "postgres"})
        assert r.status_code == 422

    def test_scan_no_tables(self):
        r = client.post("/api/scan", json={"ddl": "-- just a comment\n", "dialect": "postgres"})
        assert r.status_code == 422

    def test_scan_findings_have_severity_weight(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        findings = r.json()["findings"]
        assert all("severity_weight" in f for f in findings)

    def test_scan_findings_sorted_by_severity(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        weights = [f["severity_weight"] for f in r.json()["findings"]]
        assert weights == sorted(weights, reverse=True)

    def test_scan_regulation_breakdown(self):
        r = client.post("/api/scan", json={"ddl": _PG_DDL, "dialect": "postgres"})
        reg = r.json()["summary"]["findings_by_regulation"]
        assert "SAMA" in reg and "PDPL" in reg


# ── POST /api/scan/html ────────────────────────────────────────────────────────

class TestScanHtmlEndpoint:
    def test_returns_html(self):
        r = client.post("/api/scan/html", json={"ddl": _PG_DDL, "dialect": "postgres"})
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_html_has_report_content(self):
        r = client.post("/api/scan/html", json={"ddl": _PG_DDL, "dialect": "postgres"})
        assert "SAMA" in r.text
        assert "customers" in r.text

    def test_html_content_disposition(self):
        r = client.post("/api/scan/html", json={"ddl": _PG_DDL, "dialect": "postgres"})
        assert "compliance_report.html" in r.headers.get("content-disposition", "")


# ── POST /api/remediation ──────────────────────────────────────────────────────

class TestRemediationEndpoint:
    def test_returns_sql_text(self):
        r = client.post("/api/remediation", json={"ddl": _PG_DDL, "dialect": "postgres"})
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]

    def test_sql_has_content(self):
        r = client.post("/api/remediation", json={"ddl": _PG_DDL, "dialect": "postgres"})
        assert len(r.text) > 0

    def test_content_disposition(self):
        r = client.post("/api/remediation", json={"ddl": _PG_DDL, "dialect": "postgres"})
        assert "remediation_report.sql" in r.headers.get("content-disposition", "")


# ── POST /api/audit-trail ─────────────────────────────────────────────────────

class TestAuditTrailEndpoint:
    def test_returns_json(self):
        r = client.post("/api/audit-trail", json={"ddl": _PG_DDL, "dialect": "postgres"})
        assert r.status_code == 200
        body = r.json()
        assert "audited_tables" in body
        assert "audit_tables_sql" in body
        assert "audit_triggers_sql" in body
        assert "setup_session_sql" in body
        assert "trace_transaction_sql" in body

    def test_audit_tables_in_output(self):
        r = client.post("/api/audit-trail", json={"ddl": _PG_DDL, "dialect": "postgres"})
        assert "customers" in r.json()["audited_tables"]

    def test_no_sensitive_tables(self):
        ddl = "CREATE TABLE country_codes (code CHAR(2), name VARCHAR(100));"
        r = client.post("/api/audit-trail", json={"ddl": ddl, "dialect": "postgres"})
        assert r.status_code == 200
        assert r.json()["audited_tables"] == []
