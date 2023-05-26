"""Generates SQL for Intemediate data"""

import re
from typing import List, Dict
from dataclasses import dataclass, field

from dbsync import intermediate as IM
from dbsync.comparing.comparison_repo import ComparisonRepo
from dbsync.comparing.unpacked_insert import UnpackedInsert
from dbsync.exceptions import DbSyncCompareException


# class Column(NameMixin):
# class Table(Intermediate, NameMixin):
# don't need: class Insert(Intermediate, NameMixin):
# class Set(Intermediate):
# class Use(Intermediate):
# class Alteration(Intermediate, NameMixin):
# class PrimaryKey(Alteration):
# class Modification(Alteration):
# InsertRecord
