"""Tests the ColumnList class"""

import pytest
from dbsync.parsing.sql_statement import SqlStatement
from dbsync.parsing.create_table_statement import ColumnList
import dbsync.intermediate as IM


class TestColumnList:
    def test_single_column(self):
        sql_text = "(`id` bigint not null)"
        ss = SqlStatement(sql_text)

        column_list = ColumnList()
        cols, _ = column_list.get_columns(ss.tl)
        assert isinstance(cols, list), "get_columns should return a list"
        assert len(cols) == 1, "list should have 1 element"
        assert cols[0].name == "id", "column should be named 'id'"
        assert cols[0].datatype == "bigint", "column data type should be bigint"
        assert cols[0].modifiers == "not null", "modifiers should be 'not null'"

    def test_two_columns(self):
        sql_text = """(
  `id` bigint not null,
  `note` varchar(255) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci
)"""
        ss = SqlStatement(sql_text)

        column_list = ColumnList()
        cols, _ = column_list.get_columns(ss.tl)
        assert isinstance(cols, list), "get_columns should return a list"
        assert len(cols) == 2, "list should have 1 element"
        assert cols[0].name == "id", "column should be named 'id'"
        assert cols[0].datatype == "bigint", "column data type should be bigint"
        assert cols[0].modifiers == "not null", "modifiers should be 'not null'"
        assert cols[1].name == "note", "column should be named 'note'"
        assert cols[1].datatype == "varchar(255)", "column data type should be varchar(255)"
        assert cols[1].modifiers == "CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci", \
            "modifiers should be 'CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci'"

    def test_single_column_with_autoinc(self):
        sql_text = "(`id` bigint not null AUTO_INCREMENT)"
        ss = SqlStatement(sql_text)

        column_list = ColumnList()
        cols, _ = column_list.get_columns(ss.tl)
        assert isinstance(cols, list), "get_columns should return a list"
        assert len(cols) == 1, "list should have 1 element"
        assert cols[0].name == "id", "column should be named 'id'"
        assert cols[0].datatype == "bigint", "column data type should be bigint"
        assert cols[0].modifiers == "not null AUTO_INCREMENT", \
            "modifiers should be 'not null AUTO_INCREMENT'"

    @pytest.mark.xfail
    # TODO this one fails because the comma after auto_increment is added to the modifiers
    def test_two_columns_with_autoinc(self):
        sql_text = """(
  `id` bigint not null AUTO_INCREMENT,
  `note` varchar(255) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci
)"""
        ss = SqlStatement(sql_text)

        column_list = ColumnList()
        cols, _ = column_list.get_columns(ss.tl)
        assert isinstance(cols, list), "get_columns should return a list"
        assert len(cols) == 2, "list should have 1 element"
        assert cols[0].name == "id", "column should be named 'id'"
        assert cols[0].datatype == "bigint", "column data type should be bigint"
        assert cols[0].modifiers == "not null AUTO_INCREMENT", \
            "modifiers should be 'not null AUTO_INCREMENT'"
        assert cols[1].name == "note", "column should be named 'note'"
        assert cols[1].datatype == "varchar(255)", "column data type should be varchar(255)"
        assert cols[1].modifiers == "CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci", \
            "modifiers should be 'CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci'"

    @pytest.mark.xfail
    # TODO this one fails because the parser depends on there being a newline
    # at the end of the first column definition
    def test_two_columns_with_autoinc_and_no_whitespace(self):
        sql_text = "(`id` bigint not null AUTO_INCREMENT, \
`note` varchar(255) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci)"
        ss = SqlStatement(sql_text)

        column_list = ColumnList()
        cols, _ = column_list.get_columns(ss.tl)
        assert isinstance(cols, list), "get_columns should return a list"
        assert len(cols) == 2, "list should have 1 element"
        assert cols[0].name == "id", "column should be named 'id'"
        assert cols[0].datatype == "bigint", "column data type should be bigint"
        assert cols[0].modifiers == "not null AUTO_INCREMENT", \
            "modifiers should be 'not null AUTO_INCREMENT'"
        assert cols[1].name == "note", "column should be named 'note'"
        assert cols[1].datatype == "varchar(255)", "column data type should be varchar(255)"
        assert cols[1].modifiers == "CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci", \
            "modifiers should be 'CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci'"

    #
    # Keys
    def test_single_column_with_pk(self):
        sql_text = "(`id` bigint not null, primary key (`id`))"
        ss = SqlStatement(sql_text)

        column_list = ColumnList()
        cols, keys = column_list.get_columns(ss.tl)
        assert isinstance(cols, list), "get_columns should return a list"
        assert len(cols) == 1, "list should have 1 element"
        assert cols[0].name == "id", "column should be named 'id'"
        assert cols[0].datatype == "bigint", "column data type should be bigint"
        assert cols[0].modifiers == "not null", "modifiers should be 'not null'"

        assert len(keys) == 1
        assert keys[0].name == ""
        assert len(keys[0].columns) == 1
        assert keys[0].columns[0].name == "id"
        assert keys[0].columns[0].length is None
        assert keys[0].is_primary
        assert not keys[0].is_unique

    def test_two_columns_with_pk_and_uk(self):
        sql_text = """(
  `id` bigint not null,
  `note` varchar(255) CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci,
  primary key (`id`),
  unique key `my_uk` (`note`(10))
)"""
        ss = SqlStatement(sql_text)

        column_list = ColumnList()
        cols, keys = column_list.get_columns(ss.tl)
        assert isinstance(cols, list), "get_columns should return a list"
        assert len(cols) == 2, "list should have 1 element"
        assert cols[0].name == "id", "column should be named 'id'"
        assert cols[0].datatype == "bigint", "column data type should be bigint"
        assert cols[0].modifiers == "not null", "modifiers should be 'not null'"
        assert cols[1].name == "note", "column should be named 'note'"
        assert cols[1].datatype == "varchar(255)", "column data type should be varchar(255)"
        assert cols[1].modifiers == "CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci", \
            "modifiers should be 'CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci'"

        assert len(keys) == 2
        assert keys[0].name == ""
        assert len(keys[0].columns) == 1
        assert keys[0].columns[0].name == "id"
        assert keys[0].columns[0].length is None
        assert keys[0].is_primary
        assert not keys[0].is_unique

        assert keys[1].name == "my_uk"
        assert len(keys[1].columns) == 1
        assert keys[1].columns[0].name == "note"
        assert keys[1].columns[0].length == 10
        assert keys[1].is_unique
        assert not keys[1].is_primary
