"""PII Classifier — assigns sensitivity tiers to columns based on name patterns.

Tier 1: Directly identifying (name, email, national_id, etc.)
Tier 2: Indirectly identifying (IP, device_id, session_id, etc.)
Tier 3: Financial / regulated (account_number, IBAN, salary, etc.)
Tier 4: PDPL Art.3 sensitive categories (health, religion, biometric, etc.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Optional

import yaml

from parser.ddl_parser import SchemaModel, TableModel, ColumnModel


class PIITier(IntEnum):
    TIER1 = 1   # Directly identifying
    TIER2 = 2   # Indirectly identifying
    TIER3 = 3   # Financial / regulated
    TIER4 = 4   # PDPL Art.3 sensitive


TIER_LABELS: dict[PIITier, str] = {
    PIITier.TIER1: "Directly Identifying",
    PIITier.TIER2: "Indirectly Identifying",
    PIITier.TIER3: "Financial/Regulated",
    PIITier.TIER4: "PDPL Art.3 Sensitive",
}


@dataclass
class ClassificationResult:
    column_name: str
    table_name: str
    tier: Optional[PIITier]
    label: Optional[str]
    matched_pattern: Optional[str]

    @property
    def is_sensitive(self) -> bool:
        return self.tier is not None

    def __repr__(self) -> str:
        if self.tier:
            return (
                f"ClassificationResult({self.table_name}.{self.column_name} → "
                f"Tier {self.tier.value}: {self.label!r}, pattern={self.matched_pattern!r})"
            )
        return f"ClassificationResult({self.table_name}.{self.column_name} → not sensitive)"


class PIIClassifier:
    """Classifies columns in a SchemaModel and annotates them with PII tiers."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        if config_path is None:
            config_path = str(
                Path(__file__).parent.parent / "config" / "default_config.yaml"
            )
        self._patterns: dict[int, list[re.Pattern[str]]] = {}
        self._load_config(config_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify_schema(self, schema: SchemaModel) -> list[ClassificationResult]:
        """Classify all columns in a schema; annotates tables and columns in-place."""
        results: list[ClassificationResult] = []
        for table in schema.tables:
            table_results = self.classify_table(table)
            results.extend(table_results)
        return results

    def classify_table(self, table: TableModel) -> list[ClassificationResult]:
        """Classify all columns of a single table."""
        results: list[ClassificationResult] = []
        for col in table.columns:
            result = self.classify_column(col, table.name)
            results.append(result)
            # Annotate in-place
            col.pii_tier = result.tier.value if result.tier else None
            col.pii_label = result.label
            if result.tier:
                table.sensitivity_tiers.add(result.tier.value)
                table.has_sensitive_data = True
        return results

    def classify_column(
        self, col: ColumnModel, table_name: str = ""
    ) -> ClassificationResult:
        """Classify a single column. Checks tiers in priority order: 4 > 1 > 3 > 2."""
        col_lower = col.name.lower()

        # Check in priority order (most sensitive first)
        for tier in [PIITier.TIER4, PIITier.TIER1, PIITier.TIER3, PIITier.TIER2]:
            tier_int = tier.value
            if tier_int not in self._patterns:
                continue
            for pattern in self._patterns[tier_int]:
                if pattern.search(col_lower):
                    return ClassificationResult(
                        column_name=col.name,
                        table_name=table_name,
                        tier=tier,
                        label=TIER_LABELS[tier],
                        matched_pattern=pattern.pattern,
                    )

        return ClassificationResult(
            column_name=col.name,
            table_name=table_name,
            tier=None,
            label=None,
            matched_pattern=None,
        )

    def get_sensitive_columns(
        self, table: TableModel, tiers: Optional[list[int]] = None
    ) -> list[ColumnModel]:
        """Return columns that match the specified tiers (default: all tiers)."""
        target_tiers = set(tiers) if tiers else {1, 2, 3, 4}
        return [c for c in table.columns if c.pii_tier in target_tiers]

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _load_config(self, config_path: str) -> None:
        with open(config_path, encoding="utf-8") as fh:
            config = yaml.safe_load(fh)

        pii_config = config.get("pii_patterns", {})
        tier_keys = {
            "tier1": PIITier.TIER1,
            "tier2": PIITier.TIER2,
            "tier3": PIITier.TIER3,
            "tier4": PIITier.TIER4,
        }

        for key, tier in tier_keys.items():
            tier_data = pii_config.get(key, {})
            col_patterns: list[str] = tier_data.get("column_patterns", [])
            compiled: list[re.Pattern[str]] = []
            for p in col_patterns:
                # Only match whole underscore-separated segments, never substrings.
                # e.g. pattern "ip" matches "ip_address" and "session_ip" but NOT "description".
                compiled.append(re.compile(rf"(^|_){re.escape(p)}(_|$)", re.IGNORECASE))
            self._patterns[tier.value] = compiled

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------

    def summary(self, results: list[ClassificationResult]) -> dict[str, int]:
        """Return counts per tier."""
        counts: dict[str, int] = {
            "tier1": 0,
            "tier2": 0,
            "tier3": 0,
            "tier4": 0,
            "not_sensitive": 0,
        }
        for r in results:
            if r.tier is None:
                counts["not_sensitive"] += 1
            else:
                counts[f"tier{r.tier.value}"] += 1
        return counts
