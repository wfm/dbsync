"""An easier-to-work-with representation of an insert statement"""

import re
from typing import Callable, List, Dict, Iterator
from operator import itemgetter
from dataclasses import dataclass, field

from dbsync import intermediate as IM
from dbsync.exceptions import DbSyncCompareException
from dbsync.settings import Settings


@dataclass
class InsertRecord:
    """Data needed to generate insert and update statements for a table"""
    key: List[str]                          # values of (unique|primary) keys
    insert_vals: Dict[str, str]             # key,value pairs of all columns
    key_vals: Dict[str, str]                # key,value pairs of (unique|primary) keys
    update_vals: Dict[str, str]             # key,value pairs of non-key (unique|primary) columns
    pk: List[str]                           # primary key values
    pk_vals: Dict[str, str]                 # key,value pairs of primary keys
    autoinc: int | None                     # autoincrement column value
    is_unique: bool                         # T => key is from unique key, F => key is from pk
    msg: str = field(default="")


class UnpackedInsert:
    """An "unpacked" version of an insert statement"""
    def __init__(self, table: IM.Table, insert: IM.Insert):
        self.name = table.name
        # important: use insert cols not table cols
        self.columns = insert.columns
        self.values = self._dstify(self._unpack(insert.values))

        self.comparison_key = table.get_comparison_key()
        self.is_unique = self.comparison_key.is_unique
        if self.comparison_key is None:
            raise DbSyncCompareException("Table has no keys")

        self.key_column_names = self.comparison_key.get_column_names()
        # for timestamp-based comparison
        if table.use_time_based_comparison:
            self.create_time_column_name = table.get_create_time_column_name()
            self.key_column_names = [self.create_time_column_name] + self.key_column_names
        self._key_numeric_cols = []
        for name in self.key_column_names:
            datatype = table.get_column(name).datatype
            if Settings.obj().is_integer_datatype(datatype):
                t = "i"
            elif Settings.obj().is_numeric_datatype(datatype):
                t = "f"
            else:
                t = "-"
            self._key_numeric_cols.append(t)

        self._key_getter = itemgetter(*self.key_column_names)

        pk = table.get_primary_key()
        self.pk_cols = pk.get_column_names()
        self._pk_getter = itemgetter(*self.pk_cols)

        self.nonkey_column_names = [x for x in self.columns if x not in self.key_column_names]
        if len(self.nonkey_column_names) == 0:
            self._nonkey_getter = None
        else:
            self._nonkey_getter = itemgetter(*self.nonkey_column_names)

        self.autoinc_column_name = table.get_autoinc_column_name()

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
        key_items = self.apply_getter(values, self._key_getter)
        key = []
        for indicator, str_value in zip(self._key_numeric_cols, key_items, strict=True):
            if str_value.casefold() == "null":
                val = float("nan")
            elif indicator == "i":
                val = int(str_value)
            elif indicator == "f":
                val = float(str_value)
            else:
                val = str_value
            key.append(val)
        return key

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

    def append(self, insert: IM.Insert) -> None:
        if insert.columns != self.columns:
            msg = f"Tried to append different shaped Inserts, table {self.name}"
            raise DbSyncCompareException(msg)
        u = self._unpack(insert.values)
        self.values += u

    def _unpack(self, values: List[List[str]]) -> List[Dict[str, str]]:
        return [dict(zip(self.columns, v, strict=True)) for v in values]

    def _dstify(self, values: List[Dict[str, str]]) -> List[List[str]]:
        if Settings.obj().is_dst_table(self.name):
            return values

        rules = Settings.obj().get_special_rules(self.name)
        if rules is None:
            self._test_special_rules(values)
            return values

        def apply_rules(key: str, value: str) -> str:
            if key in rules:
                return rules[key](value)
            return value

        result = [
            {k: apply_rules(k, v) for k, v in row.items()}
            for row in values]

        self._test_special_rules(values, list(rules.keys()))
        return result

    def _test_special_rules(self,
                            values: List[Dict[str, str]],
                            cols_with_rules: List[str] | None = None) -> None:
        if not Settings.obj().debug_mode:
            return

        if cols_with_rules is None:
            cols_with_rules = []

        for row in values:
            for col, val in row.items():
                if col not in cols_with_rules:
                    for regex in Settings.obj().get_test_patterns():
                        m = regex.search(val)
                        if m:
                            print(f"Edit data in table {self.name}, column {col}: {m.group(0)}")

    def pack(self) -> IM.Insert:
        packed_vals = UnpackedInsert.pack_values(self.values)
        return IM.Insert(self.name, self.columns, packed_vals)

    def sort(self) -> None:
        """Sort and removed duplicates"""
        if (len(self.values) < 2):
            return

        try:
            self.values.sort(key=self.get_key)
        except KeyError as ke:
            print(f"KeyError on table {self.name}")
            print(f"  keys are: {self.key_column_names}")
            print("  Offending data:")
            for v in self.values:
                try:
                    _ = self.get_key(v)
                except Exception:
                    print(repr(v))
                    break

            raise ke

    def _get_key_values_dict(self, vals: List[str]) -> Dict[str, str]:
        return dict(zip(self.key_column_names, vals, strict=True))

    def _get_nonkey_values_dict(self, v: Dict[str, str]) -> Dict[str, str]:
        nonkey_vals = self.get_non_key(v)
        return dict(zip(self.nonkey_column_names, nonkey_vals, strict=True))

    def _get_pk_values_dict(self, pk: List[str]) -> Dict[str, str]:
        return dict(zip(self.pk_cols, pk, strict=True))

    def _get_autoinc_value(self, v: Dict[str, str]) -> int | None:
        if self.autoinc_column_name is None:
            return None
        autoinc = v[self.autoinc_column_name]
        autoinc = re.sub(r"^([\"'])(\d+)\1$", r"\2", autoinc)
        return int(autoinc)

    # TODO maybe use __iter__ ????
    def values_gen(self) -> Iterator[InsertRecord]:
        """Generator yielding keys and values from the insert statement"""
        for v in self.values:
            key = self.get_key(v)
            kv = self._get_key_values_dict(key)
            upd = self._get_nonkey_values_dict(v)
            pk = self.apply_getter(v, self._pk_getter)
            pk_vals = self._get_pk_values_dict(pk)
            autoinc = self._get_autoinc_value(v)
            yield InsertRecord(key, v, kv, upd, pk, pk_vals, autoinc, self.is_unique)
