"""Matches up tables and compares the structure and data"""

from io import TextIOWrapper
import re
from datetime import datetime
from typing import List

from dbsync import intermediate as IM
from dbsync.comparing.comparison_repo import ComparisonRepo
from dbsync.comparing.compare_insert import CompareInsert
from dbsync.comparing.unpacked_insert import UnpackedInsert
from dbsync.settings import Settings


class Comparison:
    def __init__(self,
                 repo: ComparisonRepo,
                 filename: str = None,
                 fd: TextIOWrapper = None) -> None:
        self.repo = repo
        self.filename = filename
        if self.filename is None:
            self.fd = None
        else:
            self.fd = open(filename, mode="w", encoding="utf-8")
            self._write(f"-- dbsync started at {datetime.now()}")

    def _write(self, text: str) -> None:
        if self.fd is None:
            print(text)
        else:
            self.fd.write(text + "\n")

    def _has_method(self, obj: object, name: str):
        x = getattr(obj, name, None)
        return callable(x)

    def _sanity_check(self, pair: tuple) -> None:
        # TODO throw an exception if the columns are different
        pass

    def _pad_inserts(self,
                     src_inserts: List[UnpackedInsert | None],
                     dst_inserts: List[UnpackedInsert | None]) -> None:
        while len(src_inserts) < len(dst_inserts):
            src_inserts.append(None)

        while len(dst_inserts) < len(src_inserts):
            dst_inserts.append(None)

    def output_table(self, table: IM.Table) -> None:
        if not Settings.obj().should_include_table(table.name):
            return

        src_inserts = self.repo.get_inserts(table.name)
        # we don't want to output the table DDL
        # just the insert and update statements
        dst_prefix = Settings.obj().dst_prefix
        dst_regex = re.compile(f"^{dst_prefix}")

        if not dst_regex.search(table.name):
            dst_name = dst_prefix + table.name
            dst = self.repo.get_table(dst_name)
            # dumb: get_table raises an exception if the table doesn't exist
            if dst is not None:
                dst_inserts = self.repo.get_inserts(dst_name)
                # TODO this is too dumb.
                self._pad_inserts(src_inserts, dst_inserts)
                pairs = list(zip(src_inserts, dst_inserts, strict=True))
            else:
                dst = IM.Table(dst_name, table.columns, table.primary_keys)
                sql = dst.generate_sql()
                self._write(sql)
                src_inserts = self.repo.get_inserts(table.name)
                pairs = []
                for i in src_inserts:
                    pairs.append((i, None))

            if len(pairs) > 0:
                self._write(f"-- Prod table {table.name}")
                if dst is not None:
                    self._write(f"-- Staging table {dst_name}")
                else:
                    self._write("-- No staging table found")

                self._write("-- TODO disable pk constraints and auto_increment")
                for p in pairs:
                    self._sanity_check(p)
                    diffs = CompareInsert.compare(p[0], p[1], dst)
                    print(f"{table.name} : {len(diffs.additions)} inserts, {len(diffs.updates)} updates")
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
