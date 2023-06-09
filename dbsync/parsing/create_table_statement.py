"""Parses create table statements"""

from dataclasses import dataclass
from sqlparse import sql
from sqlparse import tokens as T
from enum import IntEnum
from typing import Callable, List, Tuple, Dict

from dbsync.exceptions import DbSyncParseException
from dbsync import constants as C
from dbsync import intermediate as IM
from dbsync.parsing.sql_statement import SqlStatement
from dbsync.parsing.utilities \
    import match_tokens, get_flattened_tokens, get_id_list_tokens
from dbsync.settings import Settings


class ColumnState(IntEnum):
    OPEN_PAREN = 0
    IDENTIFIER = 1      # may also get PRIMARY, UNIQUE, or KEY here
    DATA_TYPE = 2
    POST_DATA_TYPE = 3
    DATA_SIZE = 4
    MODIFIERS = 5
    KEY = 6
    KEY_NAME = 7
    KEY_COLS_START = 8
    KEY_COL_NAME = 9
    KEY_COL_LENGTH = 10
    KEY_COL_LENGTH_END = 11
    KEY_COLS_END = 12
    CLOSE_PAREN = 13


@dataclass
class ActionParams:
    """Parameters passed to an action_method"""
    state: ColumnState
    t_prev: sql.Token
    t_curr: sql.Token


@dataclass
class Action:
    """Defines one action that may be performed based on current state"""
    current_state: ColumnState | None
    expected_token: sql.Token | None
    action_method: Callable[[ActionParams], ColumnState | None]
    next_state: ColumnState | None

    def __repr__(self) -> str:
        s = "("
        s += "None" if self.current_state is None else ColumnState(self.current_state).name
        s += ", "
        s += "None" if self.expected_token is None else f"'{self.expected_token.value}'"
        s += ", "
        s += "None" if self.action_method is None else self.action_method
        s += ", "
        s += "None" if self.next_state is None else self.next_state.name
        s += ")"
        return s


class ParserActions:
    """The data we need to keep track of while parsing column defs and methods to alter it"""
    def __init__(self):
        self.cols: List[IM.Column] = []
        self.keys: List[IM.Key] = []
        self._reset_for_next_column(ColumnState.OPEN_PAREN)

    def _reset_for_next_column(self, state: ColumnState = ColumnState.IDENTIFIER) -> None:
        self.state = state      # TODO should this be here or in StateMachine?
        self.name = ""
        self.datatype = ""
        self.modifiers = []
        self.has_auto_increment = False
        self.grab_auto_increment_value = False
        self.auto_increment_value = 0
        self.is_primary = False
        self.is_unique = False
        self.current_key: IM.Key | None = None
        self.current_key_column: IM.KeyColumn | None = None
        self.save_prev = True

    def reset_for_next_token(self):
        self.save_prev = True

    def _continue_action(self, params: ActionParams) -> ColumnState | None:     # NOSONAR S1172
        self.save_prev = False

    def _newline_special_case(self, params: ActionParams) -> ColumnState | None:
        #
        # argh, if AUTO_INCREMENT appears at the end of a list of
        # column modifiers, we assume the comma means there is
        # more to come, not that we are at the end of a column def.
        if self.state == ColumnState.MODIFIERS and match_tokens(params.t_prev, C.COMMA_TOKEN):
            # TODO in this case, there will be a trailing comma in the modifier list
            self._on_to_next_column()
        self.save_prev = False

    def _save_name(self, params: ActionParams) -> ColumnState | None:
        self.name = params.t_curr.value

    def _set_primary(self, params: ActionParams) -> ColumnState | None:     # NOSONAR S1172
        self.is_primary = True

    def _set_unique(self, params: ActionParams) -> ColumnState | None:      # NOSONAR S1172
        self.is_unique = True

    def _accumulate_datatype(self, params: ActionParams) -> ColumnState | None:
        self.datatype += params.t_curr.value
        return ColumnState.MODIFIERS if match_tokens(params.t_curr, C.RPAREN_TOKEN) else None

    def _accumulate_modifiers(self, params: ActionParams) -> ColumnState | None:
        # need to check for auto increment
        if self.grab_auto_increment_value and params.t_curr.ttype == T.Number.Integer:
            self.grab_auto_increment_value = False
            self.auto_increment_value = int(params.t_curr.value)

        if match_tokens(params.t_curr, C.AUTO_INCREMENT_TOKEN):
            self.has_auto_increment = True
            self.grab_auto_increment_value = True

        # Special case:
        # AUTO_INCREMENT, AUTO_INCREMENT=1244
        # We get tripped up on the comma
        auto_inc_comma = params.t_prev is not None and \
            match_tokens(params.t_prev, C.AUTO_INCREMENT_TOKEN) \
            and match_tokens(params.t_curr, C.COMMA_TOKEN)

        if auto_inc_comma or not self._check_for_end_of_column(params.t_curr):
            if isinstance(params.t_curr, sql.IdentifierList):
                self.modifiers += [x.value for x in get_id_list_tokens(params.t_curr)]
            else:
                self.modifiers.append(params.t_curr.value)
            return ColumnState.MODIFIERS
        return None

    def _check_keytype(self, params: ActionParams) -> ColumnState | None:       # NOSONAR S1172
        ### print(f"Check key type, primary: {self.is_primary}, unique: {self.is_unique}")

        if self.is_primary:
            self.current_key = IM.Key("", [], self.is_primary, self.is_unique)
            return ColumnState.KEY_COLS_START
        return ColumnState.KEY_NAME

    def _save_key_name(self, params: ActionParams) -> ColumnState | None:
        self.current_key = IM.Key(params.t_curr.value, [], self.is_primary, self.is_unique)
        ### print(f"Key name: {self.current_key.name}")

    def _save_key_col_name(self, params: ActionParams) -> ColumnState | None:
        self.current_key_column = IM.KeyColumn(params.t_curr.value)

    def _save_key_col_length(self, params: ActionParams) -> ColumnState | None:
        self.current_key_column.length = int(params.t_curr.value)

    def _save_key_col(self, params: ActionParams) -> ColumnState | None:        # NOSONAR S1172
        if self.current_key_column is not None:
            self.current_key.add_column(self.current_key_column)
            self.current_key_column = None

    def _save_key(self, params: ActionParams) -> ColumnState | None:
        if self.current_key is not None:
            self._save_key_col(params)
            self.keys.append(self.current_key)
            self.current_key = None

    def _check_for_end_of_column(self, t: T.Token, is_column: bool = True) -> bool:
        at_end = False
        # lol, comma ends a column def except when it doesn't
        # in particular, we have AUTO_INCREMENT, AUTO_INCREMENT=1244
        # on modify statements
        if match_tokens(t, C.COMMA_TOKEN):
            self.state = ColumnState.IDENTIFIER
            at_end = True
        elif match_tokens(t, C.RPAREN_TOKEN):
            self.state = ColumnState.CLOSE_PAREN
            at_end = True

        ### print(f"_check_for_end_of_column, token: {t.value}, at_end: {at_end}, is_column: {is_column}")
        if at_end and is_column:
            self._on_to_next_column()
        return at_end

    def _on_to_next_column(self):
        modifier_str = ' '.join(self.modifiers).replace(" = ", "=").replace(" ,", ",")
        self.cols.append(
            IM.Column(self.name, self.datatype, modifier_str,
                      self.has_auto_increment, self.auto_increment_value))
        self._reset_for_next_column()

    def get_result(self):
        return (self.cols, self.keys)


