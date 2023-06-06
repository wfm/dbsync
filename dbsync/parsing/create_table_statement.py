"""Parses create table statements"""

from sqlparse import sql
from sqlparse import tokens as T
from enum import IntEnum
from typing import List, Tuple

from dbsync.exceptions import DbSyncParseException
from dbsync import constants as C
from dbsync import intermediate as IM
from dbsync.parsing.sql_statement import SqlStatement
from dbsync.parsing.utilities \
    import match_tokens, get_flattened_tokens, get_id_list_tokens
from dbsync.settings import Settings


# Maybe this should go back to alter_statement.py:
def get_pk_columns(name: str, ss: SqlStatement) -> List[str]:
    pk_columns = []
    t = ss.get_token()
    if (isinstance(t, sql.Parenthesis)):
        iss = SqlStatement(None, t)
        iss.eat_token(C.LPAREN_TOKEN)
        it = iss.get_token()
        while it is not None and not match_tokens(it, C.RPAREN_TOKEN):
            pk_columns += it.value.split(",")
            it = iss.get_token()

    return IM.PrimaryKey(name, pk_columns)


def get_columns(tl: sql.TokenList) -> Tuple[List[IM.Column], IM.PrimaryKey]:
    """ Gets column definitions for a CREATE TABLE statement """
    class State(IntEnum):
        OPEN_PAREN = 0
        IDENTIFIER = 1
        DATA_TYPE = 2
        POST_DATA_TYPE = 3
        DATA_SIZE = 4
        MODIFIERS = 5
        KEY = 6
        PK_START = 7
        PK_COLS = 8
        PK_END = 9
        CLOSE_PAREN = 10

    state = State.OPEN_PAREN
    cols: List[IM.Column] = []
    tokens = get_flattened_tokens(tl)
    name = ""
    datatype = ""
    modifiers = []
    has_auto_increment = False
    grab_auto_increment_value = False
    auto_increment_value = 0
    pk_columns = []

    def check_for_end_of_column(t: T.Token, is_column: bool = True) -> bool:
        nonlocal state

        at_end = False
        # lol, comma ends a column def except when it doesn't
        # in particular, we have AUTO_INCREMENT, AUTO_INCREMENT=1244
        # on modify statements
        if match_tokens(t, C.COMMA_TOKEN):
            state = State.IDENTIFIER
            at_end = True
        elif match_tokens(t, C.RPAREN_TOKEN):
            state = State.CLOSE_PAREN
            at_end = True

        if at_end and is_column:
            on_to_next_column()
        return at_end

    def on_to_next_column():
        nonlocal cols, name, datatype, modifiers, state, has_auto_increment, grab_auto_increment_value, auto_increment_value

        modifier_str = ' '.join(modifiers).replace(" = ", "=").replace(" ,", ",")
        cols.append(IM.Column(name, datatype, modifier_str, has_auto_increment, auto_increment_value))
        name = ""
        datatype = ""
        modifiers = []
        state = State.IDENTIFIER
        has_auto_increment = False
        grab_auto_increment_value = False
        auto_increment_value = 0

    def do_modifiers(t: sql.Token, t_prev: sql.Token | None) -> None:
        nonlocal state, modifiers, has_auto_increment, grab_auto_increment_value, auto_increment_value

        # need to check for auto increment
        if grab_auto_increment_value and t.ttype == T.Number.Integer:
            grab_auto_increment_value = False
            auto_increment_value = int(t.value)

        if match_tokens(t, C.AUTO_INCREMENT_TOKEN):
            has_auto_increment = True
            grab_auto_increment_value = True

        # Special case:
        # AUTO_INCREMENT, AUTO_INCREMENT=1244
        # We get tripped up on the comma
        auto_inc_comma = t_prev is not None and \
            match_tokens(t_prev, C.AUTO_INCREMENT_TOKEN) \
            and match_tokens(t, C.COMMA_TOKEN)

        if auto_inc_comma or not check_for_end_of_column(t):
            state = State.MODIFIERS
            if isinstance(t, sql.IdentifierList):
                modifiers += [x.value for x in get_id_list_tokens(t)]
            else:
                modifiers.append(t.value)

    t_prev = None
    for t in tokens:
        if t.ttype == T.Whitespace:
            continue
        elif t.ttype == T.Newline:
            # argh, if AUTO_INCREMENT appears at the end of a list of
            # column modifiers, we assume the comma means there is
            # more to come, not that we are at the end of a column def.
            if state == State.MODIFIERS and match_tokens(t_prev, C.COMMA_TOKEN):
                on_to_next_column()
            else:
                continue
        elif state == State.OPEN_PAREN and match_tokens(t, C.LPAREN_TOKEN):
            state = State.IDENTIFIER
        elif state == State.IDENTIFIER and t.ttype == T.Name:
            name = t.value
            state = State.DATA_TYPE
        elif state == State.IDENTIFIER and match_tokens(t, C.PRIMARY_TOKEN):
            state = State.KEY
        elif state == State.IDENTIFIER and match_tokens(t, C.SEMICOLON_TOKEN):
            break
        elif state == State.DATA_TYPE:  # and t.ttype == T.Name:
            datatype = t.value
            state = State.POST_DATA_TYPE
        elif state == State.POST_DATA_TYPE:
            if match_tokens(t, C.LPAREN_TOKEN):
                datatype += "("
                state = State.DATA_SIZE
            else:
                do_modifiers(t, t_prev)
        elif state == State.DATA_SIZE:
            datatype += t.value
            if match_tokens(t, C.RPAREN_TOKEN):
                state = State.MODIFIERS
        elif state == State.MODIFIERS:
            do_modifiers(t, t_prev)
        elif state == State.KEY and match_tokens(t, C.KEY_TOKEN):
            state = State.PK_START
        elif state == State.PK_START and match_tokens(t, C.LPAREN_TOKEN):
            state = State.PK_COLS
        elif state == State.PK_COLS:
            if match_tokens(t, C.RPAREN_TOKEN):
                state = State.PK_END
            elif t.ttype == T.Name:
                pk_columns.append(t.value)
        elif state == State.PK_END:
            check_for_end_of_column(t, is_column=False)
        elif state == State.CLOSE_PAREN:
            break
        else:
            msg = f"Confusion, state: {State(state).name}, token: {repr(t)}"
            raise DbSyncParseException(msg)

        if state == State.CLOSE_PAREN:
            break
        t_prev = t

    if len(pk_columns) > 0:
        return (cols, IM.PrimaryKey(name, pk_columns))
    return (cols, None)


