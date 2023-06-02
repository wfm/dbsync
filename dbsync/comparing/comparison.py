"""Matches up tables and compares the structure and data"""

import re
from io import TextIOWrapper
from datetime import datetime
from typing import List, Tuple
from operator import attrgetter

from dbsync import intermediate as IM
from dbsync.comparing.comparison_repo import ComparisonRepo
from dbsync.comparing.compare_insert import CompareInsert
from dbsync.comparing.unpacked_insert import UnpackedInsert
from dbsync.keyzip import keyzip
from dbsync.settings import Settings


class Comparison:
    def __init__(self,
                 repo: ComparisonRepo,
                 filename: str = None,
                 fd: TextIOWrapper = None) -> None:
        self.repo = repo
        self.filename = filename
        if fd is not None:
            self.fd = fd
        elif filename is not None:
            self.fd = open(filename, mode="w", encoding="utf-8")
            self._write(f"-- dbsync started at {datetime.now()}")
        else:
            self.fd = None

    def _write(self, text: str) -> None:
        if self.fd is None:
            print(text)
        else:
            self.fd.write(text + "\n")

    def _has_method(self, obj: object, name: str):
        x = getattr(obj, name, None)
        return callable(x)

    def _pair_inserts(self,
                      src_inserts: List[UnpackedInsert],
                      dst_inserts: List[UnpackedInsert]) \
            -> List[Tuple[IM.Insert, IM.Insert]]:
        # still dumb, but it works for maryjoya_WPKWA
        # the zip blows up for maryjoya_WP5Z2
        # pairs = list(zip(src_inserts, dst_inserts, strict=True))
        # hopefully less dumb:
        pairs = keyzip(src_inserts, dst_inserts, attrgetter("columns"))
        return pairs

    def output_table(self, table: IM.Table) -> None:
        if not Settings.obj().should_include_table(table.name):
            return

        # we don't want to output the table DDL
        # just the insert and update statements
        dst_prefix = Settings.obj().dst_prefix
        if re.search(f"^{dst_prefix}", table.name):
            # this is not a src table
            return

        src_inserts = self.repo.get_inserts(table.name)
        dst_name = dst_prefix + table.name
        dst = self.repo.get_table(dst_name)
        dst_inserts = self.repo.get_inserts(dst_name)
        pairs = self._pair_inserts(src_inserts, dst_inserts)
        for p in pairs:
            diffs = CompareInsert.compare(p[0], p[1], dst)
            sql = diffs.generate_sql()
            self._write(f"-- Prod table {table.name}")
            if dst is not None:
                self._write(f"-- Staging table {dst_name}")
            else:
                self._write("-- No staging table found")

            self._write(dst.disable_autoinc())
            self._write(sql)
            new_autoinc = max(table.get_autoinc_val(), dst.get_autoinc_val())
            self._write(dst.enable_autoinc(autoinc_val=new_autoinc))

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
