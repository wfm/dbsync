from bisect import bisect_left
from typing import Any, List, Self, Tuple

from dbsync.settings import Settings


# from https://stackoverflow.com/a/56842689:
class Reverser:
    def __init__(self, obj: Any) -> None:
        self.obj = obj

    def __eq__(self, other: Self) -> bool:
        return other.obj == self.obj

    def __lt__(self, other: Self) -> bool:
        return other.obj < self.obj


class OrderedTableNames:
    def __init__(self, unordered_table_names: List[str]) -> None:
        self.unordered_table_names = unordered_table_names
        self.accumulator = {}
        self.key_tables = [(fk.src_table, fk.dst_table) for fk in Settings.obj().foreign_keys]
        self.key_tables.sort(key=lambda k: k[0])

    def _accumulate(self, table_name: str) -> None:
        if table_name in self.accumulator:
            self.accumulator[table_name] += 1
        else:
            self.accumulator[table_name] = 1

    def _follow_chain(self, table_name_pair, level=0):
        if table_name_pair[0] == table_name_pair[1]:
            return

        self._accumulate(table_name_pair[1])
        if len(table_name_pair[1]) > 0:
            idx = bisect_left(self.key_tables, table_name_pair[1], key=lambda k: k[0])
            while idx != len(self.key_tables) and table_name_pair[1] == self.key_tables[idx][0]:
                self._follow_chain(self.key_tables[idx], level + 1)
                idx += 1

    def _get_final_sort_key(self, table_name: str) -> Tuple[str, int]:
        if table_name in self.accumulator:
            return Reverser(self.accumulator[table_name]), table_name
        return Reverser(0), table_name

    def get_ordered_tables(self) -> List[str]:
        for table_name_pair in self.key_tables:
            self._follow_chain(table_name_pair)

        table_names = [Settings.obj().get_base_table_name(x)
                       for x in self.unordered_table_names
                       if Settings.obj().is_src_table(x)]
        table_names.sort(key=lambda x: self._get_final_sort_key(x))
        return [Settings.obj().get_src_table_name_from_base_name(x) for x in table_names]
