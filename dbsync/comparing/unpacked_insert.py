"""An easier-to-work-with representation of an insert statement"""

from typing import List, Dict, Iterator, Tuple
from operator import itemgetter
from dataclasses import dataclass

from dbsync import intermediate as IM


@dataclass
class InsertRecord:
    """Data needed to generate insert and update statements for a table"""
    key: Tuple  # of strings
    insert_vals: Dict[str, str] | None
    key_vals: Dict[str, str]
    update_vals: Dict[str, str]


class UnpackedInsert:
    """An "unpacked" version of an insert statement"""
    def __init__(self, table: IM.Table, insert: IM.Insert):
        self.name = table.name
        # important: use insert cols not table cols
        self.columns = insert.columns
        self.values = self._unpack(insert.values)

        self.primary_keys = table.primary_keys
        if len(self.primary_keys) == 0:
            print(f"Table {self.name} has no primary key columns")
            self._key_getter = None
        else:
            self._key_getter = itemgetter(*self.primary_keys)

        self.nonkeys = [x for x in self.columns if x not in self.primary_keys]
        if len(self.nonkeys) == 0:
            print(f"Table {self.name} has no non-primary key columns")
            self._nonkey_getter = None
        else:
            self._nonkey_getter = itemgetter(*self.nonkeys)

    def __str__(self):
        return f"UnpackedInsert for {self.name}"

    def __repr__(self):
        return f"""{self.__str__()}
    columns: {self.columns}
        PKs: {self.primary_keys}
   non-keys: {self.nonkeys}
     values: {self.values}"""

    @classmethod
    def pack_values(cls, values: List[Dict[str, str]]) -> List[List[str]]:
        return [list(d.values()) for d in values]

    def apply_getter(self, values, getter):
        if getter is None:
            return []

        result = getter(values)     # this is returning a tuple, dunno why
        if isinstance(result, tuple):
            return list(result)
        elif isinstance(result, list):
            return result
        return [result]

    def get_key(self, values):
        return self.apply_getter(values, self._key_getter)

    def get_non_key(self, values):
        return self.apply_getter(values, self._nonkey_getter)

    def append(self, insert: IM.Insert) -> None:
        u = self._unpack(insert.values)
        self.values += u

    def _unpack(self, values: List[List[str]]) -> List[Dict[str, str]]:
        return [dict(zip(self.columns, v, strict=True)) for v in values]

    def pack(self) -> IM.Insert:
        packed_vals = UnpackedInsert.pack_values(self.values)
        return IM.Insert(self.name, self.columns, packed_vals)

    def dedup(self) -> None:
        """Sort and removed duplicates"""
        #
        # TODO re sorting
        # The sort will use the collating sequence for strings
        # so numeric columns won't be in numeric order. I'm
        # not sure this is a bad thing.
        # Alternatives:
        # 1. Be smart about the datatype - hard and error prone
        # 2. Wrap the data with the original order and unsort at the end
        if (len(self.values) < 2):
            return

        filtered = []
        try:
            self.values.sort(key=self._key_getter)
        except KeyError as ke:
            print(f"KeyError on table {self.name}")
            print(f"  keys are: {self.primary_keys}")
            print("  Offending data:")
            for v in self.values:
                try:
                    _ = self._key_getter(v)
                except:
                    print(repr(v))
                    break

            raise ke

        i = 0
        curr = self.get_key(self.values[0])
        while i < len(self.values) - 1:
            succ = self.get_key(self.values[i+1])
            if curr != succ:
                filtered.append(self.values[i])
            i += 1
            curr = succ

        filtered.append(self.values[-1])
        self.values = filtered

    def _get_key_values_dict(self, vals: List[str]) -> Dict[str, str]:
        return dict(zip(self.primary_keys, vals, strict=True))

    def _get_nonkey_values_dict(self, v: Dict[str, str]) -> Dict[str, str]:
        nonkey_vals = self.get_non_key(v)
        return dict(zip(self.nonkeys, nonkey_vals, strict=True))

    # TODO maybe use __iter__ ????
    def values_gen(self) -> Iterator[InsertRecord]:
        """Generator yielding keys and values from the insert statement"""
        for v in self.values:
            key = self.get_key(v)
            kv = self._get_key_values_dict(key)
            upd = self._get_nonkey_values_dict(v)
            yield InsertRecord(key, v, kv, upd)
