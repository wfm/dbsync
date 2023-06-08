from tests.fixtures import *
from dbsync.comparing.compare_insert import CompareInsert


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
                src_mod=DataSources.INSERT,
                dst_mod=DataSources.INSERT
            ),
            # src and dst have same data -> no add or upd needed
            dict(
                src_sl=slice(0, DATA_LEN),
                dst_sl=slice(0, DATA_LEN),
                add_sl=slice(0, 0),
                upd_sl=slice(0, 0),
                src_mod=DataSources.INSERT,
                dst_mod=DataSources.INSERT
            ),
            # src is empty, dst has data -> no add or upd needed
            dict(
                src_sl=slice(0, 0),
                dst_sl=slice(0, DATA_LEN),
                add_sl=slice(0, 0),
                upd_sl=slice(0, 0),
                src_mod=DataSources.INSERT,
                dst_mod=DataSources.INSERT
            ),
            # variation on previous
            dict(
                src_sl=slice(0, DATA_LEN, 2),
                dst_sl=slice(0, DATA_LEN),
                add_sl=slice(0, 0),
                upd_sl=slice(0, 0),
                src_mod=DataSources.INSERT,
                dst_mod=DataSources.INSERT
            ),
            # src has rows not in dst -> adds output for missing rows
            dict(
                src_sl=slice(0, DATA_LEN),
                dst_sl=slice(0, DATA_LEN, 2),
                add_sl=slice(1, DATA_LEN, 2),
                upd_sl=slice(0, 0),
                src_mod=DataSources.INSERT,
                dst_mod=DataSources.INSERT
            ),
            # src has different data from dst -> updates output
            # for now, we output both the src and dst data
            dict(
                src_sl=slice(0, DATA_LEN),
                dst_sl=slice(0, DATA_LEN),
                add_sl=slice(0, 0),
                upd_sl=slice(0, DATA_LEN),
                src_mod=DataSources.MODIFY,
                dst_mod=DataSources.INSERT
            ),
        ],
        "test_insert_diffs": [
            # one insert
            dict(
                src_sl=slice(0, 1),
                dst_sl=slice(0, 0),
                src_mod=DataSources.INSERT,
                dst_mod=DataSources.INSERT,
                expected_sql="""-- Inserting 1 row:
INSERT INTO `NhU_test_table` (`f1`, `f2`, `f3`, `f4`) VALUES
(01, '2', '3', '4');"""
            ),
            # one update
            dict(
                src_sl=slice(4, 5),
                dst_sl=slice(4, 5),
                src_mod=DataSources.MODIFY,
                dst_mod=DataSources.INSERT,
                expected_sql="""-- Updating 1 record:
UPDATE `NhU_test_table`
SET `f3`='I', `f4`='J'
WHERE `f1`=17 AND `f2`='i';"""
            )
        ],
        "test_unique": [
            dict(expected_sql="""-- Inserting 1 record:
INSERT INTO `NhU_test_table` (`f1`, `f2`, `f3`, `f4`) VALUES
(03, 'E', 'F', 'key 1');"""
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
            for zz in zip(actual_data, INSERT_DATA[add_sl], strict=True):
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

    def test_unique(self, expected_sql, get_unpacked_insert, table):
        slc = slice(0, LEN_UNIQ_TEST)
        src = get_unpacked_insert(slc, DataSources.SRC)
        dst = get_unpacked_insert(slc, DataSources.DST)

        print(f"src: {repr(src)}")
        print(f"dst: {repr(dst)}")

        ci = CompareInsert()
        ins_diffs = ci.compare(src, dst, table)
        actual_sql = ins_diffs.generate_sql()
        print("SQL:")
        print(actual_sql)
        assert actual_sql == expected_sql       # noqa: S101
