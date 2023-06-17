"""Compares data between the prod and staging databases"""

from dataclasses import dataclass
import re
from typing import List, Dict, Tuple

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
        def __init__(self, ui: UnpackedInsert):
            ui.sort()      # side effects!
            self.gen = ui.values_gen()
            self.is_open = True

        def get_next_item(self) -> InsertRecord | None:
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
                 dst: UnpackedInsert | None,
                 dst_table: IM.Table) -> InsertDiffs:
        self.src = src
        self.dst = dst
        self.dst_table = dst_table

        if self.src is not None:
            self.srcgen = CompareInsert.Generator(self.src)

        if self.dst is None:
            self.dstgen = None
        else:
            self.dstgen = CompareInsert.Generator(self.dst)

        self.add: List[Dict[str, str]] = []
        self.update: List[InsertRecord] = []

    def compare(self):
        if self.src is None:
            return InsertDiffs(self.dst_table, [], [])
        src_item = self.srcgen.get_next_item()
        dst_item = self.dstgen.get_next_item()

        while self.srcgen.is_open:
            if self.dstgen is None or not self.dstgen.is_open or src_item.key < dst_item.key:
                # if dst is closed, copy remaining records from src into dst
                # if src key < dst key, insert this record into dst
                if self.dstgen is None or not self.dstgen.is_open:
                    dst_key = "None"
                else:
                    dst_key = dst_item.key
                # print(f"< [{src_item.key}]  [{dst_key}] => INSERT src record")
                self._append_insert_vals(src_item.insert_vals)
                src_item = self.srcgen.get_next_item()
            elif src_item.key > dst_item.key:
                # skip over dst records until we "catch up"
                # print(f"> [{src_item.key}]  [{dst_item.key}] => SKIP dst")
                dst_item = self.dstgen.get_next_item()
            elif src_item.insert_vals == dst_item.insert_vals:
                # records are the same
                # print(f"= [{src_item.key}]  [{dst_item.key}] => SKIP BOTH")
                src_item = self.srcgen.get_next_item()
                dst_item = self.dstgen.get_next_item()
            else:
                # the keys are the same but the data is different
                # use the timestamp columns to determine which rows to update
                do_update, msg = self._get_time_info(src_item, dst_item)
                cols = []  # TODO temp
                if do_update:
                    # TODO use separate InsertRecord and UpdateRecord?
                    update_vals, old_vals = self._update_only_necessary_cols(src_item, dst_item)
                    cols = list(update_vals.keys())   # TODO temp
                    self.update.append(
                        InsertRecord(
                            src_item.key,
                            None,
                            src_item.key_vals,
                            update_vals,
                            src_item.pk, src_item.is_unique,
                            msg))

                # print(f"{'U' if do_update else 'X'} [{src_item.key}]  [{dst_item.key}] => {cols}")
                # if "post_content" in update_vals:
                #     update_vals["post_content"] = update_vals["post_content"][0:50]
                # print("NEW:")
                # print(update_vals)
                # print(80 * '-')
                # if "post_content" in old_vals:
                #     old_vals["post_content"] = old_vals["post_content"][0:50]
                # print("OLD:")
                # print(old_vals)
                # print(80 * '=')

                src_item = self.srcgen.get_next_item()
                dst_item = self.dstgen.get_next_item()

        return InsertDiffs(self.dst_table, self.add, self.update)

    def _append_insert_vals(self, insert_vals):
        new_pk_val = str(self.dst_table.next_autoinc_val())
        pk_name = self.dst.pk_cols
        assert len(pk_name) == 1, "Expected 1 PK column name"
        pk_name = pk_name[0]
        old_pk_val = insert_vals[pk_name]
        insert_vals[pk_name] = new_pk_val
        print(f"new pk: {new_pk_val}, old pk: {old_pk_val}")

        # Update URLs with the id in them
        # e.g., https://maryjoyart.com/?p=1712
        pk_re = re.compile(r"(([?&]|&#03f;|&#038;)\w+=)" + old_pk_val + r"\b", flags=re.IGNORECASE)
        repl = r"\g<1>" + new_pk_val
        for k, v in insert_vals.items():
            new_v, num = pk_re.subn(repl, v)
            if num > 0:
                insert_vals[k] = new_v

        rd = RowData(insert_vals, int(new_pk_val), int(old_pk_val))
        self.add.append(rd)

    _time_regex = re.compile(r"^(['\"])\d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2}\1$")

    def _get_time_info(self, src_item: InsertRecord, dst_item: InsertRecord) -> Tuple[bool, str]:
        do_update = False
        msg = ""
        if self.dst_table.timestamp_columns is None or \
                len(self.dst_table.timestamp_columns) == 0:
            # not certain whether to update or not to update
            do_update = Settings.obj().should_update_table(self.dst_table.name)
            msg = "+++ Update of table without a timestamp column"
        else:
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

        return (do_update, msg)

    @classmethod
    def _get_column_values(cls, vals: Dict[str, str], cols: List[str]):
        result = []
        for col in cols:
            if col in vals:
                result.append(vals[col])
        return result

    @classmethod
    def _update_only_necessary_cols(cls,
                                    src_item: InsertRecord,
                                    dst_item: InsertRecord) -> \
            Tuple[Dict[str, str], Dict[str, str]]:
        update_vals: Dict[str, str] = {}
        old_vals: Dict[str, str] = {}
        for col, src_val in src_item.update_vals.items():
            dst_val = dst_item.update_vals[col]
            if src_val != dst_val:
                update_vals[col] = src_val
                old_vals[col] = dst_val
        return update_vals, old_vals
