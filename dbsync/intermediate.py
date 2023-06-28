"""Intermediate representations of SQL statements"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple

from dbsync.exceptions import DbSyncCompareException
from dbsync.settings import DmlOptions, Settings


class Quoted:
    _re = re.compile(r"^\s*`?(.+?)`?\s*$")

    @classmethod
    def fix_name(cls, name):
        m = cls._re.match(name)
        if m:
            return m.group(1)
        return name


@dataclass
class NameMixin:
    name: str

    def __post_init__(self):
        self.name = Quoted.fix_name(self.name)


@dataclass
class Intermediate:
    """Base class for the rest of the classes in this module"""
    def _print_verbose(self, text) -> None:
        if Settings.obj().verbose_mode:
            print(text)


@dataclass
class KeyColumn(NameMixin):
    """Represents a column in a KEY specification"""
    length: int | None = field(default=None)


@dataclass
class Key(Intermediate, NameMixin):
    """Represents a KEY specification"""
    columns: List[KeyColumn] = field(default_factory=list)
    is_primary: bool = field(default=False)
    is_unique: bool = field(default=False)

    def add_column(self, col: KeyColumn) -> None:
        self.columns.append(col)

    def get_column_names(self) -> List[str]:
        return [col.name for col in self.columns]

    def get_column_lengths(self) -> List[str]:
        return [col.length for col in self.columns]

    def generate_sql(self) -> str:
        sql = ""
        if self.is_primary:
            sql += "PRIMARY "
        elif self.is_unique:
            sql += "UNIQUE "
        sql += "KEY"

        if len(self.name) > 0:
            sql += f" `{self.name}`"

        sql += " ("
        for col in self.columns:
            sql += f"`{col.name}`"
            if col.length is not None:
                sql += f"({col.length})"
            sql += "),"

        return sql


@dataclass
class Column(NameMixin):
    """Represents a column within a table definition"""
    datatype: str
    modifiers: str
    auto_inc: bool = field(default_factory=bool)
    auto_inc_val: int = field(default_factory=int)
    starting_auto_inc_val: int = field(default=-1)

    def __post_init__(self):
        super().__post_init__()
        self.datatype = self.datatype.strip()
        self.modifiers = self.modifiers.strip()

    # TODO we added the auto_increment stuff to the modifiers field
    def _get_modifier_str(self):
        m = re.search(r"^(.+?) AUTO_INCREMENT", self.modifiers)
        if m:
            modstr = m.group(1)
        else:
            modstr = self.modifiers
        if self.auto_inc:
            modstr += " AUTO_INCREMENT"
        return modstr

    def _get_sql_str(self, terminator: str, modstr: str) -> str:
        sql = f" `{self.name}` {self.datatype} {modstr}{terminator}"
        return sql

    def generate_sql(self, terminator: str = ",") -> str:
        modstr = self._get_modifier_str()
        return self._get_sql_str(terminator, modstr)

    def generate_autoinc_sql(self, terminator: str = ",", autoinc_val: int | None = None) -> str:
        if autoinc_val is not None:
            self.auto_inc_val = autoinc_val
        modstr = self._get_modifier_str()
        modstr += f" AUTO_INCREMENT, AUTO_INCREMENT={self.auto_inc_val}"
        return self._get_sql_str(terminator, modstr)

    def next_autoinc_val(self) -> int:
        assert self.auto_inc, "This only works on auto-increment columns"
        val = self.auto_inc_val
        self.auto_inc_val += 1
        return val


@dataclass
class Table(Intermediate, NameMixin):
    """Represents a table definition"""
    columns: List[Column]
    timestamp_columns: List[str] = field(default_factory=list)
    post_definition_modifiers: str = field(default="")
    use_time_based_comparison: bool = field(default=False)
    _keys: List[Key] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.timestamp_columns = Settings.obj().get_timestamp_cols(self.name)
        self.use_time_based_comparison = Settings.obj().get_use_time_based_comparison(self.name)

        primary_cols = Settings.obj().get_synthetic_primary_key(self.name)
        if primary_cols is not None:
            columns = [KeyColumn(name, None) for name in primary_cols]
            primary = Key(self.name, columns, is_primary=True)
            self.append_key(primary)

        unique_cols = Settings.obj().get_synthetic_unique_key(self.name)
        if unique_cols is not None:
            existing = self.get_unique_key()
            if existing is not None:
                msg = f"Table {self.name} already has a unique key - can't add a synthetic one"
                raise DbSyncCompareException(msg)
            columns = [KeyColumn(name, None) for name in unique_cols]
            synth = Key(self.name, columns, is_unique=True)
            self.append_key(synth)

    @property
    def count(self) -> int:
        """Returns the number of columns in the table"""
        return len(self.columns)

    @property
    def keys(self) -> List[Key]:
        return self._keys

    def get_primary_key(self) -> Key | None:
        """Returns the primary key, if any"""
        keys = [key for key in self.keys if key.is_primary]
        return self._return_key(keys, "primary")

    def has_primary_key(self) -> bool:
        return self.get_primary_key() is not None

    def get_unique_key(self) -> Key | None:
        """Returns the unique key, if any"""
        keys = [key for key in self.keys if key.is_unique]
        return self._return_key(keys, "unique")

    def get_comparison_key(self) -> Key | None:
        key = self.get_unique_key()
        if key is None:
            key = self.get_primary_key()
        return key

    def _return_key(self, keys: List[Key], name: str) -> Key | None:
        if len(keys) == 0:
            return None
        elif len(keys) == 1:
            return keys[0]
        else:
            raise DbSyncCompareException(f"Table has multiple {name} keys - \
                                         I assumed there would be at most 1")

    def has_unique_key(self) -> bool:
        return self.get_unique_key() is not None

    def has_timestamp(self) -> bool:
        return len(self.timestamp_columns) > 0

    def get_create_time_column_name(self) -> str | None:
        if len(self.timestamp_columns) > 0:
            # create time is last in list
            return self.timestamp_columns[-1]
        return None

    def append_key(self, key: Key) -> None:
        if key.is_primary and self.has_primary_key():
            self._print_verbose(f"Ignoring primary key in SQL. \
Table {self.name} already has a (possibly synthetic) primary key.")
        elif key.is_unique and self.has_unique_key():
            self._print_verbose(f"Ignoring unique key in SQL. \
Table {self.name} already has a (possibly synthetic) unique key.")
        else:
            self.keys.append(key)

    def get_column_names(self) -> List[str]:
        return [c.name for c in self.columns]

    def get_column(self, name: str) -> Column:
        """Gets a column by name"""
        col = [c for c in self.columns if c.name == name]
        if len(col) == 0:
            msg = f"No column \"{name}\" in table"
            raise DbSyncCompareException(msg)
        return col[0]

    def _start_sql(self, keyword: str, alt_name: str = None) -> str:
        if alt_name is None:
            table_name = self.name
        else:
            table_name = alt_name

        return f"{keyword} TABLE `{table_name}`"

    def generate_sql(self, alt_name: str = None) -> str:
        sql = []
        sql.append(self._start_sql("CREATE", alt_name) + " (")
        for col in self.columns:
            sql.append(col.generate_sql())
        for key in self.keys:
            sql.append(key.generate_sql())
        # get rid of final comma
        sql[-1] = sql[-1].rstrip(",")
        sql.append(f") {self.post_definition_modifiers};")
        return "\n".join(sql)

    def _get_autoinc_column(self) -> Column | None:
        autoinc_cols = [c for c in self.columns if c.auto_inc]
        if len(autoinc_cols) == 1:
            return autoinc_cols[0]
        else:
            quantity = "no" if len(autoinc_cols) == 0 else "multiple"
            msg = f"Table {self.name} has {quantity} autoinc column(s)"
            raise DbSyncCompareException(msg)

    def get_autoinc_column_name(self) -> str | None:
        autoinc_cols = [c for c in self.columns if c.auto_inc]
        if len(autoinc_cols) == 1:
            return autoinc_cols[0].name
        else:
            return None

    def has_autoinc_column(self) -> bool:
        autoinc_cols = [c for c in self.columns if c.auto_inc]
        return len(autoinc_cols) > 0

    def get_autoinc_val(self) -> int:
        autoinc_col = self._get_autoinc_column()
        if autoinc_col is not None:
            return autoinc_col.auto_inc_val
        return -1

    def get_starting_autoinc_val(self) -> int:
        autoinc_col = self._get_autoinc_column()
        if autoinc_col is not None:
            return autoinc_col.starting_auto_inc_val
        return -1

    def update_autoinc_val(self, newval: int) -> None:
        autoinc_col = self._get_autoinc_column()
        if autoinc_col is not None:
            autoinc_col.auto_inc_val = newval
            if autoinc_col.starting_auto_inc_val < 0:
                autoinc_col.starting_auto_inc_val = newval

    def next_autoinc_val(self) -> int:
        autoinc_col = self._get_autoinc_column()
        return autoinc_col.next_autoinc_val()

    def disable_autoinc(self, alt_name: str = None, autoinc_val: int | None = None) -> str:
        sql = []
        autoinc_col = self._get_autoinc_column()
        if autoinc_col is not None:
            if alt_name is None:
                alt_name = self.name

            if Settings.obj().dml_options == DmlOptions.DISABLE_AUTO_INCREMENT:
                sql.append("-- Disable auto-increment")
                sql.append(self._start_sql("ALTER", alt_name))
                sql.append("  MODIFY" + autoinc_col.generate_sql(";"))
            elif Settings.obj().dml_options == DmlOptions.GENERATE_LOCK_TABLES:
                sql.append(f"LOCK TABLES `{alt_name}` WRITE;")
                sql.append(f"/*!40000 ALTER TABLE `{alt_name}` DISABLE KEYS */;")
                sql.append(f"/*!ALTER TABLE `{alt_name}` AUTO_INCREMENT={autoinc_val} */;")
        return "\n".join(sql)

    def enable_autoinc(self, alt_name: str = None, autoinc_val: int | None = None) -> str:
        sql = []
        autoinc_col = self._get_autoinc_column()
        if autoinc_col is not None:
            if alt_name is None:
                alt_name = self.name

            if Settings.obj().dml_options == DmlOptions.DISABLE_AUTO_INCREMENT:
                sql.append("-- Enable auto-increment")
                sql.append(self._start_sql("ALTER", alt_name))
                sql.append("  MODIFY" + autoinc_col.generate_autoinc_sql(";", autoinc_val))
            elif Settings.obj().dml_options == DmlOptions.GENERATE_LOCK_TABLES:
                sql.append(f"/*!40000 ALTER TABLE `{alt_name}` ENABLE KEYS */;")
                sql.append("UNLOCK TABLES;")
        return "\n".join(sql)

    def truncate(self) -> str:
        sql = []
        sql.append("-- Copy src table to dst")
        sql.append(f"TRUNCATE TABLE `{self.name}`;")
        return "\n".join(sql)


@dataclass
class Insert(Intermediate, NameMixin):
    """Represents a simple insert statement with values"""
    columns: List[str]
    values: List[List[str]]


@dataclass
class Set(Intermediate):
    """Represents a set statement"""
    value: str

    def dont_use_generate_sql(self) -> str:
        # The value is "X = Y"
        return f"SET {self.value};"


@dataclass
class Use(Intermediate):
    """Represents a USE statement"""
    value: str
    is_target: bool = field(default=False)

    def __post_init__(self):
        self.value = Quoted.fix_name(self.value)

    def generate_sql(self) -> str:
        """Returns a USE and START TRANSACTION"""
        if not self.is_target:
            return ""

        return f"""SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
SET time_zone = "+00:00";
USE `{self.value}`;
-- Note: there is no commit at the end of the file
-- DON'T FORGET TO TURN OFF AUTO-COMMIT!
START TRANSACTION;"""


@dataclass
class Alteration(Intermediate, NameMixin):
    """Base class for alter statements"""
    pass


@dataclass
class KeyList(Alteration):
    """Represents key specifications in an ALTER TABLE statement"""
    keys: List[Key]


@dataclass
class Modification(Alteration):
    """Represents a modification, typically to add autoincrement to a column"""
    columns: List[Column]
