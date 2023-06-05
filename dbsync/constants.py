
"""Constants used in dbsync parsing"""

from sqlparse import sql
from sqlparse import tokens as T

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
MODIFY_TOKEN = sql.Token(T.Keyword, "MODIFY")
AUTO_INCREMENT_TOKEN = sql.Token(T.Keyword, "AUTO_INCREMENT")
