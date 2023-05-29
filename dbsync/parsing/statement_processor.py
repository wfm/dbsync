from typing import List

from sqlparse import sql
from sqlparse import tokens as T

from dbsync.exceptions import DbSyncException, DbSyncParseException
from dbsync import intermediate as IM
from dbsync.parsing.sql_statement import SqlStatement
from dbsync.parsing.alter_statement import AlterStatement
from dbsync.parsing.create_table_statement import create_table
from dbsync.parsing.insert_statement import insert_data
from dbsync.comparing.comparison_repo import ComparisonRepo


def set_statement(ss: SqlStatement) -> IM.Set:
    t = ss.get_token()
    if isinstance(t, sql.Comparison):
        return IM.Set(t.value)
    raise DbSyncParseException("Invalid SET statement")


def use_statement(ss: SqlStatement) -> IM.Use:
    t = ss.get_token()
    return IM.Use(t.value)



def process_statements(text_l: List[str], target_database: str) -> ComparisonRepo:
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
                us = use_statement(ss)
                repo.append(us)
                before_use = False
                us.is_target = us.value == target_database

                print("-- db:", us.value, "in_target:", us.is_target)
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
