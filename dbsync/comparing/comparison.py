"""Matches up tables and compares the structure and data"""

import re
from io import TextIOWrapper
from datetime import datetime
from typing import Dict, List, Tuple
from operator import attrgetter

from dbsync import intermediate as IM
from dbsync.comparing.comparison_repo import ComparisonRepo
from dbsync.comparing.compare_insert import CompareInsert
from dbsync.comparing.unpacked_insert import UnpackedInsert
from dbsync.keyzip import keyzip
from dbsync.settings import Settings, SyncActions


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
            self._write_sql(f"-- dbsync started at {datetime.now()}")
        else:
            self.fd = None

    def _write_sql(self, text: str) -> None:
        if self.fd is None:
            print(text)
        else:
            self.fd.write(text + "\n")

    def _print_remark(self, text: str) -> None:
        if Settings.obj().verbose_mode:
            print(text)

    def _has_method(self, obj: object, name: str):
        x = getattr(obj, name, None)
        return callable(x)

    def _is_dst_table(self, name):
        dst_prefix = Settings.obj().dst_prefix
        return re.search(f"^{dst_prefix}", name)

    def _get_dst_name(self, name):
        dst_prefix = Settings.obj().dst_prefix
        return dst_prefix + name

    def _pair_inserts(self,
                      src_inserts: List[UnpackedInsert],
                      dst_inserts: List[UnpackedInsert]) \
            -> List[Tuple[IM.Insert, IM.Insert]]:
        # hopefully less dumb:
        pairs = keyzip(src_inserts, dst_inserts, attrgetter("columns"))
        return pairs

    def _output_table(self, table: IM.Table) -> None:
        # we don't want to output the table DDL
        # just the insert and update statements
        if self._is_dst_table(table.name):
            # this is not a src table
            return

        if not Settings.obj().should_include_table(table.name):
            self._print_remark(f"DO NOT INCLUDE table {table.name}")
            return

        # Get the action. If we skip this table, just return
        action = Settings.obj().get_table_action(table.name)
        if action == SyncActions.DEFAULT:
            self._print_remark(f"SKIP table {table.name} by DEFAULT")
            return

        if action == SyncActions.SKIP:
            self._print_remark(f"SKIP table {table.name}")
            return

        dst_name = self._get_dst_name(table.name)
        dst = self.repo.get_table(dst_name)

        if action == SyncActions.COPY:
            self._print_remark(f"COPY table {table.name}")
            self._copy_table(table, dst)
            return

        if action == SyncActions.MERGE:
            self._print_remark(f"MERGE table {table.name}")
            self._merge_table(table, dst)
            return

        self._print_remark(f"Not sure what to do with table {table.name}")

    def _copy_table(self, src: IM.Table, dst: IM.Table) -> None:
        src_inserts = self.repo.get_inserts(src.name)
        pairs = [(si, None) for si in src_inserts]
        self._output_inserts(True, src, dst, pairs)

    def _merge_table(self, src: IM.Table, dst: IM.Table) -> None:
        src_inserts = self.repo.get_inserts(src.name)
        dst_inserts = self.repo.get_inserts(dst.name)
        pairs = self._pair_inserts(src_inserts, dst_inserts)
        self._output_inserts(False, src, dst, pairs)

    def _output_inserts(self,
                        truncate: bool,
                        src: IM.Table,
                        dst: IM.Table,
                        pairs: List[Tuple[IM.Insert, IM.Insert]]) -> None:
        for p in pairs:
            diffs = CompareInsert.compare(p[0], p[1], dst)
            sql_text = diffs.generate_sql()
            if len(sql_text) > 0:
                self._write_sql(f"\n\n-- Prod table {src.name}")
                if dst is not None:
                    self._write_sql(f"-- Staging table {dst.name}")
                else:
                    self._write_sql("-- No staging table found")

                new_autoinc = max(src.get_autoinc_val(), dst.get_autoinc_val())
                self._write_sql("")
                self._write_sql(dst.disable_autoinc(autoinc_val=new_autoinc))

                if truncate:
                    self._write_sql("")
                    self._write_sql(dst.truncate())

                self._write_sql("")
                self._write_sql(sql_text)

                self._write_sql("")
                self._write_sql(dst.enable_autoinc(autoinc_val=new_autoinc))

    def _output_statement(self, statement: IM.Intermediate) -> None:
        if self._has_method(statement, "generate_sql"):
            text = statement.generate_sql()
            self._write_sql(text)

    def compare(self):
        for statement in self.repo:
            if isinstance(statement, IM.Table):
                self._output_table(statement)
            elif isinstance(statement, IM.Insert):
                # we'll output these after the table ddl
                continue
            else:
                self._output_statement(statement)

    def write_high_water_marks(self):
        if self.filename is None:
            return False

        hw_filename = self.filename.replace(".sql", "_hw.py")
        if hw_filename == self.filename:
            return False

        with open(hw_filename, mode="w", encoding="utf-8") as stream:
            stream.write(f"# generated by dbsync at {datetime.now()}\n")
            high_water_marks: Dict[str, int] = {}
            for _, table in self.repo.tables.items():
                high_water_marks[table.name] = table.get_autoinc_val()
            stream.write(str(high_water_marks))

        return True
