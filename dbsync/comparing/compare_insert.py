"""Compares data between the prod and staging databases"""

from io import TextIOWrapper
import os
import re
from typing import Any, List, Dict, Tuple

from dbsync.comparing.insert_diffs import InsertDiffs, RowData
from dbsync import intermediate as IM
from dbsync.comparing.unpacked_insert import UnpackedInsert, InsertRecord
from dbsync.settings import Settings


class CompareInsert:
    """
    Compares the values in two insert statements and generates
    lists of data to be inserted and updated in the dst table
    to make it equivalent to the src table.
    """
    class Generator:
        """Decorates an UnpackedInsert generator"""
        def __init__(self, ui: UnpackedInsert):
            ui.sort()
            self.gen = ui.values_gen()
            self.is_open = True

        def get_next_item(self) -> InsertRecord | None:
            """Gets the next item from the generator"""
            item = None
            if self.is_open:
                try:
                    item = next(self.gen)
                except StopIteration:
                    self.is_open = False
                    self.gen.close()

            return item

    def __init__(self,
                 src: UnpackedInsert | None,
                 src_table: IM.Table,
                 dst: UnpackedInsert | None,
                 dst_table: IM.Table,
                 are_copying: bool = False) -> InsertDiffs:
        self.src = src
        self.src_table = src_table
        self.dst = dst
        self.dst_table = dst_table
        # if true, reuse PKs on inserts
        self.are_copying = are_copying

        self.debug_mode = Settings.obj().debug_mode
        self.debug_file = self._create_debug_file()

        if self.src is not None:
            self.srcgen = CompareInsert.Generator(self.src)

        if self.dst is None:
            self.dstgen = None
        else:
            self.dstgen = CompareInsert.Generator(self.dst)

        self.add: List[RowData] = []
        self.update: List[InsertRecord] = []

    def _create_debug_file(self) -> TextIOWrapper | None:
        if self.debug_mode:
            debug_filename = f"{Settings.obj().get_base_table_name(self.src.name)}-debug.txt"
            output_dir = os.path.dirname(Settings.obj().output_file)
            debug_path = os.path.join(output_dir, "debug")
            if not os.path.exists(debug_path):
                os.makedirs(debug_path)
            full_path = os.path.join(debug_path, debug_filename)
            debug_file = open(full_path, "w", encoding="utf8")
            return debug_file
        return None

    def _debug_print(self, obj: Any) -> None:
        if self.debug_mode:
            self.debug_file.write(str(obj))

    def _verbose_print(self, msg):
        if Settings.obj().verbose_mode:
            print(msg)

    def compare(self):
        if self.src is None:
            return InsertDiffs(self.dst_table, [], [])
        src_item = self.srcgen.get_next_item()
        if self.dstgen is not None:
            dst_item = self.dstgen.get_next_item()

        while self.srcgen.is_open:
            if self.dstgen is None or not self.dstgen.is_open or src_item.key < dst_item.key:
                # if dst is closed, copy remaining records from src into dst
                # if src key < dst key, insert this record into dst
                if self.debug_mode:
                    if self.dstgen is None or not self.dstgen.is_open:
                        dst_key = "None"
                    else:
                        dst_key = dst_item.key
                    self._debug_print(f"< {src_item.key}  {dst_key} => INSERT src record")
                    # hwm = Settings.obj().get_high_water(self.src_table.name)
                    # print(f"  hwm: {hwm}, pk: {src_item.pk}")

                self._append_insert_vals(src_item.insert_vals)
                src_item = self.srcgen.get_next_item()
            elif src_item.key > dst_item.key:
                # skip over dst records until we "catch up"
                if self.debug_mode:
                    self._debug_print(f"> {src_item.key}  {dst_item.key} => SKIP dst")

                dst_item = self.dstgen.get_next_item()
            elif src_item.insert_vals == dst_item.insert_vals:
                # records are the same
                # if self.debug_mode:
                #     self._debug_print(f"= {src_item.key}  {dst_item.key} => SKIP")

                src_item = self.srcgen.get_next_item()
                dst_item = self.dstgen.get_next_item()
            else:
                # the keys are the same but the data is different
                # use the timestamp columns to determine which rows to update
                self._compare_update(src_item, dst_item)

                src_item = self.srcgen.get_next_item()
                dst_item = self.dstgen.get_next_item()

        return InsertDiffs(self.dst_table, self.add, self.update)

    def _compare_update(self, src_item, dst_item):
        updated = False
        do_update, maybe_update, msg = self._should_update(src_item, dst_item)
        cols = []  # TODO temp
        if do_update:
            # TODO use separate InsertRecord and UpdateRecord?
            update_vals, old_vals = self._update_only_necessary_cols(src_item, dst_item)
            cols = list(update_vals.keys())   # TODO temp
            if len(update_vals) > 0:
                updated = True
                self.update.append(
                    InsertRecord(
                        src_item.key,
                        None,
                        src_item.key_vals,
                        update_vals,
                        src_item.pk, src_item.is_unique,
                        msg))

        if self.debug_mode:
            self._debug_print(f"{'U' if updated else 'X'} {src_item.key}  {dst_item.key} => {cols}")
            self._debug_print(msg)

            if not updated:
                update_vals, old_vals = self._update_only_necessary_cols(src_item, dst_item)
            if "meta_value" in update_vals:
                update_vals["meta_value"] = update_vals["meta_value"][0:50]
            self._debug_print("NEW:")
            self._debug_print(update_vals)
            self._debug_print(80 * '-')
            if "meta_value" in old_vals:
                old_vals["meta_value"] = old_vals["meta_value"][0:50]
            self._debug_print("OLD:")
            self._debug_print(old_vals)
            self._debug_print(80 * '=')

    def _append_insert_vals(self, insert_vals: Dict[str, str]) -> RowData:
        """Updates the PK, if necessary, and appends the record to the add list."""
        if self.are_copying or not self.dst_table.has_autoinc_column():
            _, old_pk_val = self._get_old_pk_val(insert_vals)
            rd = RowData(insert_vals, int(old_pk_val), int(old_pk_val))
        else:
            rd = self._update_pk(insert_vals)

        self.add.append(rd)

    def _get_old_pk_val(self, insert_vals: Dict[str, str]) -> Tuple[str, str]:
        """Returns the current PK in a row to be inserted"""
        pk_name = self.dst_table.get_primary_key().get_column_names()
        assert len(pk_name) == 1, "Expected 1 PK column name"
        pk_name = pk_name[0]
        old_pk_val = insert_vals[pk_name]
        return pk_name, old_pk_val

    def _update_pk(self, insert_vals: Dict[str, str]) -> RowData:
        """Assigns a new PK value to an inserted record"""
        new_pk_val = str(self.dst_table.next_autoinc_val())
        pk_name, old_pk_val = self._get_old_pk_val(insert_vals)
        insert_vals[pk_name] = new_pk_val
        self._verbose_print(f"  Assigned new PK to column {pk_name}, \
old: {old_pk_val}, new: {new_pk_val}")

        # Update URLs with the id in them
        # e.g., https://maryjoyart.com/?p=1712
        # TODO use "special rules"
        pk_re = re.compile(r"(([?&]|&#03f;|&#038;)\w+=)" + old_pk_val + r"\b", flags=re.IGNORECASE)
        repl = r"\g<1>" + new_pk_val
        for k, v in insert_vals.items():
            new_v, num = pk_re.subn(repl, v)
            if num > 0:
                self._verbose_print(f"    Updated PK {num} times in column {k}")
                insert_vals[k] = new_v
        return RowData(insert_vals, int(new_pk_val), int(old_pk_val))

    _time_regex = re.compile(r"^(['\"])\d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2}\1$")

    def _should_update(self,
                       src_item: InsertRecord,
                       dst_item: InsertRecord) -> Tuple[bool, bool, str]:
        """Tries to figure out whether a record should be updated"""
        if self.dst_table.timestamp_columns is None or \
                len(self.dst_table.timestamp_columns) == 0:
            return self._pk_should_update(src_item, dst_item)
        return self._time_should_update(src_item, dst_item)

    def _pk_should_update(self,
                          src_item: InsertRecord,
                          dst_item: InsertRecord) -> Tuple[bool, bool, str]:
        """
        Uses PKs to decide if a record should be updated.
        We can only guess...
        """
        do_update = False
        maybe_update = False
        msg = ""
        if len(src_item.pk) > 1:
            print(f"*** multi-column PK: {src_item.pk}")

        if not self.src_table.has_autoinc_column():
            msg = "No auto-increment on this table"
            return do_update, maybe_update, msg

        # Here is where it might be good to know the autoinc_val
        # when the staging tables were created.
        hwm = Settings.obj().get_high_water(self.src_table.name)
        src_end = self.src_table.get_starting_autoinc_val()
        src_pk_val = int(src_item.pk[0])
        dst_end = self.dst_table.get_starting_autoinc_val()
        dst_pk_val = int(dst_item.pk[0])

        if src_pk_val == dst_pk_val:
            msg = "PKs are equal, MAYBE update"
            do_update = True
            maybe_update = True
        elif dst_pk_val > src_end:
            msg = "dst record is more recent, don't update"
        else:
            do_update = True
            msg = "src record is possibly more recent, update"

        if self.debug_mode:
            extra = f" - hwm: {hwm}, src: {[src_end, src_pk_val]} > \
dst: {[dst_end, dst_pk_val]} => {do_update}"
            self._verbose_print(f"  comparing PKs {extra}")
            msg += extra
        return do_update, maybe_update, msg

    def _time_should_update(self,
                            src_item: InsertRecord,
                            dst_item: InsertRecord) -> Tuple[bool, bool, str]:
        """
        Uses timestamp data to decide if a record should be updated.
        This should be exact.
        """
        do_update = False
        msg = ""
        src_times = self._get_column_values(src_item.insert_vals, self.dst_table.timestamp_columns)
        dst_times = self._get_column_values(dst_item.insert_vals, self.dst_table.timestamp_columns)
        try:
            src = next(filter(CompareInsert._time_regex.match, src_times))
            dst = next(filter(CompareInsert._time_regex.match, dst_times))

            do_update = src >= dst  # TODO is it ok to compare strings here?
            msg = ("" if do_update else "DO NOT ") + "Update dst"
        except StopIteration:
            msg = "*** Time comparison raised StopIteration ***"
            print(msg)

        return do_update, False, msg

    @classmethod
    def _get_column_values(cls, vals: Dict[str, str], cols: List[str]):
        """Returns a subset of the data with the specified columns"""
        return [vals[col] for col in cols if col in vals]
        # This could be a comprehension:
        # result = []
        # for col in cols:
        #     if col in vals:
        #         result.append(vals[col])
        # return result

    def _update_only_necessary_cols(self,
                                    src_item: InsertRecord,
                                    dst_item: InsertRecord) -> \
            Tuple[Dict[str, str], Dict[str, str]]:
        """Returns just the set of columns in the update_vals that should be updated."""
        update_vals: Dict[str, str] = {}
        old_vals: Dict[str, str] = {}
        # don't update PK columns
        pk_columns = self.dst_table.get_primary_key().get_column_names()
        for col, src_val in src_item.update_vals.items():
            if col not in pk_columns:
                dst_val = dst_item.update_vals[col]
                if src_val != dst_val:
                    update_vals[col] = src_val
                    old_vals[col] = dst_val
        return update_vals, old_vals
