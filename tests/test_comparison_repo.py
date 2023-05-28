"""Tests the comparison_repo module"""

from tests.fixtures import *
from dbsync import intermediate as IM
from dbsync.comparing.comparison_repo import ComparisonRepo


class TestComparisonRepo:

    def test_concatenate(self, table, get_insert_stmt):
        slc0 = slice(0, DATA_LEN, 2)
        slc1 = slice(1, DATA_LEN, 2)
        insert0: IM.Insert = get_insert_stmt(slc0)
        insert1: IM.Insert = get_insert_stmt(slc1)

        repo = ComparisonRepo()
        repo.append(table)
        repo.append(insert0)
        repo.append(insert1)
        repo.post_process()
        print(repr(repo))
        ins = repo.get_inserts(insert0.name)
        assert len(ins) == 1
        combined = ins[0].pack()
        assert combined.values == INSERT_DATA