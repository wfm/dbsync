"""Matches up tables and compares the structure and data"""

import re
from typing import List, Dict
from dataclasses import dataclass, field

from dbsync import intermediate as IM
from dbsync.comparing.comparison_repo import ComparisonRepo
from dbsync.comparing.compare_insert import CompareInsert, InsertDiffs
from dbsync.comparing.unpacked_insert import UnpackedInsert
from dbsync.exceptions import DbSyncCompareException

# In Bluehost's staging scheme, the prod tables
# are copied to tables with the prefix "staging_"
# To keep things simple, we'll always update the
# "staging" tables from the prod tables.
DST_PREFIX = "staging_"
DST_REGEX = re.compile(r"^staging_")


class Comparison:
    def __init__(self, repo: ComparisonRepo, filename: str = None) -> None:
        self.repo = repo
        self.filename = filename
        if self.filename is None:
            self.fd = None
        else:
            self.fd = open(filename, mode="w", encoding="utf-8")
        self.first_table = True
        self.table_seen: Dict[str, bool] = {}

    def _write(self, text: str) -> None:
        if self.fd is None:
            print(text)
        else:
            self.fd.write(text + "\n")

    def _has_method(self, obj: object, name: str):
        x = getattr(obj, name, None)
        return callable(x)

    def _sanity_check(self, pair: tuple) -> None:
        # TODO
        pass

    def output_table(self, table: IM.Table) -> None:
        # we don't want to output the table DDL
        # just the insert and update statements
        if not DST_REGEX.search(table.name):
            self.table_seen[table.name] = True
            self._write(f"-- Prod table {table.name}")
            dst_name = DST_PREFIX + table.name
            dst = self.repo.get_table(dst_name)
            if dst is not None:
                self.table_seen[dst_name] = True
                self._write(f"-- Staging table {dst_name}")
                src_inserts = self.repo.get_inserts(table.name)
                dst_inserts = self.repo.get_inserts(dst_name)
                pairs = list(zip(src_inserts, dst_inserts, strict=True))
            else:
                self._write("-- No staging table found")
                dst = IM.Table(dst_name, table.columns, table.primary_keys)
                sql = dst.generate_sql()
                self._write(sql)
                src_inserts = self.repo.get_inserts(table.name)
                pairs = []
                for i in src_inserts:
                    pairs.append((i, None))

            self._write("-- TODO disable pk constraints and auto_increment")
            for p in pairs:
                self._sanity_check(p)
                diffs = CompareInsert.compare(p[0], p[1], dst)
                sql = diffs.generate_sql()
                self._write(sql)
            self._write("-- TODO enable pk constraints and auto_increment")

    def output_statement(self, statement: IM.Intermediate) -> None:
        if self._has_method(statement, "generate_sql"):
            text = statement.generate_sql()
            self._write(text)

    def compare(self):
        for statement in self.repo:
            if isinstance(statement, IM.Table):
                self.output_table(statement)
            elif isinstance(statement, IM.Insert):
                # we'll output these after the table ddl
                continue
            else:
                self.output_statement(statement)