_state_action_list: List[Action] = [
    # if we wanted to validate the SQL, we'd need a lot more states.
    # TODO more states and fewer state variables would be a good thing.
    Action(None, C.SPACE_TOKEN, "_continue_action", None),
    Action(None, C.NEWLINE_TOKEN, "_newline_special_case", None),
    Action(ColumnState.OPEN_PAREN, C.LPAREN_TOKEN, None, ColumnState.IDENTIFIER),
    Action(ColumnState.IDENTIFIER, C.NAME_TOKEN, "_save_name", ColumnState.DATA_TYPE),
    Action(ColumnState.IDENTIFIER, C.PRIMARY_TOKEN, "_set_primary", ColumnState.KEY),
    Action(ColumnState.IDENTIFIER, C.UNIQUE_TOKEN, "_set_unique", ColumnState.KEY),
    Action(ColumnState.IDENTIFIER, C.KEY_TOKEN, "_check_keytype", ColumnState.KEY_COLS_START),
    # presumably, we're parsing an ALTER TABLE statement:
    Action(ColumnState.IDENTIFIER, C.ADD_TOKEN, None, None),
    # TODO does this happen?
    Action(ColumnState.IDENTIFIER, C.SEMICOLON_TOKEN, None, ColumnState.CLOSE_PAREN),
    Action(ColumnState.DATA_TYPE, None, "_accumulate_datatype", ColumnState.POST_DATA_TYPE),
    Action(ColumnState.POST_DATA_TYPE, C.LPAREN_TOKEN, "_accumulate_datatype", ColumnState.DATA_SIZE),
    Action(ColumnState.POST_DATA_TYPE, None, "_accumulate_modifiers", ColumnState.MODIFIERS),
    Action(ColumnState.DATA_SIZE, None, "_accumulate_datatype", None),
    Action(ColumnState.MODIFIERS, None, "_accumulate_modifiers", None),
    Action(ColumnState.KEY, C.KEY_TOKEN, "_check_keytype", None),
    Action(ColumnState.KEY_NAME, C.NAME_TOKEN, "_save_key_name", ColumnState.KEY_COLS_START),
    Action(ColumnState.KEY_COLS_START, C.LPAREN_TOKEN, None, ColumnState.KEY_COL_NAME),
    Action(ColumnState.KEY_COL_NAME, C.NAME_TOKEN, "_save_key_col_name", None),
    Action(ColumnState.KEY_COL_NAME, C.LPAREN_TOKEN, None, ColumnState.KEY_COL_LENGTH),
    Action(ColumnState.KEY_COL_NAME, C.COMMA_TOKEN, "_save_key_col", None),
    Action(ColumnState.KEY_COL_NAME, C.RPAREN_TOKEN, "_save_key", ColumnState.KEY_COLS_END),
    Action(ColumnState.KEY_COL_LENGTH, C.INTEGER_TOKEN, "_save_key_col_length", None),
    Action(ColumnState.KEY_COL_LENGTH, C.RPAREN_TOKEN, "_save_key_col", ColumnState.KEY_COL_LENGTH_END),
    Action(ColumnState.KEY_COL_LENGTH_END, C.COMMA_TOKEN, None, ColumnState.KEY_COL_NAME),
    Action(ColumnState.KEY_COL_LENGTH_END, C.RPAREN_TOKEN, "_save_key", ColumnState.KEY_COLS_END),
    Action(ColumnState.KEY_COLS_END, C.COMMA_TOKEN, "_reset_for_next_column", ColumnState.IDENTIFIER),
    Action(ColumnState.KEY_COLS_END, C.RPAREN_TOKEN, None, ColumnState.CLOSE_PAREN),
    Action(ColumnState.CLOSE_PAREN, None, None, None),
]