def _get_post_table_modifiers(ss: SqlStatement, table: IM.Table) -> None:
    class State(IntEnum):
        AUTO_INC = 0,
        EQUALS = 1,
        VALUE = 2,
        DONE = 3

    tl = ss.get_tokens_to_eol()
    modifiers = []
    state = State.AUTO_INC
    for t in tl:
        if match_tokens(t, C.SEMICOLON_TOKEN):
            break

        modifiers.append(t.value)

        if state == State.AUTO_INC and match_tokens(t, C.AUTO_INCREMENT_TOKEN):
            state = state.EQUALS
        elif state == State.EQUALS and match_tokens(t, C.EQUALS_TOKEN):
            state = state.VALUE
        elif state == State.VALUE and t.ttype == T.Number.Integer:
            table.update_autoinc_val(int(t.value))
            state = State.DONE

    table.post_definition_modifiers = " ".join(modifiers).replace(" = ", "=")


def create_table(ss: SqlStatement) -> IM.Table:
    t = ss.get_token()
    if isinstance(t, sql.Identifier):
        name = t.value
        if not Settings.obj().should_include_table(name):
            return None

        t = ss.get_token()
        if isinstance(t, sql.Parenthesis):
            cols, pks = get_columns(t)
            table = IM.Table(name, cols)
            if pks is not None:
                table.primary_keys = pks.primary_keys

            _get_post_table_modifiers(ss, table)
            return table
    raise DbSyncParseException("Invalid CREATE TABLE statement")
