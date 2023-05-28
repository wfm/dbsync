"""Intermediate representations of SQL statements"""

import re
from dataclasses import dataclass, field
from typing import List

from dbsync.exceptions import DbSyncCompareException


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
class Column(NameMixin):
    """Represents a column within a table definition"""
    datatype: str
    modifiers: str
    auto_inc: bool = field(default_factory=bool)
    auto_inc_val: int = field(default_factory=int)

    # TODO we added the auto_increment stuff to the modifiers field
    def generate_sql(self) -> str:
        m = re.search(r"^(.+?) AUTO_INCREMENT", self.modifiers)
        if m:
            modstr = m.group(1)
        else:
            modstr = self.modifiers

        sql = f"  `{self.name}` {self.datatype} {modstr},"
        return sql


@dataclass
class Table(Intermediate, NameMixin):
    """Represents a table definition"""
    columns: List[Column]
    primary_keys: List[str] = field(default_factory=list)

    @property
    def count(self):
        """Returns the number of columns in the table"""
        return len(self.columns)

    def get_column(self, name):
        """Gets a column by name"""
        col = [c for c in self.columns if c.name == name]
        if len(col) == 0:
            msg = f"No column \"{name}\" in table"
            raise DbSyncCompareException(msg)
        return col[0]

    def generate_sql(self, alt_name=None):
        sql = []
        if alt_name is None:
            table_name = self.name
        else:
            table_name = alt_name

        sql.append(f"CREATE TABLE `{table_name}` (")
        for col in self.columns:
            sql.append(col.generate_sql())
        # get rid of final comma
        sql[-1:][0].rstrip(",")
        # TODO should get all this crap from the prod table definition
        sql.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 \
                   COLLATE=utf8mb4_unicode_520_ci;")
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

    def generate_sql(self):
        # value is SET X = Y
        return f"SET {self.value}"


@dataclass
class Use(Intermediate):
    """Represents a USE statement"""
    value: str
    is_target: bool = field(default=False)

    def __post_init__(self):
        self.value = Quoted.fix_name(self.value)

    def generate_sql(self):
        """Returns a USE and START TRANSACTION"""
        if not self.is_target:
            return ""

        return f"""USE `{self.value}`;
-- Note: there is no commit at the end of the file
START TRANSACTION;"""


@dataclass
class Alteration(Intermediate, NameMixin):
    """Base class for alter statements"""
    pass


@dataclass
class PrimaryKey(Alteration):
    """Represents a primary key specification"""
    primary_keys: List[str]

    def __post_init__(self):
        self.primary_keys = [Quoted.fix_name(n) for n in self.primary_keys]


@dataclass
class Modification(Alteration):
    """Represents a modification, typically to add autoincrement to a column"""
    columns: List[Column]
