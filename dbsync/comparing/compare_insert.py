"""Compares data between the prod and staging databases"""

from dataclasses import dataclass
from typing import List, Dict

from dbsync import intermediate as IM
from dbsync.comparing.unpacked_insert import UnpackedInsert, InsertRecord
from dbsync.exceptions import DbSyncCompareException


@dataclass
class InsertDiffs:
    dst_table: IM.Table
    additions: List[Dict[str, str]]
    updates: List[InsertRecord]

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

    # TODO do we need backticks on the column names?
    def _generate_insert(self) -> List[str]:
        if (len(self.additions) == 0):
            return []

        sql = []
        l = len(self.additions)
        r = self._pluralize(l, "row")
        sql.append(f"-- Inserting {l} {r}:")
        dst_cols = list(self.additions[0].keys())
        col_str = ", ".join(dst_cols)
        sql.append(f"INSERT INTO `{self.dst_table.name}` ({col_str}) VALUES")
        for add in self.additions:
            values = [val for val in add.values()]
            sql.append(f"({', '.join(values)}),")
        self._add_semicolon(sql)
        return sql

    def _generate_update(self, record: InsertRecord) -> List[str]:
        sql = []
        sql.append(f"UPDATE `{self.dst_table.name}`")
        assignments = [f"{col}={val}" for col, val in record.update_vals.items()]
        sql.append(f"SET {', '.join(assignments)}")
        conditions = [f"{col}={val}" for col, val in record.key_vals.items()]
        sql.append(f"WHERE {' AND '.join(conditions)};")
        return sql

    def generate_sql(self):
        sql = self._generate_insert()

        l = len(self.updates)
        if (l > 0):
            r = self._pluralize(l, "record")
            sql.append(f"-- Updating {l} {r}:")
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

        add = []
        update = []

        src_item = srcgen.get_next_item()
        if dstgen is None or not dstgen.is_open:
            dst_item = None
        else:
            dst_item = dstgen.get_next_item()

        while srcgen.is_open:
            if dstgen is None or not dstgen.is_open or \
               src_item.key < dst_item.key:
                # if dst is closed, copy remaining records from src into dst
                # if src key < dst key, insert this record into dst
                add.append(src_item.insert_vals)
                src_item = srcgen.get_next_item()
            elif src_item.insert_vals == dst_item.insert_vals:
                # records are the same
                src_item = srcgen.get_next_item()
                dst_item = dstgen.get_next_item()
            elif src_item.key > dst_item.key:
                # skip over dst records until we "catch up"
                dst_item = dstgen.get_next_item()
            else:
                # the key are the same but the data is different
                # what should we do here? if the src record is newer,
                # we probably want to copy it to dst. Otherwise, we
                # don't want to do anything
                # TODO just update the columns that are different
                # TODO use a timestamp column to decide whether or not to update
                # TODO use separate InsertRecord and UpdateRecord?
                update.append(InsertRecord(src_item.key, None, src_item.key_vals, src_item.update_vals))

                src_item = srcgen.get_next_item()
                dst_item = dstgen.get_next_item()

        return InsertDiffs(dst_table, add, update)
