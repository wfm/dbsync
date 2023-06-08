"""Intermediate representations of SQL statements"""

import re
from dataclasses import dataclass, field
from typing import List

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
    pass


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


@dataclass
class Column(NameMixin):
    """Represents a column within a table definition"""
    datatype: str
    modifiers: str
    auto_inc: bool = field(default_factory=bool)
    auto_inc_val: int = field(default_factory=int)

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


@dataclass
class Table(Intermediate, NameMixin):
    """Represents a table definition"""
    columns: List[Column]
    timestamp_columns: List[str] = field(default_factory=list)
    post_definition_modifiers: str = field(default="")
    keys: List[Key] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.timestamp_columns = Settings.obj().get_timestamp_cols(self.name)

    @property
    def count(self) -> int:
        """Returns the number of columns in the table"""
        return len(self.columns)

    @property
    def primary_keys(self) -> List[str]:
        """Returns the names of the PK columns"""
        pk = [key for key in self.keys if key.is_primary]
        if len(pk) == 1:
            names = [c.name for c in pk[0].columns]
            return names
        raise DbSyncCompareException("Table has no primary key columns")

    def get_unique_key(self) -> Key | None:
        """Returns the unique key, if any"""
        keys = [key for key in self.keys if key.is_unique]
        if len(keys) == 0:
            return None
        elif len(keys) == 1:
            return keys[0]
        else:
            raise DbSyncCompareException("Table has multiple unique keys - \
                                         I assumed there would be at most 1")

    def append_key(self, key: Key) -> None:
        self.keys.append(key)

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
        # get rid of final comma
        sql[-1:][0].rstrip(",")

        sql.append(f") {self.post_definition_modifiers};")
        return "\n".join(sql)

    def _get_autoinc_column(self) -> Column | None:
        autoinc_cols = [c for c in self.columns if c.auto_inc]
        if len(autoinc_cols) == 0:
            return None
        elif len(autoinc_cols) == 1:
            return autoinc_cols[0]
        else:
            raise DbSyncCompareException("Multiple autoinc columns found")

    def get_autoinc_val(self) -> int:
        autoinc_col = self._get_autoinc_column()
        if autoinc_col is not None:
            return autoinc_col.auto_inc_val
        return -1

    def update_autoinc_val(self, newval: int) -> None:
        autoinc_col = self._get_autoinc_column()
        if autoinc_col is not None:
            autoinc_col.auto_inc_val = newval

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
