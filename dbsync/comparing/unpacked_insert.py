"""An easier-to-work-with representation of an insert statement"""

from typing import List, Dict
from operator import itemgetter

from dbsync import intermediate as IM
from dbsync.exceptions import DbSyncCompareException


class UnpackedInsert:
    def __init__(self, table: IM.Table, insert: IM.Insert):
        self.name = table.name
        self.primary_keys = table.primary_keys
        # important: use insert cols not table cols
        self.columns = insert.columns
        self.values = self._unpack(insert.values)

    def append(self, insert: IM.Insert) -> None:
        u = self._unpack(insert.values)
        self.values += u

    def _unpack(self, values: List[List[str]]) -> List[Dict[str, str]]:
        return [[dict(zip(self.columns, v))] for v in values]

    def pack(self) -> IM.Insert:
        packed_vals = [d.values() for d in self.values]
        return IM.Insert(self.name, self.columns, packed_vals)

    def dedup(self) -> None:
        filtered = []
        f = itemgetter(self.columns)
        self.values.sort(key=f)
        i = 0
        curr = f(self.values[0])
        while i < (len(self.values))-1:
            succ = f(self.values[i+1])
            if curr != succ:
                filtered.append(self.values[i])
            i += 1
            curr = succ
        filtered.append(len(self.values)-1)

        self.values = filtered
