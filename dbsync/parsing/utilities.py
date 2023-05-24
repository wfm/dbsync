"""Utilities for working with sqlparse"""

from sqlparse import sql
from typing import List

from dbsync.parsing.sql_statement import SqlStatement


def match_tokens(ltoken: sql.Token, rtoken: sql.Token) -> bool:
    """
    Compares two tokens and returns true if the ttype and value are equal
    """
    return ltoken.match(rtoken.ttype, rtoken.value)


def get_id_list_tokens(il: sql.IdentifierList) -> List[sql.Token]:
    tokens = []
    identifiers = il.get_identifiers()
    while True:
        try:
            item = next(identifiers)
            if SqlStatement.get_dump_tokens():
                print("il:", repr(item))
            tokens.append(item)
        except StopIteration:
            break

    return tokens


def get_flattened_tokens(tl: sql.TokenList) -> List[sql.Token]:
    tokens = []
    flat = tl.flatten()
    while True:
        try:
            item = next(flat)
            if SqlStatement.get_dump_tokens():
                print("fl", repr(item))
            tokens.append(item)
        except StopIteration:
            break

    return tokens
