"""Tests for the PII classifier."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from parser.ddl_parser import DDLParser, ColumnModel
from classifier.pii_classifier import PIIClassifier, PIITier


def make_col(name: str, dtype: str = "varchar") -> ColumnModel:
    return ColumnModel(name=name, data_type=dtype, raw_type=dtype)


class TestPIIClassifier:
    def setup_method(self):
        self.clf = PIIClassifier()

    # Tier 1 checks
    def test_email_is_tier1(self):
        col = make_col("email")
        result = self.clf.classify_column(col, "users")
        assert result.tier == PIITier.TIER1

    def test_full_name_is_tier1(self):
        col = make_col("full_name")
        result = self.clf.classify_column(col, "users")
        assert result.tier == PIITier.TIER1

    def test_national_id_is_tier1(self):
        col = make_col("national_id")
        result = self.clf.classify_column(col, "users")
        assert result.tier == PIITier.TIER1

    def test_phone_number_is_tier1(self):
        col = make_col("phone_number")
        result = self.clf.classify_column(col, "users")
        assert result.tier == PIITier.TIER1

    def test_dob_is_tier1(self):
        col = make_col("date_of_birth")
        result = self.clf.classify_column(col, "users")
        assert result.tier == PIITier.TIER1

    # Tier 2 checks
    def test_ip_address_is_tier2(self):
        col = make_col("ip_address")
        result = self.clf.classify_column(col, "sessions")
        assert result.tier == PIITier.TIER2

    def test_device_id_is_tier2(self):
        col = make_col("device_id")
        result = self.clf.classify_column(col, "devices")
        assert result.tier == PIITier.TIER2

    # Tier 3 checks
    def test_iban_is_tier3(self):
        col = make_col("iban")
        result = self.clf.classify_column(col, "accounts")
        assert result.tier == PIITier.TIER3

    def test_account_number_is_tier3(self):
        col = make_col("account_number")
        result = self.clf.classify_column(col, "accounts")
        assert result.tier == PIITier.TIER3

    def test_salary_is_tier3(self):
        col = make_col("salary")
        result = self.clf.classify_column(col, "employees")
        assert result.tier == PIITier.TIER3

    # Tier 4 checks
    def test_diagnosis_is_tier4(self):
        col = make_col("diagnosis")
        result = self.clf.classify_column(col, "health_records")
        assert result.tier == PIITier.TIER4

    def test_religion_is_tier4(self):
        col = make_col("religion")
        result = self.clf.classify_column(col, "profiles")
        assert result.tier == PIITier.TIER4

    def test_racial_origin_is_tier4(self):
        col = make_col("racial_origin")
        result = self.clf.classify_column(col, "profiles")
        assert result.tier == PIITier.TIER4

    # Non-sensitive
    def test_plain_id_not_sensitive(self):
        col = make_col("id")
        result = self.clf.classify_column(col, "any_table")
        assert result.tier is None

    def test_description_not_sensitive(self):
        col = make_col("description")
        result = self.clf.classify_column(col, "products")
        assert result.tier is None

    def test_created_at_not_sensitive(self):
        col = make_col("created_at")
        result = self.clf.classify_column(col, "orders")
        assert result.tier is None

    # Schema-level classification
    def test_classify_schema(self):
        ddl = """
        CREATE TABLE users (
            id BIGSERIAL PRIMARY KEY,
            email VARCHAR(255),
            salary NUMERIC(18,2),
            religion VARCHAR(100),
            created_at TIMESTAMP
        );
        """
        parser = DDLParser(dialect="postgres")
        schema = parser.parse(ddl)
        results = self.clf.classify_schema(schema)
        sensitive = [r for r in results if r.is_sensitive]
        tiers = {r.tier.value for r in sensitive}
        assert PIITier.TIER1 in tiers   # email
        assert PIITier.TIER3 in tiers   # salary
        assert PIITier.TIER4 in tiers   # religion

    def test_table_sensitivity_annotated(self):
        ddl = "CREATE TABLE t (id INT PRIMARY KEY, email VARCHAR(100));"
        parser = DDLParser(dialect="postgres")
        schema = parser.parse(ddl)
        self.clf.classify_schema(schema)
        tbl = schema.tables[0]
        assert tbl.has_sensitive_data
        assert 1 in tbl.sensitivity_tiers
