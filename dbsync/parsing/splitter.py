from typing import List

from sqlparse import sql
from sqlparse import tokens as T

from dbsync.exceptions import DbSyncParseException
from dbsync.parsing.sql_statement import SqlStatement
from dbsync.parsing.statement_processor import use_statement
from dbsync.parsing.utilities import match_tokens
from dbsync.settings import Settings
from dbsync.intermediate import Quoted
import dbsync.constants as C


class Splitter:
    def __init__(self):
        self.target_database = Settings.obj().db_name
        self.in_target = False

    def separate_statements(self, text_l: List[str]) -> None:
        filename = Settings.obj().output_file
        src_filemame = filename.replace(".sql", "_src.sql")
        dst_filemame = filename.replace(".sql", "_dst.sql")
        with open(src_filemame, "w", encoding="utf8") as src_file, \
             open(dst_filemame, "w", encoding="utf8") as dst_file:
            for text in text_l:
                x = self._classify_statement(text)
                if x < 0:
                    src_file.write(text)
                elif x > 0:
                    dst_file.write(text)

    def _classify_statement(self, text: str) -> int:
        ss = SqlStatement(text)
        token = ss.get_token()
        if token is None:
            print("Token is None. SQL:")
            print(text)
            return 1

        if token.match(T.Keyword, "USE"):
            us = use_statement(ss)
            self.in_target = us.value == self.target_database
            print(f"USE {us.value} -> {self.in_target}")
        elif self.in_target:
            if token.match(T.DDL, "CREATE"):
                return self._classify_table(ss)
            if token.match(T.DML, "INSERT"):
                return self._classify_insert(ss)
            if token.match(T.DDL, "ALTER"):
                return self._classify_alter(ss)
        return 0

    def _classify_table(self, ss: SqlStatement) -> int:
        token = ss.get_token()
        if match_tokens(token, C.TABLE_TOKEN):
            token = ss.get_token()
            if isinstance(token, sql.Identifier):
                name = token.value
                return self._is_src_or_dst(name)
            else:
                raise DbSyncParseException(f"Expected an identifier, got {repr(token)}")
        return 0

    def _classify_insert(self, ss: SqlStatement) -> int:
        # TODO there are other keywords that could precede the name
        # INSERT [LOW_PRIORITY | DELAYED | HIGH_PRIORITY] [IGNORE] [INTO] tbl_name
        token = ss.get_token()
        if match_tokens(token, C.INTO_TOKEN):
            token = ss.get_token()
        if isinstance(token, sql.Function):
            name = token.get_name()
            return self._is_src_or_dst(name)
        else:
            raise DbSyncParseException(f"Expected an identifier, got {repr(token)}")

    def _classify_alter(self, ss: SqlStatement) -> int:
        token = ss.get_token()
        if match_tokens(token, C.TABLE_TOKEN):
            token = ss.get_token()
            if isinstance(token, sql.Identifier):
                name = token.value
                return self._is_src_or_dst(name)
            else:
                raise DbSyncParseException(f"Expected an identifier, got {repr(token)}")
        return 0

    def _is_src_or_dst(self, name: str) -> int:
        # TODO handle non-blank src prefix
        name = Quoted.fix_name(name)
        if name.startswith(Settings.obj().dst_prefix):
            return 1
        elif name.startswith(Settings.obj().tbl_prefix):
            return -1
        raise DbSyncParseException(f"Weird name token: {name}")
