"""Matches up tables and compares the structure and data"""

import re
from io import TextIOWrapper
from datetime import datetime
from typing import Dict, List, Tuple
from operator import attrgetter

from dbsync import intermediate as IM
from dbsync.comparing.comparison_repo import ComparisonRepo
from dbsync.comparing.compare_insert import CompareInsert
from dbsync.comparing.insert_diffs import InsertDiffs
from dbsync.comparing.unpacked_insert import UnpackedInsert
from dbsync.exceptions import DbSyncCompareException
from dbsync.keyzip import keyzip
from dbsync.settings import ForeignKey, Settings, SyncActions, UpdateModes


class Comparison:
    def __init__(self,
                 repo: ComparisonRepo,
                 filename: str = None,
                 fd: TextIOWrapper = None) -> None:
        self.insert_diffs: Dict[str, InsertDiffs] = {}
        self.repo = repo
        self.filename = filename
        if fd is not None:
            self.fd = fd
        elif filename is not None:
            self.fd = open(filename, mode="w", encoding="utf-8")
            self._write_sql(f"-- dbsync started at {datetime.now()}")
            print(f"Comparison started at {datetime.now()}")
        else:
            self.fd = None

    def _write_sql(self, text: str, blank_line: bool = True) -> None:
        prefix = "\n" if blank_line else ""
        if self.fd is None:
            print(prefix + text)
        else:
            self.fd.write(prefix + text + "\n")

    def _print_remark(self, text: str) -> None:
        if Settings.obj().verbose_mode:
            print(text)

    def _has_method(self, obj: object, name: str):
        x = getattr(obj, name, None)
        return callable(x)

    def _pair_inserts(self,
                      src_inserts: List[UnpackedInsert],
                      dst_inserts: List[UnpackedInsert]) \
            -> List[Tuple[IM.Insert, IM.Insert]]:
        # hopefully less dumb:
        pairs = keyzip(src_inserts, dst_inserts, attrgetter("columns"))
        return pairs

    def _output_table(self, table: IM.Table) -> None:
        self._print_remark(f"_output_table({table.name})")
        # we don't want to output the table DDL
        # just the insert and update statements
        if Settings.obj().is_dst_table(table.name):
            self._print_remark("  ...is not a src table")
            # this is not a src table
            return

        if not Settings.obj().should_include_table(table.name):
            self._print_remark(f"\nDO NOT INCLUDE table {table.name}")
            return

        # Get the action. If we skip this table, just return
        action = Settings.obj().get_table_action(table.name)
        if action == SyncActions.DEFAULT:
            self._print_remark(f"\nSKIP table {table.name} by DEFAULT")
            return

        if action == SyncActions.SKIP:
            self._print_remark(f"\nSKIP table {table.name}")
            return

        dst_name = Settings.obj().get_dst_table_name(table.name)
        dst = self.repo.get_table(dst_name)

        if action == SyncActions.COPY:
            self._print_remark(f"\nCOPY table {table.name}")
            if (Settings.obj().has_foreign_keys(table.name)):
                self._print_remark("  WARNING: table has foreign keys that won't be updated")
            self._copy_table(table, dst)
            return

        if action == SyncActions.MERGE:
            self._print_remark(f"\nMERGE table {table.name}")
            update_mode = Settings.obj().get_update_mode(table.name)
            self._print_remark(f"  Update mode is {UpdateModes(update_mode).name}")
            text = "has" if Settings.obj().table_has_timestamp(table.name) else "does not have"
            self._print_remark(f"  Table {text} a timestamp column")
            self._merge_table(table, dst)
            return

        self._print_remark(f"\nNot sure what to do with table {table.name}")

    def _copy_table(self, src: IM.Table, dst: IM.Table) -> None:
        src_inserts = self.repo.get_inserts(src.name)
        pairs = [(si, None) for si in src_inserts]
        self._output_inserts(True, src, dst, pairs)

    def _merge_table(self, src: IM.Table, dst: IM.Table) -> None:
        src_inserts = self.repo.get_inserts(src.name)
        dst_inserts = self.repo.get_inserts(dst.name)
        pairs = self._pair_inserts(src_inserts, dst_inserts)
        self._print_remark(f"  Table {src.name} has {len(pairs)} insert statements")
        if len(pairs) > 0:
            self._output_inserts(False, src, dst, pairs)
        else:
            self._add_to_insert_diffs(dst, InsertDiffs(dst, [], [], f"Table {src.name} has no data"))

    def _add_to_insert_diffs(self, dst: IM.Table, diffs: InsertDiffs):
        base_name = Settings.obj().get_base_table_name(dst.name)
        self.insert_diffs[base_name] = diffs

    def _output_inserts(self,
                        truncate: bool,
                        src: IM.Table,
                        dst: IM.Table,
                        pairs: List[Tuple[IM.Insert, IM.Insert]]) -> None:
        for p in pairs:
            ci = CompareInsert(p[0], src, p[1], dst, self.repo, truncate)
            diffs = ci.compare()
            self._add_to_insert_diffs(dst, diffs)
            self._patch_foreign_keys(diffs, dst, ci)
            ci.close()
            sql_text = diffs.generate_sql()
            if len(sql_text) > 0:
                self._write_sql(f"\n-- Prod table {src.name}")
                if dst is not None:
                    self._write_sql(f"-- Staging table {dst.name}", blank_line=False)
                else:
                    self._write_sql("-- No staging table found", blank_line=False)

                if src.has_autoinc_column():
                    new_autoinc = max(src.get_autoinc_val(), dst.get_autoinc_val())
                    self._write_sql(dst.disable_autoinc(autoinc_val=new_autoinc))

                if truncate:
                    self._write_sql(dst.truncate())

                self._write_sql(sql_text)

                if src.has_autoinc_column():
                    self._write_sql(dst.enable_autoinc(autoinc_val=new_autoinc))

    # TODO what happens with multi-column keys?
    def _patch_foreign_keys(self, diffs: InsertDiffs, dst: IM.Table, ci: CompareInsert) -> None:
        fks = Settings.obj().get_foreign_keys(dst.name)
        for fk in fks:
            sync_action = Settings.obj().get_table_action_from_base_name(fk.dst_table)
            if sync_action == SyncActions.SKIP:
                continue

            ci.debug_print(f"  Patching {fk}")
            if len(fk.dst_table) == 0 or len(fk.dst_column) == 0:
                raise DbSyncCompareException(f"The FK info for {dst.name} is incomplete")

            assert fk.dst_table in self.insert_diffs, \
                f"Need to process {fk.dst_table} before \
{Settings.obj().get_base_table_name(dst.name)}"
            fk_id = self.insert_diffs[fk.dst_table]

            if fk.weak:
                self._patch_weak_fk(diffs, ci, fk, fk_id)
            else:
                self._patch_strong_fk(diffs, ci, fk, fk_id)

    def _patch_strong_fk(self,
                         diffs: InsertDiffs,
                         ci: CompareInsert,
                         fk: ForeignKey,
                         fk_id: InsertDiffs) -> None:
        for add in diffs.additions:
            old_key_val = add.insert_vals[fk.src_column]
            # TODO i thought we were replacing NULL with None
            if old_key_val is not None and \
                    old_key_val.casefold() != "null" \
                    and int(old_key_val) > 0:
                new_key_val = fk_id.find_replacement_key(int(old_key_val))
                if new_key_val != int(old_key_val):
                    ci.debug_print(
                        f"    old: {old_key_val}, new: {new_key_val}")
                    add.insert_vals[fk.src_column] = str(new_key_val)

    def _patch_weak_fk(self,
                       diffs: InsertDiffs,
                       ci: CompareInsert,
                       fk: ForeignKey,
                       fk_id: InsertDiffs) -> None:
        key_regex = Settings.obj().weak_reference_regex
        value_regex = re.compile(r"^(['\"])(\d+)\1$")
        for add in diffs.additions:
            step = 0
            key = add.insert_vals[fk.key_column]
            if key_regex.search(key):
                step = 1
                old_key_val = add.insert_vals[fk.src_column]
                m = value_regex.search(old_key_val)
                if m:
                    old_key_val = m.group(2)
                    step = 2
                    int_old_key = int(old_key_val)
                    if int_old_key > 0:
                        step = 3
                        int_new_key = fk_id.find_replacement_key(int_old_key, weak=True)
                        if int_new_key != int_old_key:
                            step = 4
                            ci.debug_print(
                                f"    key: {key}, old: {old_key_val}, new: {int_new_key} (WEAK)")
                            add.insert_vals[fk.src_column] = str(int_new_key)
            if step > 0 and step < 4:
                ci.debug_print(f"    didn't map key: {key}, value: {old_key_val}, step: {step} (WEAK)")

    def _output_statement(self, statement: IM.Intermediate) -> None:
        if self._has_method(statement, "generate_sql"):
            text = statement.generate_sql()
            self._write_sql(text)

    def compare(self):
        # The only thing we output besides insert and update are a few set statements
        # that occur before the first table definition.
        for statement in self.repo:
            if isinstance(statement, IM.Table) or isinstance(statement, IM.Insert):
                break
            else:
                self._output_statement(statement)

        for table_name in self.repo.get_ordered_tables():
            try:
                self._output_table(self.repo.get_table(table_name))
            except DbSyncCompareException:
                self.repo.dump_everything(table_name)
                raise

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
