import sys
import sqlparse
from sqlparse import sql
from sqlparse import tokens as T
from typing import List

from dbsync.exceptions import DbSyncException, DbSyncParseException
from dbsync import constants as C
from dbsync import intermediate as IM
from dbsync.parsing.sql_statement import SqlStatement
from dbsync.parsing.alter_statement import AlterStatement
from dbsync.parsing.create_table_statement import create_table
from dbsync.parsing.utilities \
    import match_tokens, get_id_list_tokens
from dbsync.comparing.comparison_repo import ComparisonRepo


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
            # TODO was having trouble with this:
            # ["staging_NhU_wps_hit", "`staging_NhU_wps_hit`"]:
            values = get_values(t, column_count)

            return IM.Insert(name, columns, values)
    raise DbSyncParseException("Invalid INSERT statement")


def set_statement(ss: SqlStatement) -> IM.Set:
    t = ss.get_token()
    if isinstance(t, sql.Comparison):
        return IM.Set(t.value)
    raise DbSyncParseException("Invalid SET statement")


def process_statements(text_l):
    in_target = False
    before_use = True
    repo = ComparisonRepo()

    def add_parsed(f):
        if in_target:
            x = f()
            if x is not None:
                repo.append(x)

    for text in text_l:
        try:
            ss = SqlStatement(text)
            t = ss.get_token()
            if t is None:
                continue
            elif t.match(T.DDL, "CREATE"):
                t = ss.get_token()
                if t.value == "TABLE":
                    add_parsed(lambda p=ss: create_table(p))
                # CREATE DATABASE is not supported
            elif t.match(T.DML, "INSERT"):
                add_parsed(lambda p=ss: insert_data(p))
            elif t.match(T.Keyword, "SET"):
                if before_use:
                    repo.append(set_statement(ss))
                else:
                    add_parsed(lambda p=ss: set_statement(p))
            elif t.match(T.DML, "START"):
                # don't think we need this
                continue
            elif t.match(T.Keyword, "USE"):
                t = ss.get_token()
                dbname = t.value
                in_target = dbname == C.TARGET_DATABASE
                before_use = False
                print("db:", dbname, "in_target:", in_target)
            elif t.match(T.DDL, "ALTER"):
                add_parsed(lambda a=AlterStatement(), p=ss: a.parse(p))
            elif in_target:
                print("Got something else:", repr(t))
                while t is not None:
                    t = ss.get_token()
                    print(" ", repr(t))
                print("SQL:", text)
                exit()

        except DbSyncException as err:
            print(f"{type(err)} - {err}")
            print(f"Index: {ss.token_ix}")
            print(f"SQL: {text}")

    return repo


def main():
    filename = sys.argv[1]
    print("db-compare of", filename)
    with open(filename, "r", encoding="utf8") as f:
        text_l = sqlparse.split(f.read())

    repo = process_statements(text_l)

    print("Parsed statements:")
    for p in repo.parsed:
        print(p)

    return 0
