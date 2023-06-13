
"""Constants used in dbsync parsing"""

from sqlparse import sql
from sqlparse import tokens as T

# Convention: if the token value is "*any*", match_tokens will only
# compare the token types.
ANY = "*any*"
SPACE_TOKEN = sql.Token(T.Whitespace, ANY)
NEWLINE_TOKEN = sql.Token(T.Newline, ANY)
NAME_TOKEN = sql.Token(T.Name, ANY)
NUMBER_TOKEN = sql.Token(T.Number, ANY)
INTEGER_TOKEN = sql.Token(T.Number.Integer, ANY)

LPAREN_TOKEN = sql.Token(T.Punctuation, "(")
RPAREN_TOKEN = sql.Token(T.Punctuation, ")")
COMMA_TOKEN = sql.Token(T.Punctuation, ",")
SEMICOLON_TOKEN = sql.Token(T.Punctuation, ";")
EQUALS_TOKEN = sql.Token(T.Comparison, "=")

VALUES_TOKEN = sql.Token(T.Keyword, "VALUES")
TABLE_TOKEN = sql.Token(T.Keyword, "TABLE")
ADD_TOKEN = sql.Token(T.Keyword, "ADD")
PRIMARY_TOKEN = sql.Token(T.Keyword, "PRIMARY")
KEY_TOKEN = sql.Token(T.Keyword, "KEY")
UNIQUE_TOKEN = sql.Token(T.Keyword, "UNIQUE")
MODIFY_TOKEN = sql.Token(T.Keyword, "MODIFY")
AUTO_INCREMENT_TOKEN = sql.Token(T.Keyword, "AUTO_INCREMENT")
INTO_TOKEN = sql.Token(T.Keyword, "INTO")
