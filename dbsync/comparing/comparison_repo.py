"""Data structures to store intermediate representations of the SQL"""

import re
from typing import List, Dict

from dbsync import intermediate as IM
from dbsync.comparing.unpacked_insert import UnpackedInsert
from dbsync.exceptions import DbSyncCompareException


class ComparisonRepo:
    _auto_inc_re = re.compile(r"\bAUTO_INCREMENT\s*=\s*(\d+)")

    """The repository of the data used in comparing the tables"""
    def __init__(self):
        # statments in the order in which they occur in the file
        self.parsed: List[IM.Intermediate] = []
        # DDL to create tables, by table name
        self.tables: Dict[str, IM.Table] = {}
        # Insert statments after they have been coalesced
        self.inserts: Dict[str, List[UnpackedInsert]] = {}
        # used to output tables in correct order
        self.order = 0

    def __iter__(self):
        """Iterates through the list of parsed statements"""
        # not 100% sure what I'm doing here
        for p in self.parsed:
            yield p

    def __str__(self) -> str:
        return f"Repo statments: {len(self.parsed)}, \
tables: {len(self.tables)}, \
inserts: {len(self.inserts)}"
 
    def __repr__(self):
        return f"""Parsed statements:
{self.parsed}
Tables:
{self.tables}
Insert statements:
{self.inserts}
"""

    def append(self, item: IM.Intermediate) -> None:
        """Appends the representation of a SQL statement to the repo"""
        self.parsed.append(item)

        if isinstance(item, IM.Table):
            table: IM.Table = item  # does one do this in python?
            if self.tables.get(table.name):
                msg = f"Table {table.name} was already added"
                raise DbSyncCompareException(msg)

            self.tables[table.name] = table

    def _add_pk(self, pk):
        tbl = self.get_table(pk.name)
        tbl.primary_keys = pk.primary_keys

    def _update_columns(self, mod):
        tbl = self.get_table(mod.name)
        for col in mod.columns:
            tcol = tbl.get_column(col.name)
            tcol.datatype = col.datatype
            tcol.modifiers = col.modifiers
            ComparisonRepo._set_auto_inc(tcol)

    @classmethod
    def _set_auto_inc(cls, col):
        m = cls._auto_inc_re.search(col.modifiers)
        if m:
            col.auto_inc = True
            col.auto_inc_val = int(m.group(1))
        else:
            col.auto_inc = False

    def _add_insert(self, insert: IM.Insert) -> None:
        """Merge insert statements for same table, same columns"""
        table = self.get_table(insert.name)
        existing = self.get_inserts(insert.name)
        unpacked = UnpackedInsert(table, insert)
        updated = False
        for e in existing:
            if insert.columns == e.columns:
                e.values += unpacked.values
                e.dedup()
                updated = True
                break

        if not updated:
            existing.append(unpacked)
            self.inserts[insert.name] = existing

    def post_process(self):
        """Post-processing: updates pks, auto_inc, and inserts"""
        for im in self.parsed:
            if isinstance(im, IM.PrimaryKey):
                self._add_pk(im)
            elif isinstance(im, IM.Modification):
                self._update_columns(im)

        # need to update the tables before we can do this
        for im in self.parsed:
            if isinstance(im, IM.Insert):
                self._add_insert(im)

    def get_table_names(self) -> List[str]:
        """Returns a list of the table names"""
        return list(self.tables.keys())

    def get_table(self, name: str) -> IM.Table:
        """Returns a table by name"""
        tbl = self.tables.get(name)
        if tbl is None:
            raise DbSyncCompareException(f"No table \"{name}\"")
        return tbl

    def get_inserts(self, name: str) -> List[UnpackedInsert]:
        """Gets the insert statements into a particular table"""
        return self.inserts.get(name, [])
