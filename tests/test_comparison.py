"""Tests the comparison module"""

from typing import Tuple
from io import StringIO

from tests.fixtures import *
from dbsync import intermediate as IM
from dbsync.comparing.comparison_repo import ComparisonRepo
from dbsync.comparing.comparison import Comparison
from dbsync.settings import Settings
from dbsync.exceptions import DbSyncCompareException


class TestComparison:

    def _make_stage_data(self,
                         table: IM.Table, insert0: IM.Insert, insert1: IM.Insert) -> \
            Tuple[IM.Table, IM.Insert, IM.Insert]:
        stg_name = Settings.obj().dst_prefix + table.name
        stg_table = IM.Table(stg_name, table.columns, table.primary_keys)
        stg_insert0 = IM.Insert(stg_name, insert0.columns, insert0.values)
        col_slc = slice(0, len(table.columns)-1)
        stg_data1 = [c[col_slc] for c in insert1.values]
        stg_insert1 = IM.Insert(stg_name, insert1.columns[col_slc], stg_data1)
        return (stg_table, stg_insert0, stg_insert1)

    # Not applicable any more:
    def no_test_inserts_have_different_columns(self,
                                               table, get_insert_stmt, get_narrow_insert_stmt):
        slc0 = slice(0, DATA_LEN, 2)
        slc1 = slice(1, DATA_LEN, 2)
        insert0 = get_insert_stmt(slc0)
        insert1 = get_narrow_insert_stmt(slc1)
        stg_table, stg_insert0, stg_insert1 = self._make_stage_data(table, insert0, insert1)

        repo = ComparisonRepo()
        repo.append(table)
        repo.append(insert0)
        ##repo.append(insert1)
        repo.append(stg_table)
        repo.append(stg_insert1)
        ##repo.append(stg_insert0)
        repo.post_process()

        fd = StringIO()
        comparison = Comparison(repo, None, fd)
        with pytest.raises(DbSyncCompareException):
            comparison.compare()

    # not applicable any more
    def no_test_unequal_number_of_inserts(self,
                                       table, get_insert_stmt, get_narrow_insert_stmt):
        slc0 = slice(0, DATA_LEN, 2)
        slc1 = slice(1, DATA_LEN, 2)
        insert0 = get_insert_stmt(slc0)
        insert1 = get_narrow_insert_stmt(slc1)
        stg_table, stg_insert0, stg_insert1 = self._make_stage_data(table, insert0, insert1)

        repo = ComparisonRepo()
        repo.append(table)
        repo.append(insert0)
        repo.append(insert1)
        repo.append(stg_table)
        repo.append(stg_insert1)
        #repo.append(stg_insert0)
        repo.post_process()

        fd = StringIO()
        comparison = Comparison(repo, None, fd)
        with pytest.raises(DbSyncCompareException):
            comparison.compare()
