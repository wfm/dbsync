
"""Intermediate representations of SQL statements"""

from dataclasses import dataclass
from typing import List


@dataclass
class Intermediate:
    """Base class for the rest of the classes in this module"""
    pass


@dataclass
class Column:
    """Represents a column within a table definition"""
    name: str
    datatype: str
    modifiers: str


@dataclass
class Table(Intermediate):
    """Represents a table definition"""
    name: str
    columns: List[Column]

    @property
    def count(self):
        """Returns the number of columns in the table"""
        return len(self.columns)


@dataclass
class Insert(Intermediate):
    """Represents a simple insert statement with values"""
    into_table: str
    columns: str
    values: List[List[str]]


@dataclass
class Set(Intermediate):
    """Represents a set statement"""
    value: str


@dataclass
class Alteration(Intermediate):
    """Base class for alter statements"""
    name: str


@dataclass
class PrimaryKey(Alteration):
    """Represents a primary key specification"""
    primary_keys: List[int]


@dataclass
class Modification(Alteration):
    """Represents a modification, typically to add autoincrement to a column"""
    columns: List[Column]
