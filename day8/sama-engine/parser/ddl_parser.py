"""DDL Parser — converts raw SQL DDL into a structured SchemaModel using sqlglot."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import sqlglot
import sqlglot.expressions as exp

from .dialect import normalize_dialect, to_sqlglot_dialect


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ConstraintModel:
    type: str                          # PRIMARY_KEY, FOREIGN_KEY, UNIQUE, CHECK, NOT_NULL, DEFAULT
    columns: list[str] = field(default_factory=list)
    ref_table: Optional[str] = None
    ref_columns: list[str] = field(default_factory=list)
    on_delete: Optional[str] = None   # CASCADE, RESTRICT, SET NULL, NO ACTION
    on_update: Optional[str] = None
    expression: Optional[str] = None  # raw expression for CHECK / DEFAULT

    def __repr__(self) -> str:
        return (
            f"ConstraintModel(type={self.type!r}, columns={self.columns}, "
            f"ref_table={self.ref_table!r}, on_delete={self.on_delete!r})"
        )


@dataclass
class ColumnModel:
    name: str
    data_type: str                          # normalised lowercase type name
    raw_type: str                           # original type string from DDL
    nullable: bool = True
    default: Optional[str] = None
    constraints: list[ConstraintModel] = field(default_factory=list)

    # Filled by PII classifier later
    pii_tier: Optional[int] = None
    pii_label: Optional[str] = None

    @property
    def is_primary_key(self) -> bool:
        return any(c.type == "PRIMARY_KEY" for c in self.constraints)

    @property
    def is_foreign_key(self) -> bool:
        return any(c.type == "FOREIGN_KEY" for c in self.constraints)

    def __repr__(self) -> str:
        return (
            f"ColumnModel(name={self.name!r}, data_type={self.data_type!r}, "
            f"nullable={self.nullable}, pii_tier={self.pii_tier})"
        )


@dataclass
class TableModel:
    name: str
    schema: Optional[str] = None
    dialect: str = "postgres"
    columns: list[ColumnModel] = field(default_factory=list)
    constraints: list[ConstraintModel] = field(default_factory=list)  # table-level

    # Filled by rules / classifier
    has_sensitive_data: bool = False
    sensitivity_tiers: set[int] = field(default_factory=set)

    @property
    def column_names(self) -> set[str]:
        return {c.name.lower() for c in self.columns}

    @property
    def has_primary_key(self) -> bool:
        # Check column-level PK constraints
        if any(c.is_primary_key for c in self.columns):
            return True
        # Check table-level PK constraints
        return any(c.type == "PRIMARY_KEY" for c in self.constraints)

    def get_column(self, name: str) -> Optional[ColumnModel]:
        name_lower = name.lower()
        return next((c for c in self.columns if c.name.lower() == name_lower), None)

    def get_foreign_keys(self) -> list[ConstraintModel]:
        fks: list[ConstraintModel] = []
        # table-level FKs
        fks.extend(c for c in self.constraints if c.type == "FOREIGN_KEY")
        # column-level FKs
        for col in self.columns:
            fks.extend(c for c in col.constraints if c.type == "FOREIGN_KEY")
        return fks

    def __repr__(self) -> str:
        return (
            f"TableModel(name={self.name!r}, columns={len(self.columns)}, "
            f"sensitivity_tiers={self.sensitivity_tiers})"
        )


@dataclass
class SchemaModel:
    dialect: str
    tables: list[TableModel] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    @property
    def table_names(self) -> set[str]:
        return {t.name.lower() for t in self.tables}

    def get_table(self, name: str) -> Optional[TableModel]:
        name_lower = name.lower()
        return next((t for t in self.tables if t.name.lower() == name_lower), None)

    def __repr__(self) -> str:
        return (
            f"SchemaModel(dialect={self.dialect!r}, "
            f"tables={[t.name for t in self.tables]})"
        )


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class DDLParser:
    """Parse SQL DDL strings into a SchemaModel.

    Usage::

        parser = DDLParser(dialect="postgres")
        schema = parser.parse(ddl_string)
    """

    def __init__(self, dialect: str = "postgres") -> None:
        self.dialect = normalize_dialect(dialect)
        self._sqlglot_dialect = to_sqlglot_dialect(self.dialect)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, ddl: str) -> SchemaModel:
        """Parse a DDL string and return a SchemaModel."""
        schema = SchemaModel(dialect=self.dialect)
        statements = self._parse_statements(ddl, schema)
        for stmt in statements:
            if isinstance(stmt, exp.Create) and stmt.kind == "TABLE":
                try:
                    table = self._extract_table(stmt)
                    if table:
                        schema.tables.append(table)
                except Exception as exc:  # noqa: BLE001
                    schema.parse_errors.append(
                        f"Error parsing table: {exc}"
                    )
        return schema

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_statements(
        self, ddl: str, schema: SchemaModel
    ) -> list[exp.Expression]:
        try:
            return sqlglot.parse(ddl, dialect=self._sqlglot_dialect, error_level=sqlglot.ErrorLevel.WARN)
        except Exception as exc:  # noqa: BLE001
            schema.parse_errors.append(f"Parse error: {exc}")
            return []

    def _extract_table(self, stmt: exp.Create) -> Optional[TableModel]:
        table_expr = stmt.find(exp.Table)
        if not table_expr:
            return None

        table_name = table_expr.name
        schema_name = table_expr.db or None

        table = TableModel(
            name=table_name,
            schema=schema_name,
            dialect=self.dialect,
        )

        schema_def = stmt.find(exp.Schema)
        if not schema_def:
            return table

        for item in schema_def.expressions:
            if isinstance(item, exp.ColumnDef):
                col = self._extract_column(item)
                table.columns.append(col)
            elif isinstance(item, (
                exp.PrimaryKey,
                exp.ForeignKey,
                exp.UniqueColumnConstraint,
                exp.CheckColumnConstraint,
            )):
                constraints = self._extract_table_constraint(item)
                table.constraints.extend(constraints)
            elif isinstance(item, exp.Constraint):
                constraints = self._extract_named_constraint(item)
                table.constraints.extend(constraints)

        return table

    def _extract_column(self, col_def: exp.ColumnDef) -> ColumnModel:
        col_name = col_def.name
        raw_type = ""
        data_type = ""

        dtype_expr = col_def.find(exp.DataType)
        if dtype_expr:
            raw_type = dtype_expr.sql(dialect=self._sqlglot_dialect)
            data_type = self._normalise_type(dtype_expr)

        col = ColumnModel(name=col_name, data_type=data_type, raw_type=raw_type)

        for constraint in col_def.constraints:
            self._apply_column_constraint(col, constraint)

        return col

    def _normalise_type(self, dtype_expr: exp.DataType) -> str:
        """Return a lowercase type name using the dialect-specific SQL output.

        sqlglot normalises some dialect-specific types internally (e.g. PostgreSQL
        BYTEA → VARBINARY), so we derive the canonical name from the rendered SQL
        rather than from the internal DataType.Type enum.
        """
        # Use the dialect-specific SQL render — this preserves BYTEA for postgres,
        # VARBINARY for MySQL/MSSQL, etc.
        raw_sql = dtype_expr.sql(dialect=self._sqlglot_dialect)
        # Strip length/precision qualifiers: VARCHAR(255) → varchar
        base = raw_sql.split("(")[0].strip().lower()
        # Normalise aliases
        _aliases = {
            "bool": "boolean",
            "int2": "smallint",
            "int4": "int",
            "int8": "bigint",
            "serial": "int",
            "bigserial": "bigint",
            "smallserial": "smallint",
            "character varying": "varchar",
            "character": "char",
            "double precision": "double",
            "timestamp with time zone": "timestamptz",
            "timestamp without time zone": "timestamp",
        }
        return _aliases.get(base, base)

    def _apply_column_constraint(
        self, col: ColumnModel, constraint: exp.ColumnConstraint
    ) -> None:
        kind = constraint.kind
        if isinstance(kind, exp.NotNullColumnConstraint):
            col.nullable = False
        elif isinstance(kind, exp.PrimaryKeyColumnConstraint):
            col.nullable = False
            col.constraints.append(ConstraintModel(type="PRIMARY_KEY", columns=[col.name]))
        elif isinstance(kind, exp.UniqueColumnConstraint):
            col.constraints.append(ConstraintModel(type="UNIQUE", columns=[col.name]))
        elif isinstance(kind, exp.DefaultColumnConstraint):
            col.default = kind.this.sql(dialect=self._sqlglot_dialect) if kind.this else None
        elif isinstance(kind, exp.Reference):
            fk = self._extract_references(col.name, kind)
            col.constraints.append(fk)
        elif isinstance(kind, exp.CheckColumnConstraint):
            col.constraints.append(
                ConstraintModel(
                    type="CHECK",
                    columns=[col.name],
                    expression=kind.this.sql() if kind.this else None,
                )
            )
        elif isinstance(kind, exp.AutoIncrementColumnConstraint):
            pass  # just informational
        elif isinstance(kind, exp.GeneratedAsIdentityColumnConstraint):
            pass

    def _extract_references(
        self, col_name: str, ref_expr: exp.Reference
    ) -> ConstraintModel:
        # The referenced table/columns are in ref_expr.this (a Schema node)
        schema_node = ref_expr.this
        ref_table_name = None
        ref_cols: list[str] = []
        if schema_node:
            tbl = schema_node.find(exp.Table)
            ref_table_name = tbl.name if tbl else None
            ref_cols = [id_.this for id_ in schema_node.expressions
                        if isinstance(id_, exp.Identifier)]

        # ON DELETE / ON UPDATE are stored as strings in ref_expr.args['options']
        on_delete = None
        on_update = None
        options: list[str] = ref_expr.args.get("options") or []
        for opt in options:
            opt_upper = opt.upper()
            if "ON DELETE" in opt_upper:
                on_delete = self._parse_referential_action(opt_upper)
            elif "ON UPDATE" in opt_upper:
                on_update = self._parse_referential_action(opt_upper)

        return ConstraintModel(
            type="FOREIGN_KEY",
            columns=[col_name],
            ref_table=ref_table_name,
            ref_columns=ref_cols,
            on_delete=on_delete,
            on_update=on_update,
        )

    def _parse_referential_action(self, raw: str) -> str:
        raw = raw.upper()
        if "CASCADE" in raw:
            return "CASCADE"
        if "SET NULL" in raw:
            return "SET NULL"
        if "SET DEFAULT" in raw:
            return "SET DEFAULT"
        if "NO ACTION" in raw:
            return "NO ACTION"
        if "RESTRICT" in raw:
            return "RESTRICT"
        return raw.strip()

    def _extract_table_constraint(
        self, item: exp.Expression
    ) -> list[ConstraintModel]:
        if isinstance(item, exp.PrimaryKey):
            cols = [c.name for c in item.find_all(exp.Column)]
            return [ConstraintModel(type="PRIMARY_KEY", columns=cols)]

        if isinstance(item, exp.ForeignKey):
            # Column list is the direct identifiers on this FK node
            cols = [id_.this for id_ in item.expressions
                    if isinstance(id_, exp.Identifier)]
            if not cols:
                cols = [c.name for c in item.find_all(exp.Column)]

            ref = item.find(exp.Reference)
            ref_table_name = None
            ref_cols: list[str] = []
            on_delete = None
            on_update = None
            if ref:
                schema_node = ref.this
                if schema_node:
                    tbl = schema_node.find(exp.Table)
                    ref_table_name = tbl.name if tbl else None
                    ref_cols = [id_.this for id_ in schema_node.expressions
                                if isinstance(id_, exp.Identifier)]
                # options list contains "ON DELETE CASCADE" etc.
                options: list[str] = ref.args.get("options") or []
                for opt in options:
                    opt_upper = opt.upper()
                    if "ON DELETE" in opt_upper:
                        on_delete = self._parse_referential_action(opt_upper)
                    elif "ON UPDATE" in opt_upper:
                        on_update = self._parse_referential_action(opt_upper)
                # Fallback: scan raw SQL
                if on_delete is None:
                    raw_sql = ref.sql(dialect=self._sqlglot_dialect).upper()
                    if "ON DELETE CASCADE" in raw_sql:
                        on_delete = "CASCADE"
                    elif "ON DELETE SET NULL" in raw_sql:
                        on_delete = "SET NULL"
                    elif "ON DELETE RESTRICT" in raw_sql:
                        on_delete = "RESTRICT"
                    elif "ON DELETE NO ACTION" in raw_sql:
                        on_delete = "NO ACTION"

            return [
                ConstraintModel(
                    type="FOREIGN_KEY",
                    columns=cols,
                    ref_table=ref_table_name,
                    ref_columns=ref_cols,
                    on_delete=on_delete,
                    on_update=on_update,
                )
            ]

        if isinstance(item, exp.UniqueColumnConstraint):
            cols = [c.name for c in item.find_all(exp.Column)]
            return [ConstraintModel(type="UNIQUE", columns=cols)]

        if isinstance(item, exp.CheckColumnConstraint):
            return [ConstraintModel(type="CHECK", expression=item.this.sql() if item.this else None)]

        return []

    def _extract_named_constraint(self, item: exp.Constraint) -> list[ConstraintModel]:
        """Handle CONSTRAINT name PRIMARY KEY (...) / FOREIGN KEY (...) forms."""
        constraints: list[ConstraintModel] = []
        for expr in item.expressions:
            constraints.extend(self._extract_table_constraint(expr))
        # If nothing extracted, try FK pattern in raw SQL
        if not constraints:
            raw = item.sql(dialect=self._sqlglot_dialect)
            constraints.extend(self._parse_raw_fk(raw))
        return constraints

    def _parse_raw_fk(self, raw: str) -> list[ConstraintModel]:
        """Fallback regex-based FK extraction for edge cases."""
        results: list[ConstraintModel] = []
        pattern = re.compile(
            r"FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+(\w+)\s*\(([^)]+)\)"
            r"(?:\s+ON\s+DELETE\s+(CASCADE|RESTRICT|SET\s+NULL|NO\s+ACTION))?",
            re.IGNORECASE,
        )
        for m in pattern.finditer(raw):
            cols = [c.strip() for c in m.group(1).split(",")]
            ref_table = m.group(2).strip()
            ref_cols = [c.strip() for c in m.group(3).split(",")]
            on_delete = m.group(4).upper().replace("  ", " ") if m.group(4) else None
            results.append(
                ConstraintModel(
                    type="FOREIGN_KEY",
                    columns=cols,
                    ref_table=ref_table,
                    ref_columns=ref_cols,
                    on_delete=on_delete,
                )
            )
        return results
