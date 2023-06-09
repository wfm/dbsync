"""An easier-to-work-with representation of an insert statement"""

from typing import List, Dict, Iterator, Tuple
from operator import itemgetter
from dataclasses import dataclass, field

from dbsync import intermediate as IM
from dbsync.exceptions import DbSyncCompareException


@dataclass
class InsertRecord:
    """Data needed to generate insert and update statements for a table"""
    key: List[str]                          # values of (unique|primary) keys
    insert_vals: Dict[str, str] | None      # key,value pairs of all columns
    key_vals: Dict[str, str]                # key,value pairs of (unique|primary) keys
    update_vals: List[str]                  # key,value pairs of non-key (unique|primary) columns
    # unique_vals: Dict[str, str] | None    # key,value pairs of unique key - still need?
    msg: str = field(default="")


class UnpackedInsert:
    """An "unpacked" version of an insert statement"""
    def __init__(self, table: IM.Table, insert: IM.Insert):
        self.name = table.name
        # important: use insert cols not table cols
        self.columns = insert.columns
        self.values = self._unpack(insert.values)

        self.comparison_key = table.get_comparison_key()
        if self.comparison_key is None:
            raise DbSyncCompareException("Table has no keys")

        self.key_column_names = self.comparison_key.get_column_names()
        self._key_getter = itemgetter(*self.key_column_names)

        self.nonkey_column_names = [x for x in self.columns if x not in self.key_column_names]
        if len(self.nonkey_column_names) == 0:
            self._nonkey_getter = None
        else:
            self._nonkey_getter = itemgetter(*self.nonkey_column_names)

    def __str__(self):
        return f"UnpackedInsert for {self.name}"

    def __repr__(self):
        return f"""{self.__str__()}
    columns: {self.columns}
       keys: {self.key_column_names}
   non-keys: {self.nonkey_column_names}
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

    def _limit_value_len(self, value: str, limit: int | None) -> str:
        if limit is not None:
            is_quoted = value[0] == "'" or '"'
            end = limit + (1 if is_quoted else 0)
            slc = slice(0, end)
            value = value[slc]
            if is_quoted and value[-1] != value[0]:
                value += value[0]
        return value

    # come back to this - we need to trim the keys with lengths for
    # comparison but use the full key for updating (i think)
    # def get_unique_vals(self, values):
    #     if self.has_unique_key:
    #         unique_vals = self.apply_getter(values, self._unique_key_getter)
    #         return [self._limit_value_len(*pair) for pair
    #                 in zip(unique_vals, self.unique_key.get_column_lengths(), strict=True)]
    #     return None

    def append(self, insert: IM.Insert) -> None:
        if insert.columns != self.columns:
            msg = f"Tried to append different shaped Inserts, table {self.name}"
            raise DbSyncCompareException(msg)
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
            print(f"  keys are: {self.key_column_names}")
            print("  Offending data:")
            for v in self.values:
                try:
                    _ = self._key_getter(v)
                except Exception:
                    print(repr(v))
                    break

            raise ke

        i = 0
        curr = self.get_key(self.values[0])
        while i < len(self.values) - 1:
            succ = self.get_key(self.values[i + 1])
            if curr != succ:
                filtered.append(self.values[i])
            i += 1
            curr = succ

        filtered.append(self.values[-1])
        self.values = filtered

    def _get_key_values_dict(self, vals: List[str]) -> Dict[str, str]:
        return dict(zip(self.key_column_names, vals, strict=True))

    def _get_nonkey_values_dict(self, v: Dict[str, str]) -> Dict[str, str]:
        nonkey_vals = self.get_non_key(v)
        return dict(zip(self.nonkey_column_names, nonkey_vals, strict=True))

    # TODO maybe use __iter__ ????
    def values_gen(self) -> Iterator[InsertRecord]:
        """Generator yielding keys and values from the insert statement"""
        for v in self.values:
            key = self.get_key(v)
            kv = self._get_key_values_dict(key)
            upd = self._get_nonkey_values_dict(v)
            yield InsertRecord(key, v, kv, upd)
