"""Dialect normalization and DB-specific helpers."""

from __future__ import annotations

SUPPORTED_DIALECTS = {"postgres", "mysql", "mssql"}

_ALIASES: dict[str, str] = {
    "postgresql": "postgres",
    "pg": "postgres",
    "mariadb": "mysql",
    "sqlserver": "mssql",
    "sql_server": "mssql",
    "tsql": "mssql",
    "ms_sql": "mssql",
}

# Maps internal dialect name → sqlglot dialect name
_SQLGLOT_DIALECT_MAP: dict[str, str] = {
    "postgres": "postgres",
    "mysql": "mysql",
    "mssql": "tsql",
}

# Canonical encrypted column types per dialect
ENCRYPTED_TYPES: dict[str, set[str]] = {
    "postgres": {"bytea"},
    "mysql": {"varbinary", "blob", "longblob", "mediumblob", "tinyblob"},
    "mssql": {"varbinary"},
}

# Timestamp-like types per dialect
TIMESTAMP_TYPES: dict[str, set[str]] = {
    "postgres": {"timestamp", "timestamptz", "timestamp with time zone",
                 "timestamp without time zone", "date", "time"},
    "mysql": {"timestamp", "datetime", "date", "time", "year"},
    "mssql": {"datetime", "datetime2", "smalldatetime", "date", "time",
               "datetimeoffset"},
}

# Boolean-like types per dialect
BOOL_TYPES: dict[str, set[str]] = {
    "postgres": {"boolean", "bool"},
    "mysql": {"tinyint", "boolean", "bool", "bit"},
    "mssql": {"bit", "tinyint"},
}

# Integer-like types (common across dialects)
INTEGER_TYPES: set[str] = {
    "int", "integer", "bigint", "smallint", "tinyint",
    "serial", "bigserial", "smallserial", "identity",
    "int2", "int4", "int8",
}

# String-like types
STRING_TYPES: set[str] = {
    "varchar", "nvarchar", "char", "nchar", "text",
    "tinytext", "mediumtext", "longtext", "clob",
    "character varying", "character", "sysname",
}


def normalize_dialect(dialect: str) -> str:
    """Normalize user-supplied dialect string to a canonical internal name."""
    d = dialect.strip().lower()
    d = _ALIASES.get(d, d)
    if d not in SUPPORTED_DIALECTS:
        raise ValueError(
            f"Unsupported dialect '{dialect}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_DIALECTS))}"
        )
    return d


def to_sqlglot_dialect(dialect: str) -> str:
    """Return the sqlglot dialect identifier for the given internal dialect."""
    return _SQLGLOT_DIALECT_MAP[normalize_dialect(dialect)]


def is_encrypted_type(col_type: str, dialect: str) -> bool:
    return col_type.lower() in ENCRYPTED_TYPES.get(dialect, set())


def is_timestamp_type(col_type: str, dialect: str) -> bool:
    return col_type.lower() in TIMESTAMP_TYPES.get(dialect, set())


def is_bool_type(col_type: str, dialect: str) -> bool:
    return col_type.lower() in BOOL_TYPES.get(dialect, set())
