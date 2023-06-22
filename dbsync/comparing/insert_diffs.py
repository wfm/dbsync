from bisect import bisect_left
from dataclasses import dataclass, field
from typing import List, Dict

from dbsync import intermediate as IM
from dbsync.comparing.unpacked_insert import InsertRecord
from dbsync.settings import Settings


@dataclass
class RowData:
    insert_vals: Dict[str, str]
    new_autoinc_val: int
    old_autoinc_val: int


@dataclass
class InsertDiffs:
    """Contains the results of the comparison of two insert statements"""
    dst_table: IM.Table
    additions: List[RowData]
    updates: List[InsertRecord]
    table_msg: str = field(default="")
    is_sorted: bool = field(default=False)

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
        self._verbose_print(f"    Inserting {add_len} {r}")
        dst_cols = [f"`{col}`" for col in list(self.additions[0].insert_vals.keys())]
        col_str = ", ".join(dst_cols)

        idx = 0
        while idx < add_len:
            sql.append(f"INSERT INTO `{self.dst_table.name}` ({col_str}) VALUES")
            last = min(add_len, idx + 100)
            for add in self.additions[idx:last]:
                values = [val for val in add.insert_vals.values()]
                sql.append(f"({', '.join(values)}),")
            self._add_semicolon(sql)
            idx = last

        return sql

    def _generate_update(self, record: InsertRecord) -> List[str]:
        sql = []
        if record.is_pessimistic and Settings.obj().omit_pessimistic_sql:
            return sql

        if len(record.msg) > 0:
            sql.append(f"-- {record.msg}")

        leader = ""
        if record.is_pessimistic:
            leader = "-- "
            sql.append("-- Pessimistically omitted:")

        sql.append(f"{leader}UPDATE `{self.dst_table.name}`")
        assignments = [f"`{col}`={val}" for col, val in record.update_vals.items()]
        sql.append(f"{leader}SET {', '.join(assignments)}")
        # always use PK in update statements
        conditions = [f"`{col}`={val}" for col, val in record.pk_vals.items()]
        sql.append(f"{leader}WHERE {' AND '.join(conditions)};")
        return sql

    def generate_sql(self):
        self._verbose_print(f"  Syncing table {self.dst_table.name}")
        sql = []
        if len(self.table_msg) > 0:
            sql.append(f"-- {self.table_msg}")
            self._verbose_print("  " + self.table_msg)

        upd_len = len(self.updates)
        if (upd_len > 0):
            r = self._pluralize(upd_len, "record")
            sql.append(f"-- Updating {upd_len} {r}:")
            self._verbose_print(f"    Updating {upd_len} {r}")
            for upd in self.updates:
                sql += self._generate_update(upd)

        sql += self._generate_insert()

        return self._join_lines(sql)

    def find_replacement_key(self, old_key_val: int) -> int:
        if not self.is_sorted:
            self.additions.sort(key=lambda x: x.old_autoinc_val)
            self.is_sorted = True

        idx = bisect_left(self.additions, old_key_val, key=lambda x: x.old_autoinc_val)
        if idx != len(self.additions) and self.additions[idx].old_autoinc_val == old_key_val:
            return self.additions[idx].new_autoinc_val
        if old_key_val < self.dst_table.get_starting_autoinc_val():
            return old_key_val
        raise ValueError(f"Old key {old_key_val} not found \
and is >= starting autoinc value ({self.dst_table.get_starting_autoinc_val()})")
