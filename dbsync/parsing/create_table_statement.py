"""Parses create table statements"""

from sqlparse import sql
from sqlparse import tokens as T
from enum import IntEnum
from typing import List

from dbsync.exceptions import DbSyncParseException
from dbsync import constants as C
from dbsync import intermediate as IM
from dbsync.parsing.sql_statement import SqlStatement
from dbsync.parsing.utilities \
    import match_tokens, get_flattened_tokens, get_id_list_tokens
from dbsync.settings import Settings


def get_columns(tl: sql.TokenList) -> List[IM.Column]:
    """ Gets column definitions for a CREATE TABLE statement """
    class State(IntEnum):
        OPEN_PAREN = 0
        IDENTIFIER = 1
        DATA_TYPE = 2
        POST_DATA_TYPE = 3
        DATA_SIZE = 4
        MODIFIERS = 5
        CLOSE_PAREN = 6

    state = State.OPEN_PAREN
    cols = []
    tokens = get_flattened_tokens(tl)
    name = ""
    datatype = ""
    modifiers = []

    def check_for_end_of_column(t: T.Token) -> bool:
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

        if at_end:
            on_to_next_column()
        return at_end

    def on_to_next_column():
        nonlocal cols, name, datatype, modifiers, state

        cols.append(IM.Column(name, datatype, ' '.join(modifiers)))
        name = ""
        datatype = ""
        modifiers = []
        state = State.IDENTIFIER

    def do_modifiers(t: sql.Token, t_prev: sql.Token | None) -> None:
        nonlocal state, modifiers

        # Special case:
        # AUTO_INCREMENT, AUTO_INCREMENT=1244
        # We get tripped up on the comma
        auto_inc_comma = t_prev is not None and \
            match_tokens(t_prev, C.AUTO_INCREMENT_TOKEN)

        if auto_inc_comma or not check_for_end_of_column(t):
            state = State.MODIFIERS
            if isinstance(t, sql.IdentifierList):
                modifiers += [x.value for x in get_id_list_tokens(t)]
            else:
                modifiers.append(t.value)

    t_prev = None
    for t in tokens:
        if (t.ttype in [T.Whitespace, T.Newline]):
            continue
        elif state == State.OPEN_PAREN and match_tokens(t, C.LPAREN_TOKEN):
            state = State.IDENTIFIER
        elif state == State.IDENTIFIER and t.ttype == T.Name:
            name = t.value
            state = State.DATA_TYPE
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
        elif state == State.CLOSE_PAREN:
            break
        else:
            msg = f"Confusion, state: {state}, token: {repr(t)}"
            raise DbSyncParseException(msg)

        if state == State.CLOSE_PAREN:
            break
        t_prev = t

    return cols


def create_table(ss: SqlStatement) -> IM.Table:
    t = ss.get_token()
    if isinstance(t, sql.Identifier):
        name = t.value
        if not Settings.obj().should_include_table(name):
            return None

        t = ss.get_token()
        if isinstance(t, sql.Parenthesis):
            cols = get_columns(t)
            return IM.Table(name, cols)
        # TODO what about the stuff after the column defs?
        # e.g., ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        # COLLATE=utf8mb4_unicode_520_ci;
    raise DbSyncParseException("Invalid CREATE TABLE statement")
