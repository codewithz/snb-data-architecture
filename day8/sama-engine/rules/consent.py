"""PDPL-CON-001 / PDPL-DSR-001 — Consent records and data subject request tables."""

from __future__ import annotations

from parser.ddl_parser import SchemaModel
from .base_rule import BaseRule, Finding, RuleResult, Severity


class ConsentTableRule(BaseRule):
    """PDPL-CON-001: Schema must include a consent_records table."""

    rule_id = "PDPL-CON-001"
    rule_name = "Consent Records Table Required"
    severity = Severity.CRITICAL
    tags = ["PDPL", "consent", "Art.10"]
    description = (
        "The schema must include a 'consent_records' table to track data subject "
        "consent per PDPL Article 10 (consent as a lawful basis for processing)."
    )

    REQUIRED_TABLE = "consent_records"
    REQUIRED_COLUMNS = [
        "id",
        "data_subject_id",
        "purpose",
        "consent_given",
        "consent_date",
    ]
    RECOMMENDED_COLUMNS = ["withdrawal_date", "consent_version"]

    def check(self, schema: SchemaModel) -> RuleResult:
        findings: list[Finding] = []
        table = schema.get_table(self.REQUIRED_TABLE)

        if table is None:
            findings.append(
                self._finding(
                    table=self.REQUIRED_TABLE,
                    message="consent_records table is missing from the schema",
                    detail=(
                        "PDPL Article 10 requires that consent be recorded with the "
                        "data subject's identity, purpose, and date. "
                        "A consent_records table must be present."
                    ),
                    remediation=self._gen_ddl(schema.dialect),
                )
            )
        else:
            missing = [c for c in self.REQUIRED_COLUMNS if c not in table.column_names]
            for col in missing:
                findings.append(
                    self._finding(
                        table=self.REQUIRED_TABLE,
                        column=col,
                        message=f"consent_records table missing required column '{col}'",
                        severity=Severity.HIGH,
                    )
                )
            # Recommended columns as LOW findings
            missing_rec = [c for c in self.RECOMMENDED_COLUMNS if c not in table.column_names]
            for col in missing_rec:
                findings.append(
                    self._finding(
                        table=self.REQUIRED_TABLE,
                        column=col,
                        message=f"consent_records table missing recommended column '{col}'",
                        severity=Severity.LOW,
                    )
                )

        return self._fail(findings) if findings else self._pass()

    @staticmethod
    def _gen_ddl(dialect: str) -> str:
        if dialect == "postgres":
            return """CREATE TABLE consent_records (
    id BIGSERIAL PRIMARY KEY,
    data_subject_id BIGINT NOT NULL,
    purpose VARCHAR(500) NOT NULL,
    consent_given BOOLEAN NOT NULL DEFAULT FALSE,
    consent_date TIMESTAMP NOT NULL DEFAULT NOW(),
    withdrawal_date TIMESTAMP NULL,
    consent_version VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP,
    updated_by VARCHAR(255)
);"""
        if dialect == "mysql":
            return """CREATE TABLE consent_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    data_subject_id BIGINT NOT NULL,
    purpose VARCHAR(500) NOT NULL,
    consent_given TINYINT(1) NOT NULL DEFAULT 0,
    consent_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    withdrawal_date DATETIME NULL,
    consent_version VARCHAR(50),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);"""
        return """CREATE TABLE consent_records (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    data_subject_id BIGINT NOT NULL,
    purpose NVARCHAR(500) NOT NULL,
    consent_given BIT NOT NULL DEFAULT 0,
    consent_date DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    withdrawal_date DATETIME2 NULL,
    consent_version NVARCHAR(50),
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    created_by NVARCHAR(255) NOT NULL,
    updated_at DATETIME2 NULL,
    updated_by NVARCHAR(255)
);"""


class DSRTableRule(BaseRule):
    """PDPL-DSR-001: Schema must include a data_subject_requests table."""

    rule_id = "PDPL-DSR-001"
    rule_name = "Data Subject Requests Table Required"
    severity = Severity.CRITICAL
    tags = ["PDPL", "DSR", "Art.14-18"]
    description = (
        "The schema must include a 'data_subject_requests' table to handle "
        "access, rectification, erasure, and portability requests "
        "per PDPL Articles 14–18."
    )

    REQUIRED_TABLE = "data_subject_requests"
    REQUIRED_COLUMNS = [
        "id",
        "data_subject_id",
        "request_type",
        "status",
        "requested_at",
    ]
    RECOMMENDED_COLUMNS = ["completed_at", "response_due_date"]

    def check(self, schema: SchemaModel) -> RuleResult:
        findings: list[Finding] = []
        table = schema.get_table(self.REQUIRED_TABLE)

        if table is None:
            findings.append(
                self._finding(
                    table=self.REQUIRED_TABLE,
                    message="data_subject_requests table is missing from the schema",
                    detail=(
                        "PDPL Articles 14–18 grant data subjects the right to access, "
                        "rectify, erase, and port their data. A data_subject_requests "
                        "table is required to track these requests and their fulfilment."
                    ),
                    remediation=self._gen_ddl(schema.dialect),
                )
            )
        else:
            missing = [c for c in self.REQUIRED_COLUMNS if c not in table.column_names]
            for col in missing:
                findings.append(
                    self._finding(
                        table=self.REQUIRED_TABLE,
                        column=col,
                        message=f"data_subject_requests table missing required column '{col}'",
                        severity=Severity.HIGH,
                    )
                )
            missing_rec = [c for c in self.RECOMMENDED_COLUMNS if c not in table.column_names]
            for col in missing_rec:
                findings.append(
                    self._finding(
                        table=self.REQUIRED_TABLE,
                        column=col,
                        message=f"data_subject_requests table missing recommended column '{col}'",
                        severity=Severity.LOW,
                    )
                )

        return self._fail(findings) if findings else self._pass()

    @staticmethod
    def _gen_ddl(dialect: str) -> str:
        if dialect == "postgres":
            return """CREATE TABLE data_subject_requests (
    id BIGSERIAL PRIMARY KEY,
    data_subject_id BIGINT NOT NULL,
    request_type VARCHAR(50) NOT NULL
        CHECK (request_type IN ('ACCESS','RECTIFICATION','ERASURE','PORTABILITY','RESTRICTION','OBJECTION')),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    requested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP NULL,
    response_due_date DATE NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP,
    updated_by VARCHAR(255)
);"""
        if dialect == "mysql":
            return """CREATE TABLE data_subject_requests (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    data_subject_id BIGINT NOT NULL,
    request_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    response_due_date DATE NULL,
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at DATETIME NULL,
    updated_by VARCHAR(255)
);"""
        return """CREATE TABLE data_subject_requests (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    data_subject_id BIGINT NOT NULL,
    request_type NVARCHAR(50) NOT NULL,
    status NVARCHAR(50) NOT NULL DEFAULT 'PENDING',
    requested_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    completed_at DATETIME2 NULL,
    response_due_date DATE NULL,
    notes NVARCHAR(MAX),
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    created_by NVARCHAR(255) NOT NULL,
    updated_at DATETIME2 NULL,
    updated_by NVARCHAR(255)
);"""
