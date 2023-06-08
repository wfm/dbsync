from sqlparse import sql
from typing import List

from dbsync.exceptions import DbSyncParseException
from dbsync import constants as C
from dbsync import intermediate as IM
from dbsync.parsing.sql_statement import SqlStatement
from dbsync.parsing.create_table_statement import ColumnList
from dbsync.parsing.utilities import match_tokens
from dbsync.settings import Settings


class AlterStatement:
    def _surround_with_parens(self, ss: SqlStatement) -> sql.TokenList:
        rest = ss.get_tokens_to_eol()

        # surround column def with parens so we can parse it
        iss = SqlStatement(None, rest)
        iss.get_token()
        first_ix = iss.token_ix
        # it seems to work, so i don't want to touch it, but i think
        # that inserting the lparen would shift the last token
        # right by one:
        last_ix = len(rest.tokens) - 1
        rest.insert_before(first_ix, C.LPAREN_TOKEN)
        if match_tokens(rest.tokens[last_ix], C.SEMICOLON_TOKEN):
            rest.insert_before(last_ix, C.RPAREN_TOKEN)
        else:
            rest.insert_after(last_ix, C.RPAREN_TOKEN)
        return rest

    def _parse_modify(self, name: str, ss: SqlStatement) -> IM.Modification:
        ss.eat_token(C.MODIFY_TOKEN)
        rest = self._surround_with_parens(ss)
        cl = ColumnList()
        cols, _ = cl.get_columns(rest)
        return IM.Modification(name, cols)

    def _parse_add_keys(self, name: str, ss: SqlStatement) -> List[IM.Key]:
        rest = self._surround_with_parens(ss)
        cl = ColumnList()
        _, keys = cl.get_columns(rest)
        return IM.KeyList(name, keys)

    def parse(self, ss: SqlStatement) -> IM.Alteration:
        ss.eat_token(C.TABLE_TOKEN)
        t = ss.get_token()
        if (isinstance(t, sql.Identifier)):
            name = t.get_name()
            if not Settings.obj().should_include_table(name):
                return None
        else:
            raise DbSyncParseException(f"Expected Identifier, got {type(t)}")

        # there are a lot of possible variations on the ALTER statement
        # this supports ALTER TABLE <name> MODIFY and
        # ALTER TABLE <name> ADD PRIMARY KEY
        t = ss.peek_token()
        if match_tokens(t, C.MODIFY_TOKEN):
            return self._parse_modify(name, ss)
        elif match_tokens(t, C.ADD_TOKEN):
            return self._parse_add_keys(name, ss)

        raise DbSyncParseException(f"Not sure how to process ALTER TABLE...{t.value}")
