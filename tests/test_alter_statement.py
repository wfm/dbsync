"""Tests ALTER TABLE parsing"""

from tests.fixtures import *
from dbsync import intermediate as IM
from dbsync.comparing.comparison_repo import ComparisonRepo
from dbsync.parsing.statement_processor import process_statements
from dbsync.settings import Settings


class TestAlterStatement:
    def test_add_primary_key(self, table: IM.Table):
        table.keys = []
        repo = ComparisonRepo()
        repo.append(table)

        sql = [
            f"USE `{Settings.obj().db_name}`",
            f"""ALTER TABLE `{table.name}`
  ADD PRIMARY KEY (`f1`, `f2`);"""
        ]

        process_statements(sql, Settings.obj().db_name, repo)
        repo.post_process()

        assert len(repo.parsed) == 3, "Repo should have 3 SQL statements"
        assert isinstance(repo.parsed[2], IM.KeyList), "Repo should have a PK"
        assert table.keys[0].is_primary
        actual_names = [c.name for c in table.keys[0].columns]
        assert actual_names == PK_COLUMNS, "PK columns should match"

    def test_add_multiple_keys(self, table: IM.Table):
        expected = IM.KeyList(table.name, [
            IM.Key("", [
                IM.KeyColumn("f1"),
                IM.KeyColumn("f2")
            ], True, False),
            IM.Key("f1_key", [
                IM.KeyColumn("f1")
            ], False, False),
            IM.Key("f3f4_key", [
                IM.KeyColumn("f3", 20),
                IM.KeyColumn("f4")
            ], False, True)
        ])

        table.keys = []
        repo = ComparisonRepo()
        repo.append(table)

        sql = [
            f"USE `{Settings.obj().db_name}`",
            f"""ALTER TABLE `{table.name}`
  ADD PRIMARY KEY (`f1`, `f2`),
  ADD KEY `f1_key` (`f1`),
  ADD UNIQUE KEY `f3f4_key` (`f3`(20), `f4`);"""
        ]

        process_statements(sql, Settings.obj().db_name, repo)
        repo.post_process()

        assert len(repo.parsed) == 3, "Repo should have 3 SQL statements"
        assert isinstance(repo.parsed[2], IM.KeyList), "Repo should have a PK"
        assert table.keys == expected.keys

    def test_modify_column(self, table: IM.Table):
        repo = ComparisonRepo()
        repo.append(table)

        sql = [
            f"USE `{Settings.obj().db_name}`",
            f"""ALTER TABLE `{table.name}`
  MODIFY `f1` bigint UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=999;"""
        ]

        process_statements(sql, Settings.obj().db_name, repo)
        repo.post_process()

        assert len(repo.parsed) == 3, "Repo should have 3 SQL statements"
        assert isinstance(repo.parsed[2], IM.Modification), "Repo should have a Modification"
        print(f"Modify: {repr(repo.parsed[2])}")
        col = table.get_column("f1")
        print(f"f1: {repr(col)}")
        col = table._get_autoinc_column()
        assert col is not None, "Table should have an auto-inc column"
        assert col.name == "f1", "f1 should be auto-inc column"
        assert table.get_autoinc_val() == 999, "Auto-inc value should be 999"
