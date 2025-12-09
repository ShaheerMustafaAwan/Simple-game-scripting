import sys
from dataclasses import dataclass
from typing import List, Optional
import argparse

# ------------------------------------
# TOKEN DEFINITION
# ------------------------------------
@dataclass
class Token:
    type: str
    value: str
    pos: int

# ------------------------------------
# LEXER 
# ------------------------------------
KEYWORDS = {
    "move": "MOVE",
    "turn": "TURN",
    "left": "LEFT",
    "right": "RIGHT",
    "jump": "JUMP",
    "attack": "ATTACK",
}

def is_letter(c):
    return c.isalpha()

def is_digit(c):
    return c.isdigit()

def lex(text: str) -> List[Token]:
    tokens = []
    i = 0
    n = len(text)

    while i < n:
        c = text[i]

        # Skip spaces and newlines
        if c in " \t\r\n":
            i += 1
            continue

        # Semicolon
        if c == ";":
            tokens.append(Token("SEMICOLON", ";", i))
            i += 1
            continue

        # NUMBER token
        if is_digit(c):
            start = i
            while i < n and is_digit(text[i]):
                i += 1
            number_value = text[start:i]
            tokens.append(Token("NUMBER", number_value, start))
            continue

        # IDENTIFIER / KEYWORD
        if is_letter(c):
            start = i
            while i < n and (text[i].isalpha()):
                i += 1
            word = text[start:i].lower()

            if word in KEYWORDS:
                tokens.append(Token(KEYWORDS[word], word, start))
            else:
                raise SyntaxError(f"Unknown identifier '{word}' at pos {start}")
            continue

        # Any other character = invalid
        raise SyntaxError(f"Unexpected character '{c}' at pos {i}")

    tokens.append(Token("EOF", "", i))
    return tokens
