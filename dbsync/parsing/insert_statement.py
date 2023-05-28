"""Parses insert statements"""

from sqlparse import sql
from typing import List

from dbsync.settings import Settings
from dbsync.exceptions import DbSyncParseException
from dbsync import constants as C
from dbsync import intermediate as IM
from dbsync.parsing.sql_statement import SqlStatement
from dbsync.parsing.utilities \
    import match_tokens, get_id_list_tokens


def get_values(tokens: sql.TokenList, column_count: int) -> List[List[str]]:
    """ Gets the values from an insert statement """
    def get_next_row(tl: sql.TokenList) -> List[str]:
        row = []
        iss = SqlStatement(None, tl)
        iss.eat_token(C.LPAREN_TOKEN)
        while len(row) < column_count:
            it = iss.get_token()
            if it is None or match_tokens(it, C.RPAREN_TOKEN):
                break
            elif match_tokens(it, C.COMMA_TOKEN):
                continue
            elif isinstance(it, sql.IdentifierList):
                idl = get_id_list_tokens(it)
                row += [x.value for x in idl]
            else:
                row.append(it.value)

        if len(row) != column_count:
            msg = f"Incorrect number of values in row initializer - \
                expected {column_count}, got: {len(row)}"
            raise DbSyncParseException(msg)
        iss.eat_token(C.RPAREN_TOKEN)
        return row

    values = []
    ss = SqlStatement(None, tokens)
    expected = C.VALUES_TOKEN

    while True:
        try:
            ss.eat_token(expected)
            t = ss.get_token()
            values.append(get_next_row(t))
            expected = C.COMMA_TOKEN
        except EOFError:
            break

    return values


def insert_data(ss: SqlStatement) -> IM.Insert:
    ss.get_token()  # INTO
    t = ss.get_token()
    if isinstance(t, sql.Function):
        name = t.get_name()
        if not Settings.obj().should_include_table(name):
            return None

        params = t.get_parameters()
        columns = []
        while True:
            try:
                ident = next(params)
                columns.append(ident.get_name())
            except StopIteration:
                break

        column_count = len(columns)
        t = ss.get_token()
        if isinstance(t, sql.Values):
            values = get_values(t, column_count)

            return IM.Insert(name, columns, values)
    raise DbSyncParseException("Invalid INSERT statement")
