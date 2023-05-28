from sqlparse import sql
from enum import IntEnum

from dbsync.exceptions import DbSyncParseException
from dbsync import constants as C
from dbsync import intermediate as IM
from dbsync.parsing.sql_statement import SqlStatement
from dbsync.parsing.create_table_statement import get_columns
from dbsync.parsing.utilities import match_tokens
from dbsync.settings import Settings


class State(IntEnum):
    ADD = 1
    PRIMARY = 2
    KEY = 3
    PK_SUCCESS = 4


class AlterStatement:
    _state_tokens = {
        State.ADD: C.ADD_TOKEN,
        State.PRIMARY: C.PRIMARY_TOKEN,
        State.KEY: C.KEY_TOKEN
    }

    def _parse_modify(self, name: str, ss: SqlStatement) -> IM.Modification:
        ss.eat_token(C.MODIFY_TOKEN)
        rest = ss.get_tokens_to_eol()

        # surround column def with parens so we can parse it
        iss = SqlStatement(None, rest)
        iss.get_token()
        first_ix = iss.token_ix
        # it seems to work, so i don't want to touch it, but i think
        # that inserting the lparen would shift the last token
        # right by one:
        last_ix = len(rest.tokens)-1
        rest.insert_before(first_ix, C.LPAREN_TOKEN)
        if match_tokens(rest.tokens[last_ix], C.SEMICOLON_TOKEN):
            rest.insert_before(last_ix, C.RPAREN_TOKEN)
        else:
            rest.insert_after(last_ix, C.RPAREN_TOKEN)

        cols = get_columns(rest)
        return IM.Modification(name, cols)

    def _parse_add_pk(self, name: str, ss: SqlStatement) -> IM.PrimaryKey:
        pk_columns = []
        state = State.ADD
        while state != State.PK_SUCCESS:
            t = ss.get_token()
            if t is None:
                break
            statok = AlterStatement._state_tokens[state]
            if t.match(statok.ttype, statok.value):
                state += 1
            else:
                state = State.ADD

        if state == State.PK_SUCCESS:
            debug = name == "NhU_term_relationships"
            if debug:
                print(f"ALTER for table {name}")
            t = ss.get_token()
            if (isinstance(t, sql.Parenthesis)):
                iss = SqlStatement(None, t)
                iss.eat_token(C.LPAREN_TOKEN)
                it = iss.get_token()
                while it is not None and not match_tokens(it, C.RPAREN_TOKEN):
                    if debug:
                        print(f"PK column: {it.value}")
                    pk_columns += it.value.split(",")
                    it = iss.get_token()
                return IM.PrimaryKey(name, pk_columns)

        raise DbSyncParseException("Invalid ALTER statment")

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

        return self._parse_add_pk(name, ss)
