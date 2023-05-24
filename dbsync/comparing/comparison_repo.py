"""Data structures to store intermediate representations of the SQL"""

from typing import List, Dict

from dbsync import intermediate as IM
from dbsync.exceptions import DbSyncCompareException


class ComparisonRepo:
    """The repository of the data used in comparing the tables"""
    def __init__(self):
        # statments in the order in which they occur in the file
        self.parsed: List[IM.Intermediate] = []
        # DDL to create tables, by table name
        self.tables: Dict(str, IM.Table) = {}
        # Insert statments after they have been coalesced
        self.inserts: Dict(str, IM.Insert) = {}

    def append(self, item: IM.Intermediate) -> None:
        self.parsed.append(item)

        if isinstance(item, IM.Table):
            table: IM.Table = item  # does one do this in python?
            if self.tables.get(table.name):
                msg = f"Table {table.name} was already added"
                raise DbSyncCompareException(msg)

            self.tables[table.name] = table

    def get_table(self, name: str) -> IM.Table | None:
        """Returns the table by name"""
        return self.tables.get(name)
