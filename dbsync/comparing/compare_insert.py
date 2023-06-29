"""Compares data between the prod and staging databases"""

import os
import re
from bisect import bisect_left
from io import TextIOWrapper
from typing import Any, Dict, List, Tuple

from dbsync import intermediate as IM
from dbsync.comparing.comparison_repo import ComparisonRepo
from dbsync.comparing.insert_diffs import InsertDiffs, RowData
from dbsync.comparing.unpacked_insert import InsertRecord, UnpackedInsert
from dbsync.exceptions import DbSyncCompareException
from dbsync.settings import UpdateActions, Settings, UpdateModes


class CompareInsert:
    """
    Compares the values in two insert statements and generates
    lists of data to be inserted and updated in the dst table
    to make it equivalent to the src table.
    """
    class Generator:
        """Decorates an UnpackedInsert generator"""
        def __init__(self, ui: UnpackedInsert):
            self.is_open = ui is not None
            if self.is_open:
                ui.sort()
                self.gen = ui.values_gen()

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
                 repo: ComparisonRepo,
                 are_copying: bool = False) -> InsertDiffs:
        self.src = src
        self.src_table = src_table
        self.dst = dst
        self.dst_table = dst_table
        self.repo = repo
        # if true, reuse PKs on inserts
        self.are_copying = are_copying

        self.debug_mode = Settings.obj().debug_mode
        self.debug_file = self._create_debug_file()

        if self.debug_mode:
            self.debug_print(f"Comparing insert for {self.dst_table.name}")

        self.dst_autoinc = []
        if self.dst is not None:
            self.dst_autoinc = \
                [item.autoinc for item in self.dst.values_gen() if item.autoinc is not None]
            self.dst_autoinc.sort()

        self.dst_table_has_autoinc_column = self.dst_table.has_autoinc_column()
        if self.dst_table_has_autoinc_column:
            start = self.dst_table.get_starting_autoinc_val()
            curr = self.dst_table.get_autoinc_val()
            highest = self.dst_autoinc[-1] if len(self.dst_autoinc) > 0 else -1
            self.debug_print(f"  autoinc before - starting: {start}, current: {curr}, highest: {highest}")

        self.max_src_autoinc = -1

        self.should_insert_pk = Settings.obj().get_should_insert_pk(self.src_table.name)

        if src is not None:
            table_name = self.src_table.name
            msg = f"  Comparison key is {'unique' if self.src.is_unique else 'primary'} key. \
Key column(s): {self.src.key_column_names}"
            self._verbose_print(msg)
            
            has_timestamp = Settings.obj().table_has_timestamp(table_name)
            self.check_fk_timestamps = not has_timestamp and self._has_fk_timestamps()
            if self.check_fk_timestamps:
                msg = "  Using FK timestamps"
            elif has_timestamp:
                msg = "  Table has timestamps"
            else:
                update_mode = Settings.obj().get_update_mode(table_name)
                msg = f"  Using PK to guess at updates – {UpdateModes(update_mode).name} mode"
            self._verbose_print(msg)

        self.srcgen = CompareInsert.Generator(self.src)
        self.dstgen = CompareInsert.Generator(self.dst)

        self.add: List[Dict[str, str]] = []
        self.update: List[InsertRecord] = []

    def _create_debug_file(self) -> TextIOWrapper | None:
        if self.debug_mode and self.src is not None:
            debug_filename = f"{Settings.obj().get_base_table_name(self.src.name)}-debug.txt"
            output_dir = os.path.dirname(Settings.obj().output_file)
            debug_path = os.path.join(output_dir, "debug")
            if not os.path.exists(debug_path):
                os.makedirs(debug_path)
            full_path = os.path.join(debug_path, debug_filename)
            debug_file = open(full_path, "w", encoding="utf8")
            return debug_file
        return None

    def debug_print(self, obj: Any) -> None:
        if self.debug_mode and self.debug_file is not None:
            self.debug_file.write(str(obj))
            self.debug_file.write("\n")

    def _verbose_print(self, msg):
        if Settings.obj().verbose_mode:
            print(msg)

    def close(self):
        if self.debug_file is not None:
            self.debug_file.close()
            self.debug_file = None

    def _dst_has_autoinc_val(self, to_search: int) -> bool:
        """Searches dst PKs to see if a PK is in use"""
        idx = bisect_left(self.dst_autoinc, to_search)
        return idx != len(self.dst_autoinc) and self.dst_autoinc[idx] == to_search

    def _save_dst_autoinc_val(self, to_save) -> None:
        """Add the PK to the list of dst PKs"""
        # The list is sorted, don't mess that up
        assert to_save is not None, "Don't save None"
        self.dst_autoinc.append(to_save)

    def compare(self):
        if self.src is None:
            return InsertDiffs(self.dst_table, [], [])
        src_item = self.srcgen.get_next_item()
        dst_item = self.dstgen.get_next_item()

        while self.srcgen.is_open:
            if src_item.autoinc is not None and \
                    src_item.autoinc > self.max_src_autoinc:
                self.max_src_autoinc = src_item.autoinc

            if self.dstgen is None or not self.dstgen.is_open or src_item.key < dst_item.key:
                # if dst is closed, copy remaining records from src into dst
                # if src key < dst key, insert this record into dst
                do_insert = True

                row_action = Settings.obj().get_row_level_action(self.src_table.name, src_item.key)
                if row_action == UpdateActions.SKIP:
                    self.debug_print(f"  Skipping {src_item.key} based on row-level action")
                    self.add.append(src_item.insert_vals)
                    do_insert = False

                col_update_action = self._apply_col_level_actions(src_item)
                if col_update_action == UpdateActions.SKIP:
                    self.debug_print(f"  Skipping {src_item.key} based on column-level action")
                    do_insert = False
                
                if not self._was_added_after_fork(src_item):
                    do_insert = False

                if do_insert:
                    if self.debug_mode:
                        self._debug_insert(src_item, dst_item)

                    if self.should_insert_pk:
                        values = src_item.insert_vals
                    else:
                        values = {k: v for k, v in src_item.insert_vals.items() if k not in src_item.pk_vals}

                    self.add.append(values)
                
                src_item = self.srcgen.get_next_item()
            elif src_item.key > dst_item.key:
                # skip over dst records until we "catch up"
                if self.debug_mode:
                    self._debug_skip_dst(src_item, dst_item)

                dst_item = self.dstgen.get_next_item()
            elif src_item.insert_vals == dst_item.insert_vals:
                # records are the same
                # self.debug_print(f"= {src_item.key}  {dst_item.key} => SKIP both")       # TODO TEMPORARY
                src_item = self.srcgen.get_next_item()
                dst_item = self.dstgen.get_next_item()
            else:
                # the keys are the same but the data is different
                # use the timestamp columns to determine which rows to update
                self._compare_update(src_item, dst_item)
                src_item = self.srcgen.get_next_item()
                dst_item = self.dstgen.get_next_item()

        with_updated_aivs = self._update_autoinc_vals()
        return InsertDiffs(self.dst_table, with_updated_aivs, self.update)

    def _debug_insert(self, src_item, dst_item):
        if self.dstgen is None or not self.dstgen.is_open:
            dst_key = "None"
        else:
            dst_key = dst_item.key
        self.debug_print(f"< {src_item.key}  {dst_key} => INSERT src record")

    def _debug_skip_dst(self, src_item, dst_item):
        # self.debug_print(f"> {src_item.key}  {dst_item.key} => SKIP dst")
        hwm = Settings.obj().get_high_water(self.src_table.name)
        dst_pk_val = int(dst_item.pk[0])
        if dst_pk_val < hwm:
            msg = f"Possible delete, dst pk: {dst_pk_val}, hwm: {hwm}"
            self.debug_print(msg)

    def _compare_update(self, src_item: InsertRecord, dst_item: InsertRecord) -> None:
        do_update, ir, old_vals = self._build_update_record(src_item, dst_item)
        if do_update:
            debug_msg = ir.msg
            msg_addition = {k: v[:80] for k, v in old_vals.items()}
            ir.msg += f"\n-- {msg_addition}"

            self.update.append(ir)

            if self.debug_mode:
                cols = list(ir.update_vals.keys())
                self.debug_print(f"U {src_item.key} ({src_item.pk})  {dst_item.key} ({dst_item.pk}) => {cols}")
                self.debug_print(f"  {debug_msg}")
                update_print = {k: v[:80] for k, v in ir.update_vals.items()}
                self.debug_print(f"  NEW: {update_print}")
                old_print = {k: v[:80] for k, v in old_vals.items()}
                self.debug_print(f"  OLD: {old_print}")

    def _msg_for_update(self,
                        update_vals: Dict[str, str],
                        old_vals: Dict[str, str],
                        msg: str) -> str:
        if len(msg) > 0:
            msg += "\n"
        old_print = {k: v[:30] for k, v in old_vals.items()}
        msg += f"-- Was: {old_print}"
        return msg

    def _update_autoinc_vals(self) -> List[RowData]:
        if not self.should_insert_pk:
            return [RowData(r, -1, -1) for r in self.add]
        
        if self.dst_table_has_autoinc_column:
            start = self.dst_table.get_starting_autoinc_val()
            curr = self.dst_table.get_autoinc_val()
            highest = self.dst_autoinc[-1] if len(self.dst_autoinc) > 0 else -1
            self.debug_print(f"  autoinc after - starting: {start}, current: {curr}, highest: {highest}")
            # why do we care about src here?
            #self.debug_print(f"  src highest autoinc val {self.max_src_autoinc}")
            # TODO maybe we have an off-by-one issue?
            self.dst_table.update_autoinc_val(curr + 1)

        result: List[RowData] = []
        # if self.dst_table_has_autoinc_column and \
        #         self.dst_table.get_autoinc_val() <= self.max_src_autoinc:
        #     # TODO kludge! Why add 10? It should be 1. Explanation:
        #     # I found that an auto-draft post was created between
        #     # the time I dumped the DB and the time I ran the update script.
        #     # I hope that burning a few auto-inc values is a harmless workaround to this.
        #     # 2023-6-28 going back to 1
        #     self.dst_table.update_autoinc_val(self.max_src_autoinc + 1)
        #     self.debug_print(f"  New autoinc value is: {self.dst_table.get_autoinc_val()}")

        # TODO parameterize reusing PKs. Not reusing now
        for insert_vals in self.add:
            ai_col_name, old_ai_val = self._get_old_autoinc_val(insert_vals)
            if self.are_copying:
                rd = RowData(insert_vals, old_ai_val, old_ai_val)
            elif not self.dst_table_has_autoinc_column:
                # i think this elif is superfluous (but there is evidence otherwise)
                rd = RowData(insert_vals, -1, -1)
            # elif not self._dst_has_autoinc_val(old_ai_val):
            #     rd = RowData(insert_vals, old_ai_val, old_ai_val)
            #     msg = f"  Reusing PK: {old_ai_val}"
            #     self.debug_print(msg)
            else:
                rd = self._assign_new_autoinc_val(insert_vals, ai_col_name, old_ai_val)

            result.append(rd)

        return result

    def _get_old_autoinc_val(self, insert_vals: Dict[str, str]) -> Tuple[str, str]:
        """Returns the current auto-increment value in a row to be inserted"""
        if self.dst_table_has_autoinc_column:
            ai_col_name = self.dst_table.get_autoinc_column_name()
            old_ai_val = insert_vals[ai_col_name]
            return ai_col_name, int(old_ai_val)
        return "N/A", -1

    def _assign_new_autoinc_val(self,
                                insert_vals: Dict[str, str],
                                ai_col_name: str,
                                old_ai_val: int) -> RowData:
        """Assigns a new PK value to an inserted record"""
        assert self.dst_table_has_autoinc_column, "Can't assign autoinc value to this table"

        new_ai_val = self.dst_table.next_autoinc_val()
        self._save_dst_autoinc_val(new_ai_val)
        insert_vals[ai_col_name] = str(new_ai_val)
        msg = f"  Assigned new PK to column {ai_col_name}, \
old: {old_ai_val}, new: {new_ai_val}"
        self.debug_print(msg)

        # Update URLs with the id in them
        # e.g., https://maryjoyart.com/?p=1712
        # TODO use "special rules"
        pattern = r"(([?&]|&#03f;|&#038;)\w+=)" + str(old_ai_val) + r"\b"
        pk_re = re.compile(pattern, flags=re.IGNORECASE)
        repl = r"\g<1>" + str(new_ai_val)
        for k, v in insert_vals.items():
            new_v, num = pk_re.subn(repl, v)
            if num > 0:
                insert_vals[k] = new_v
        return RowData(insert_vals, int(new_ai_val), int(old_ai_val))

    def _build_update_record(self,
                             src_item: InsertRecord,
                             dst_item: InsertRecord) -> Tuple[bool, InsertRecord | None, Dict[str, str] | None]:
        row_action = Settings.obj().get_row_level_action(self.src_table.name, src_item.key)
        match row_action:
            # Updates that should really be inserts
            case UpdateActions.INSERT_SRC:
                self.debug_print(f"  Inserting {src_item.key} based on row-level action")
                self.add.append(src_item.insert_vals)
                do_update = False
            case UpdateActions.SKIP:
                do_update = False
                msg = "  Skipping update based on row-level action"
                confidence = 1
            case _:
                do_update, _, msg, confidence = self._should_update(src_item, dst_item)

        col_update_action = self._apply_col_level_actions(src_item)
        if col_update_action == UpdateActions.SKIP:
            do_update = False

        if do_update:
            # TODO use separate InsertRecord and UpdateRecord?
            update_vals, old_vals = self._update_only_necessary_cols(src_item, dst_item)
            if len(update_vals) > 0:
                update_mode = Settings.obj().get_update_mode(self.dst_table.name)
                is_pessimistic = update_mode == UpdateModes.PESSIMISTIC and confidence <= 0

                ir = InsertRecord(
                    src_item.key,
                    None,
                    src_item.key_vals,
                    update_vals,
                    src_item.pk,
                    src_item.pk_vals,
                    src_item.autoinc,
                    src_item.is_unique,
                    msg,
                    is_pessimistic)
                return True, ir, old_vals
        return False, None, None

    def _apply_col_level_actions(self, src_item: InsertRecord) -> UpdateActions:
        col_update_action = UpdateActions.DEFAULT
        col_actions = Settings.obj().get_col_level_actions(self.src_table.name)
        if col_actions is not None:
            for col_action in col_actions:
                col_name, pattern, new_update_action = col_action
                if re.search(pattern, src_item.insert_vals[col_name]):
                    col_update_action = new_update_action
        return col_update_action

    def _was_added_after_fork(self, src_item: InsertRecord) -> bool:
        assert src_item is not None

        src_times = None
        if self.src_table.has_timestamp():
            src_times = self._get_column_values(src_item.insert_vals, self.src_table.timestamp_columns)
        elif self.check_fk_timestamps:
            src_times = self._get_fk_timestamps(src_item, self.src_table)

        if src_times is not None:
            timestamp = next(filter(CompareInsert._time_regex.match, src_times))
            return timestamp > Settings.obj().fork_date
        return True     # assume record should be inserted

    def _should_update(self,
                       src_item: InsertRecord,
                       dst_item: InsertRecord) -> Tuple[bool, bool, str, int]:
        """Tries to figure out whether a record should be updated"""
        if self.dst_table.has_timestamp():
            return self._time_should_update(src_item, dst_item)
        
        if self.check_fk_timestamps:
            src_fk_timestamps = self._get_fk_timestamps(src_item, self.src_table)
            dst_fk_timestamps = self._get_fk_timestamps(dst_item, self.dst_table)
            return self._check_timestamps(src_fk_timestamps, dst_fk_timestamps)

        return self._pk_should_update(src_item, dst_item)

    def _has_fk_timestamps(self) -> bool:
        fks = Settings.obj().get_foreign_keys(self.src_table.name)
        for fk in fks:
            if fk.weak:
                continue

            fk_name = Settings.obj().patch_table_name(fk.dst_table, self.src_table.name)
            fk_table = self.repo.get_table(fk_name)
            if fk_table.has_timestamp():
                return True
        return False
    
    def _get_fk_timestamps(self, item: InsertRecord, table: IM.Table) -> List[str] | None:
        fks = Settings.obj().get_foreign_keys(table.name)
        for fk in fks:
            if fk.weak:
                continue

            fk_name = Settings.obj().patch_table_name(fk.dst_table, table.name)
            fk_table = self.repo.get_table(fk_name)
            if fk_table.has_timestamp():
                inserts = self.repo.get_inserts(fk_name)
                # TODO brute force search will be slow
                item_fk = item.insert_vals[fk.src_column]
                for insert in inserts:
                    for row in insert.values:
                        other_key = insert.get_pk(row)[0]
                        if item_fk == other_key:
                            times = CompareInsert._get_column_values(row, fk_table.timestamp_columns)
                            #self.debug_print(f"  Found FK timestamps in {fk_name}: {times}")
                            #self.debug_print(f"    timestamp cols: {fk_table.timestamp_columns}")
                            #self.debug_print(f"    insert vals: {row}")
                            return times
        return None

    def _pk_should_update(self,
                          src_item: InsertRecord,
                          dst_item: InsertRecord) -> Tuple[bool, bool, str, int]:
        """
        Uses PKs to decide if a record should be updated.
        We can only guess...
        """
        do_update = False
        msg = ""
        confidence = 0

        if not self.dst_table_has_autoinc_column:
            msg = "No auto-increment on this table"
            return do_update, True, msg, confidence

        hwm = Settings.obj().get_high_water(self.src_table.name)
        src_end = self.src_table.get_starting_autoinc_val()
        src_pk_val = int(src_item.pk[0])
        dst_pk_val = int(dst_item.pk[0])

        if src_pk_val == dst_pk_val:
            msg = "PKs are equal, MAYBE update"
            if src_pk_val > hwm:
                msg += ", MAYBE insert src"
            # TODO possibly generate insert
            confidence = -1
            do_update = True
        elif dst_pk_val > src_end:
            msg = "PK of dst record is more recent, don't update"
            confidence = 1
        else:
            do_update = True
            msg = "PK of src record is POSSIBLY more recent, update"

        return do_update, True, msg, confidence

    _time_regex = re.compile(r"^(['\"])\d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2}\1$")

    def _time_should_update(self,
                            src_item: InsertRecord,
                            dst_item: InsertRecord) -> Tuple[bool, bool, str, int]:
        """
        Uses timestamp data to decide if a record should be updated.
        This should be exact.
        """
        src_times = self._get_column_values(src_item.insert_vals, self.dst_table.timestamp_columns)
        dst_times = self._get_column_values(dst_item.insert_vals, self.dst_table.timestamp_columns)
        return self._check_timestamps(src_times, dst_times)

    def _check_timestamps(self,
                          src_times: List[str],
                          dst_times: List[str]) -> Tuple[bool, bool, str, int]:
        """
        Uses timestamp data to decide if a record should be updated.
        This should be exact.
        """
        do_update = False
        msg = "Timestamp comparison"
        try:
            src = next(filter(CompareInsert._time_regex.match, src_times))
            dst = next(filter(CompareInsert._time_regex.match, dst_times))

            if src <= Settings.obj().fork_date:
                self.debug_print(f"  Skipping update, record is too old ({src})")

            do_update = src >= dst and src > Settings.obj().fork_date
        except StopIteration:
            msg = "*** Time comparison raised StopIteration ***"
            print(msg)

        return do_update, False, msg, 1

    @classmethod
    def _get_column_values(cls, vals: Dict[str, str], cols: List[str]):
        """Returns a subset of the data with the specified columns"""
        return [vals[col] for col in cols if col in vals]

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