class StateMachine:
    """State machine for parsing column (and key) definitions"""
    def __init__(self, state_action_list: List[Action]):
        self.parser_actions = ParserActions()

        self.state_action_list = state_action_list
        self.no_state_actions = [a for a in self.state_action_list if a.current_state is None]

        state_names: List[str] = [st.name for st in list(ColumnState)]
        self.state_dict: Dict[str, Action] = dict.fromkeys(state_names)
        for a in self.state_action_list:
            if a.current_state is not None:
                key = ColumnState(a.current_state).name
                if self.state_dict[key] is None:
                    self.state_dict[key] = [a]
                else:
                    self.state_dict[key].append(a)

    def parse_tokens(self, tl: sql.TokenList) -> None:
        tokens = get_flattened_tokens(tl)
        t_iter = tokens.__iter__()
        t_prev = None
        while True:
            processed = False
            self.parser_actions.reset_for_next_token()
            try:
                t_curr = next(t_iter)
            except StopIteration:
                break

            ### print(f"State: {ColumnState(self.parser_actions.state).name}, token: {repr(t_curr)}")
            params = ActionParams(self.parser_actions.state, t_prev, t_curr)
            processed, next_state = self._apply_no_state_actions(params)
            if not processed:
                processed, next_state = self._apply_state_actions(params)
            if not processed:
                msg = f"Confusion, state: {ColumnState(self.parser_actions.state).name}, token: {repr(t_curr)}"
                raise DbSyncParseException(msg)

            if next_state is not None:
                self.parser_actions.state = next_state
            if self.parser_actions.save_prev:
                t_prev = t_curr

        return self.parser_actions.get_result()

    def _apply_no_state_actions(self, params: ActionParams) -> Tuple[bool, ColumnState]:
        for action in self.no_state_actions:
            if match_tokens(params.t_curr, action.expected_token):
                next_state = self._call_action_method(action, params)
                return (True, next_state)
        return (False, None)

    def _apply_state_actions(self, params: ActionParams) -> Tuple[bool, ColumnState]:
        if params.state is not None:
            action_list = self.state_dict[params.state.name]
            for action in action_list:
                if action.expected_token is None or \
                        match_tokens(params.t_curr, action.expected_token):
                    next_state = self._call_action_method(action, params)
                    return (True, next_state)
        return (False, None)

    def _call_action_method(self, action: Action, params: ActionParams) -> ColumnState | None:
        if action.action_method is not None:
            func = getattr(self.parser_actions, action.action_method)
            next_state = func(params)
            return next_state if next_state is not None else action.next_state
        return action.next_state


class ColumnList:
    def __init__(self) -> None:
        self.state_machine = StateMachine(_state_action_list)

    def get_columns(self, tl: sql.TokenList) -> Tuple[List[IM.Column], List[IM.Key]]:
        """ Gets the column definitions for a CREATE TABLE statement """
        result = self.state_machine.parse_tokens(tl)
        return result


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
            cl = ColumnList()
            cols, pks = cl.get_columns(t)
            table = IM.Table(name, cols, keys=pks)
            _get_post_table_modifiers(ss, table)
            return table
    raise DbSyncParseException("Invalid CREATE TABLE statement")
