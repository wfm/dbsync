"""Exceptions for the dbsync package"""


class DbSyncException(Exception):
    """Base class for dbsync exceptions"""


class DbSyncParseException(DbSyncException):
    """Exceptions in the parser section of the dbsync package"""


class DbSyncCompareException(DbSyncException):
    """Exceptions in the comparison section of the dbsync package"""
