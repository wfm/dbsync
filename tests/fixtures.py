"""Reusable test fixtures"""

import pytest
from typing import Callable

from dbsync import intermediate as IM
from dbsync.comparing.unpacked_insert import UnpackedInsert
from dbsync.settings import Settings


settings = Settings()
settings.update_tables_without_timestamp = True
Settings.obj(settings)
print(f"update_tables_without_timestamp: {Settings.obj().update_tables_without_timestamp}")


TABLE_NAME = Settings.obj().tbl_prefix + "test_table"
COLUMN_NAMES = ["f1", "f2", "f3", "f4"]
PK_COLUMNS = ["f1", "f2"]
# col 0 is an "int" column, which just means that the values
# won't have quotes around them in the sql. The sort order
# is messed up though. I added leading 0s to compensate.
INSERT_DATA = [
    ["01", "'2'", "'3'", "'4'"],
    ["05", "'6'", "'7'", "'8'"],
    ["09", "'a'", "'b'", "'c'"],
    ["13", "'e'", "'f'", "'g'"],
    ["17", "'i'", "'j'", "'k'"],
    ["21", "'m'", "'n'", "'o'"],
    ["25", "'q'", "'r'", "'s'"],
    ["29", "'u'", "'v'", "'w'"]
]
DATA_LEN = len(INSERT_DATA)
MODIFY_DATA = [
    ["01", "'2'", "'A'", "'B'"],
    ["05", "'6'", "'C'", "'D'"],
    ["09", "'a'", "'E'", "'F'"],
    ["13", "'e'", "'G'", "'H'"],
    ["17", "'i'", "'I'", "'J'"],
    ["21", "'m'", "'K'", "'L'"],
    ["25", "'q'", "'M'", "'N'"],
    ["29", "'u'", "'O'", "'P'"]
]


@pytest.fixture(scope="module")
def columns():
    return [
        IM.Column("f1", "int(11)", "NOT NULL DEFAULT '0'"),
        IM.Column("f2", "varchar(20)", "COLLATE utf8mb4_unicode_520_ci NOT NULL"),
        IM.Column("f3", "datetime", "DEFAULT '0000-00-00 00:00:00'"),
        IM.Column("f4", "longtext", "COLLATE utf8mb4_unicode_520_ci")
    ]


@pytest.fixture(scope="module")
def table(columns):
    pk = IM.Key("", [IM.KeyColumn(name) for name in PK_COLUMNS], is_primary=True)
    return IM.Table(TABLE_NAME, columns, keys=[pk])


@pytest.fixture(scope="module")
def get_insert_stmt(table) -> Callable[[slice, bool], IM.Insert]:
    def _get_insert_stmt(slc: slice, use_modify: bool = False) -> IM.Insert:
        if use_modify:
            data = MODIFY_DATA[slc]
        else:
            data = INSERT_DATA[slc]
        return IM.Insert(TABLE_NAME, COLUMN_NAMES, data)

    return _get_insert_stmt


@pytest.fixture(scope="module")
def get_narrow_insert_stmt(table) -> Callable[[slice, bool], IM.Insert]:
    def _get_narrow_insert_stmt(slc: slice, use_modify: bool = False) -> IM.Insert:
        inner_slc = slice(0, len(table.columns)-1)
        if use_modify:
            data = MODIFY_DATA
        else:
            data = INSERT_DATA
        data = [inner[inner_slc] for inner in data[slc]]
        return IM.Insert(TABLE_NAME, COLUMN_NAMES[inner_slc], data)

    return _get_narrow_insert_stmt


@pytest.fixture(scope="module")
def get_unpacked_insert(table, get_insert_stmt) -> Callable[[slice, bool], UnpackedInsert]:
    def _get_unpacked_insert(slc: slice, use_modify: bool) -> UnpackedInsert:
        insert = get_insert_stmt(slc, use_modify)
        return UnpackedInsert(table, insert)

    return _get_unpacked_insert
