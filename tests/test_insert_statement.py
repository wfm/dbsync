"""Tests the insert_statement module"""

from tests.fixtures import *
from dbsync import intermediate as IM
from dbsync.comparing.comparison_repo import ComparisonRepo

# TODO test insert statements without column list

# copied from https://docs.pytest.org/en/6.2.x/example/parametrize.html
#   #parametrizing-test-methods-through-per-class-configuration
# def pytest_generate_tests(metafunc):
#     # called once per each test function
#     funcarglist = metafunc.cls.params[metafunc.function.__name__]
#     argnames = sorted(funcarglist[0])
#     metafunc.parametrize(
#         argnames,
#         [[funcargs[name] for name in argnames] for funcargs in funcarglist]
#     )


class TestInsertStatment:
    # params = {
    #     "test_normal": [
    #         # src has data, dst does not -> all src data added to dst
    #         dict(
    #             src_sl=slice(0, DATA_LEN),
    #             dst_sl=slice(0, 0),
    #             add_sl=slice(0, DATA_LEN),
    #             upd_sl=slice(0, 0),
    #             src_mod=False,
    #             dst_mod=False
    #         ),
    #     ]
    # }

    def test_normal(self, get_insert_stmt):
        slc = slice(0, 1)
        insert: IM.Insert = get_insert_stmt(slc)
        assert insert.name == TABLE_NAME            # noqa: S101
        assert insert.columns == COLUMN_NAMES       # noqa: S101
        assert insert.values == INSERT_DATA[slc]    # noqa: S101

