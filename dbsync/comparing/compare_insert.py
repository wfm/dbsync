"""Compares data between the prod and staging databases"""

import re
from dataclasses import dataclass, field
from typing import List, Dict

from dbsync import intermediate as IM
from dbsync.comparing.unpacked_insert import UnpackedInsert, InsertRecord
from dbsync.settings import Settings


@dataclass
class InsertDiffs:
    dst_table: IM.Table
    additions: List[Dict[str, str]]
    updates: List[InsertRecord]
    table_msg: str = field(default="")

    def _verbose_print(self, msg):
        if Settings.obj().verbose_mode:
            print(msg)

    def _pluralize(self, n: int, s: str) -> str:
        if n == 1:
            return s
        return s + "s"

    def _add_semicolon(self, sql: List[str]) -> None:
        """replace trailing comma with a semicolon"""
        if sql[-1][-1:] == ",":
            sql[-1] = sql[-1][:-1] + ";"

    def _join_lines(self, sql: List[str]) -> str:
        return "\n".join(sql)

    def _generate_insert(self) -> List[str]:
        add_len = len(self.additions)
        if (add_len == 0):
            return []

        sql = []
        r = self._pluralize(add_len, "row")
        sql.append(f"-- Inserting {add_len} {r}:")
        self._verbose_print(f"  Inserting {add_len} {r}")
        dst_cols = [f"`{col}`" for col in list(self.additions[0].keys())]
        col_str = ", ".join(dst_cols)

        idx = 0
        while idx < add_len:
            sql.append(f"INSERT INTO `{self.dst_table.name}` ({col_str}) VALUES")
            last = min(add_len, idx + 100)
            for add in self.additions[idx:last]:
                values = [val for val in add.values()]
                sql.append(f"({', '.join(values)}),")
            self._add_semicolon(sql)
            idx = last

        return sql

    def _generate_update(self, record: InsertRecord) -> List[str]:
        sql = []
        if len(record.msg) > 0:
            sql.append(f"-- {record.msg}")
        sql.append(f"UPDATE `{self.dst_table.name}`")
        assignments = [f"`{col}`={val}" for col, val in record.update_vals.items()]
        sql.append(f"SET {', '.join(assignments)}")
        conditions = [f"`{col}`={val}" for col, val in record.key_vals.items()]
        sql.append(f"WHERE {' AND '.join(conditions)};")
        return sql

    def generate_sql(self):
        self._verbose_print(f"Updating table {self.dst_table.name}")
        sql = []
        if len(self.table_msg) > 0:
            sql.append(f"-- {self.table_msg}")
            self._verbose_print("  " + self.table_msg)

        sql += self._generate_insert()

        upd_len = len(self.updates)
        if (upd_len > 0):
            r = self._pluralize(upd_len, "record")
            sql.append(f"-- Updating {upd_len} {r}:")
            self._verbose_print(f"  Updating {upd_len} {r}")
            for upd in self.updates:
                sql += self._generate_update(upd)

        return self._join_lines(sql)


class Generator:
    def __init__(self, ui: UnpackedInsert):
        ui.dedup()      # side effects!
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


# TODO would this be better with instance methods?
class CompareInsert:
    """
    Compares the values in two insert statements and generates
    lists of data to be inserted and updated in the dst table
    to make it equivalent to the src table.
    """
    @classmethod
    def compare(
            cls,
            src: UnpackedInsert | None,
            dst: UnpackedInsert | None,
            dst_table: IM.Table) -> InsertDiffs:

        if src is None:
            return InsertDiffs(dst_table, [], [])
        srcgen = Generator(src)

        if dst is None:
            dstgen = None
        else:
            dstgen = Generator(dst)

        add: List[Dict[str, str]] = []
        update: List[InsertRecord] = []

        src_item = srcgen.get_next_item()
        if dstgen is None or not dstgen.is_open:
            dst_item = None
        else:
            dst_item = dstgen.get_next_item()

        while srcgen.is_open:
            if dstgen is None or not dstgen.is_open or src_item.key < dst_item.key:
                # if dst is closed, copy remaining records from src into dst
                # if src key < dst key, insert this record into dst
                add.append(src_item.insert_vals)
                src_item = srcgen.get_next_item()
            elif src_item.key > dst_item.key:
                # skip over dst records until we "catch up"
                dst_item = dstgen.get_next_item()
            elif src_item.insert_vals == dst_item.insert_vals:
                # records are the same
                src_item = srcgen.get_next_item()
                dst_item = dstgen.get_next_item()
            else:
                # the key are the same but the data is different
                # what should we do here? if the src record is newer,
                # we probably want to copy it to dst. Otherwise, we
                # don't want to do anything.
                do_update = cls._get_time_info(src_item, dst_item, dst_table)
                if do_update:
                    # TODO use separate InsertRecord and UpdateRecord?
                    update_vals = cls._update_only_necessary_cols(src_item, dst_item)
                    update.append(
                        InsertRecord(
                            src_item.key,
                            None,
                            src_item.key_vals,
                            update_vals))

                src_item = srcgen.get_next_item()
                dst_item = dstgen.get_next_item()

        return InsertDiffs(dst_table, add, update)

    _time_regex = re.compile(r"^(['\"])\d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2}\1$")

    @classmethod
    def _get_time_info(cls, src_item: InsertRecord, dst_item: InsertRecord, table: IM.Table) -> bool:
        do_update = False
        if table.timestamp_columns is None or \
                len(table.timestamp_columns) == 0:
            # not certain whether to update or not to update
            do_update = Settings.obj().should_update_table(table.name)
        else:
            src_times = cls._get_column_values(src_item.insert_vals, table.timestamp_columns)
            dst_times = cls._get_column_values(dst_item.insert_vals, table.timestamp_columns)
            try:
                src = next(filter(CompareInsert._time_regex.match, src_times))
                dst = next(filter(CompareInsert._time_regex.match, dst_times))

                do_update = src >= dst  # TODO is it ok to compare strings here?
            except StopIteration:
                print("*** Time comparison raised StopIteration ***")

        return do_update

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
                                    dst_item: InsertRecord) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for col, src_val in src_item.update_vals.items():
            dst_val = dst_item.update_vals[col]
            if src_val != dst_val:
                result[col] = src_val
        return result
