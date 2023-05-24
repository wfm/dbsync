import sqlparse
from sqlparse import sql

from dbsync.exceptions import DbSyncParseException


class SqlStatement:
    """Makes working with sqlparse a little easier"""
    _dump_tokens = False

    @classmethod
    def set_dump_tokens(cls, state: bool) -> None:
        """
        Turns dump of token values to stdout on and off
        :param state: If True, tokens will be printed
        """
        SqlStatement._dump_tokens = state

    @classmethod
    def get_dump_tokens(cls):
        """Returns True if token values should be printed to stdout"""
        return SqlStatement._dump_tokens

    def __init__(self, text: str, tl: sql.TokenList = None):
        """
        Creates an instance of the SqlStatement class
        :param text: the text of a SQL statement
        :param tl: a list of tokens, which overrides the text (if any)
        """
        if tl is not None:
            self.tl = tl
        elif text is not None:
            self.text = text
            self.parsed = sqlparse.parse(text)[0]
            self.tokens = self.parsed.tokens
            self.tl = sql.TokenList(self.tokens)
        else:
            raise ValueError("Must specify text or token list")

        self.token_ix = -1

    def get_token(self) -> sql.Token | None:
        """Returns the next token in the stream and advances the stream"""
        if self.token_ix is None:
            return None
        elif self.token_ix < 0:
            t = self.tl.token_first(skip_cm=True)
            if (t is None):
                ix = None
            else:
                ix = self.tl.token_index(t)
        else:
            ix, t = self.tl.token_next(self.token_ix, skip_cm=True)
        self.token_ix = ix

        if SqlStatement._dump_tokens:
            print("Token:", repr(t))
        return t

    def peek_token(self) -> sql.Token | None:
        """Returns the next token in the stream without advancing"""
        save_ix = self.token_ix
        t = self.get_token()
        self.token_ix = save_ix
        return t

    def eat_token(self, expected: sql.Token) -> None:
        """
        Gets the next token in the stream and verifies that it
        matches the expected token
        :param expected: the expected token
        :raises DbSyncParseException
        """
        actual = self.get_token()
        if actual is None:
            raise(EOFError("No more tokens"))
        elif not actual.match(expected.ttype, expected.value):
            msg = f"Unexpected token, \
                expected: {repr(expected)}, got: {repr(actual)}"
            raise DbSyncParseException(msg)

    def get_tokens_to_eol(self) -> sql.TokenList | None:
        """
        As the name says, it gets the rest of the tokens
        for the current SQL statement
        """
        tokens = []
        while True:
            t = self.get_token()
            if t is None:
                break
            tokens.append(t)

        return sql.TokenList(tokens)
