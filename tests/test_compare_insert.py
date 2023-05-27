import pytest
from typing import List, Dict, Callable

from dbsync import intermediate as IM
from dbsync.comparing.unpacked_insert import UnpackedInsert
from dbsync.comparing.compare_insert import CompareInsert

TABLE_NAME = "test_table"
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


@pytest.fixture
def columns():
    return [
        IM.Column("f1", "int(11)", "NOT NULL DEFAULT '0'"),
        IM.Column("f2", "varchar(20)", "COLLATE utf8mb4_unicode_520_ci NOT NULL"),
        IM.Column("f3", "datetime", "DEFAULT '0000-00-00 00:00:00'"),
        IM.Column("f4", "longtext", "COLLATE utf8mb4_unicode_520_ci")
    ]


@pytest.fixture
def table(columns):
    return IM.Table(TABLE_NAME, columns, PK_COLUMNS)


@pytest.fixture
def get_unpacked_insert(table) -> Callable[[slice, bool], UnpackedInsert]:
    def _get_unpacked_insert(slc: slice, use_modify: bool) -> UnpackedInsert:
        print(f"_get_unpacked_insert, slice: {slc}, use_modify: {use_modify}")
        if use_modify:
            data = MODIFY_DATA[slc]
        else:
            data = INSERT_DATA[slc]
        print(f"  data: {data}")
        insert = IM.Insert(TABLE_NAME, COLUMN_NAMES, data)
        return UnpackedInsert(table, insert)

    return _get_unpacked_insert


# copied from https://docs.pytest.org/en/6.2.x/example/parametrize.html
#   #parametrizing-test-methods-through-per-class-configuration
def pytest_generate_tests(metafunc):
    # called once per each test function
    funcarglist = metafunc.cls.params[metafunc.function.__name__]
    argnames = sorted(funcarglist[0])
    metafunc.parametrize(
        argnames,
        [[funcargs[name] for name in argnames] for funcargs in funcarglist]
    )


class TestCompareInsert:
    params = {
        "test_normal": [
            # src has data, dst does not -> all src data added to dst
            dict(
                src_sl=slice(0, DATA_LEN),
                dst_sl=slice(0, 0),
                add_sl=slice(0, DATA_LEN),
                upd_sl=slice(0, 0),
                src_mod=False,
                dst_mod=False
            ),
            # src and dst have same data -> no add or upd needed
            dict(
                src_sl=slice(0, DATA_LEN),
                dst_sl=slice(0, DATA_LEN),
                add_sl=slice(0, 0),
                upd_sl=slice(0, 0),
                src_mod=False,
                dst_mod=False
            ),
            # src is empty, dst has data -> no add or upd needed
            dict(
                src_sl=slice(0, 0),
                dst_sl=slice(0, DATA_LEN),
                add_sl=slice(0, 0),
                upd_sl=slice(0, 0),
                src_mod=False,
                dst_mod=False
            ),
            # variation on previous
            dict(
                src_sl=slice(0, DATA_LEN, 2),
                dst_sl=slice(0, DATA_LEN),
                add_sl=slice(0, 0),
                upd_sl=slice(0, 0),
                src_mod=False,
                dst_mod=False
            ),
            # src has rows not in dst -> adds output for missing rows
            dict(
                src_sl=slice(0, DATA_LEN),
                dst_sl=slice(0, DATA_LEN, 2),
                add_sl=slice(1, DATA_LEN, 2),
                upd_sl=slice(0, 0),
                src_mod=False,
                dst_mod=False
            ),
            # src has different data from dst -> updates output
            # for now, we output both the src and dst data
            dict(
                src_sl=slice(0, DATA_LEN),
                dst_sl=slice(0, DATA_LEN),
                add_sl=slice(0, 0),
                upd_sl=slice(0, DATA_LEN),
                src_mod=True,
                dst_mod=False
            ),
        ],
        "test_insert_diffs": [
            # one insert
            dict(
                src_sl=slice(0, 1),
                dst_sl=slice(0, 0),
                src_mod=False,
                dst_mod=False,
                expected_sql="""-- Inserting 1 row:
INSERT INTO `test_table` (f1, f2, f3, f4) VALUES
(01, '2', '3', '4');"""
            ),
            # one update
            dict(
                src_sl=slice(4, 5),
                dst_sl=slice(4, 5),
                src_mod=True,
                dst_mod=False,
                expected_sql="""-- Updating 1 record:
UPDATE `test_table`
SET f3='I', f4='J'
WHERE f1=17 AND f2='i';"""
            )
        ]
    }

    def _pack(self, packed):
        return [list(d.values()) for d in packed]

    def test_normal(self,
                    src_sl, dst_sl, add_sl, upd_sl,
                    src_mod, dst_mod,
                    get_unpacked_insert, table):
        src = get_unpacked_insert(src_sl, src_mod)
        dst = get_unpacked_insert(dst_sl, dst_mod)
        ci = CompareInsert()
        actual = ci.compare(src, dst, table)
        actual_data = self._pack(actual.additions)

        if actual_data != INSERT_DATA[add_sl]:
            for zz in zip(actual_data, INSERT_DATA[add_sl]):
                print(f"act: {zz[0]}, exp: {zz[1]}")

        assert actual_data == INSERT_DATA[add_sl], "actual_data"            # noqa: S101, E501
        if src_mod or dst_mod:
            srcgen = src.values_gen()
            while len(actual.updates) > 0:
                usrc = actual.updates.pop(0)
                rsrc = next(srcgen)
                assert usrc.key == rsrc.key, "keys"                         # noqa: S101, E501
                assert usrc.update_vals == rsrc.update_vals, "update_vals"  # noqa: S101, E501

            srcgen.close()

        else:
            assert len(actual.updates) == 0        # noqa: S101

    def test_insert_diffs(self,
                          src_sl, dst_sl, src_mod, dst_mod, expected_sql,
                          get_unpacked_insert, table):
        src = get_unpacked_insert(src_sl, src_mod)
        dst = get_unpacked_insert(dst_sl, dst_mod)

        print(f"src: {repr(src)}")
        print(f"dst: {repr(dst)}")

        ci = CompareInsert()
        ins_diffs = ci.compare(src, dst, table)
        actual_sql = ins_diffs.generate_sql()
        print("SQL:")
        print(actual_sql)
        assert actual_sql == expected_sql       # noqa: S101
