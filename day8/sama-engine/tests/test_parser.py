"""Tests for the DDL parser."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from parser.ddl_parser import DDLParser, SchemaModel, TableModel, ColumnModel


SIMPLE_PG = """
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""

WITH_FK_PG = """
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(18,2) NOT NULL
);
"""

MULTI_TABLE_PG = SIMPLE_PG + WITH_FK_PG


class TestDDLParserPostgres:
    def setup_method(self):
        self.parser = DDLParser(dialect="postgres")

    def test_parse_single_table(self):
        schema = self.parser.parse(SIMPLE_PG)
        assert len(schema.tables) == 1
        assert schema.tables[0].name == "users"

    def test_column_names(self):
        schema = self.parser.parse(SIMPLE_PG)
        tbl = schema.tables[0]
        assert "id" in tbl.column_names
        assert "email" in tbl.column_names
        assert "created_at" in tbl.column_names

    def test_primary_key_detected(self):
        schema = self.parser.parse(SIMPLE_PG)
        tbl = schema.tables[0]
        assert tbl.has_primary_key

    def test_nullable_false_on_not_null(self):
        schema = self.parser.parse(SIMPLE_PG)
        tbl = schema.tables[0]
        email_col = tbl.get_column("email")
        assert email_col is not None
        assert email_col.nullable is False

    def test_foreign_key_cascade(self):
        schema = self.parser.parse(WITH_FK_PG)
        tbl = schema.tables[0]
        fks = tbl.get_foreign_keys()
        assert len(fks) >= 1
        fk = fks[0]
        assert fk.ref_table == "users"
        assert fk.on_delete == "CASCADE"

    def test_multi_table(self):
        schema = self.parser.parse(MULTI_TABLE_PG)
        assert len(schema.tables) == 2
        assert schema.table_names == {"users", "orders"}

    def test_get_table_case_insensitive(self):
        schema = self.parser.parse(SIMPLE_PG)
        assert schema.get_table("USERS") is not None
        assert schema.get_table("users") is not None

    def test_no_pk_table(self):
        ddl = "CREATE TABLE nopk (name VARCHAR(100), value TEXT);"
        schema = self.parser.parse(ddl)
        assert not schema.tables[0].has_primary_key

    def test_table_level_pk(self):
        ddl = """
        CREATE TABLE composite_pk (
            part1 INT,
            part2 INT,
            val TEXT,
            PRIMARY KEY (part1, part2)
        );
        """
        schema = self.parser.parse(ddl)
        assert schema.tables[0].has_primary_key

    def test_empty_ddl(self):
        schema = self.parser.parse("")
        assert schema.tables == []


class TestDDLParserMySQL:
    def setup_method(self):
        self.parser = DDLParser(dialect="mysql")

    def test_mysql_auto_increment(self):
        ddl = """
        CREATE TABLE products (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL
        );
        """
        schema = self.parser.parse(ddl)
        assert len(schema.tables) == 1
        assert schema.tables[0].has_primary_key


class TestDDLParserMSSQL:
    def setup_method(self):
        self.parser = DDLParser(dialect="mssql")

    def test_mssql_identity(self):
        ddl = """
        CREATE TABLE employees (
            id BIGINT IDENTITY(1,1) PRIMARY KEY,
            full_name NVARCHAR(255) NOT NULL
        );
        """
        schema = self.parser.parse(ddl)
        assert len(schema.tables) == 1
        assert schema.tables[0].has_primary_key

    def test_named_fk_constraint(self):
        ddl = """
        CREATE TABLE orders (
            id BIGINT IDENTITY(1,1) PRIMARY KEY,
            customer_id BIGINT NOT NULL,
            CONSTRAINT fk_order_customer FOREIGN KEY (customer_id)
                REFERENCES customers(id) ON DELETE CASCADE
        );
        """
        schema = self.parser.parse(ddl)
        tbl = schema.tables[0]
        fks = tbl.get_foreign_keys()
        cascade_fks = [fk for fk in fks if fk.on_delete == "CASCADE"]
        assert len(cascade_fks) >= 1
