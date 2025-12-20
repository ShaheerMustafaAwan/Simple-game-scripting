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

# ------------------------------------
# AST NODES
# ------------------------------------
@dataclass
class ASTNode:
    pass

@dataclass
class Program(ASTNode):
    statements: List['Stmt']

@dataclass
class Stmt(ASTNode):
    kind: str            # MOVE, TURN, JUMP, ATTACK
    arg: Optional[int]   # number for MOVE,JUMP
    subkind: Optional[str]  # LEFT/RIGHT for TURN
    pos: int

# ------------------------------------
# PARSER 
# ------------------------------------
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.i = 0

    def peek(self):
        return self.tokens[self.i]

    def consume(self, expected_type=None):
        tok = self.peek()
        if expected_type and tok.type != expected_type:
            raise SyntaxError(
                f"Expected {expected_type} at pos {tok.pos}, got {tok.type}"
            )
        self.i += 1
        return tok

    def parse(self) -> Program:
        stmts = []
        while self.peek().type != "EOF":
            stmts.append(self.parse_stmt())
        return Program(stmts)

    def parse_stmt(self) -> Stmt:
        tok = self.peek()

        if tok.type == "MOVE":
            self.consume("MOVE")
            num = self.consume("NUMBER")
            self.consume("SEMICOLON")
            return Stmt("MOVE", int(num.value), None, tok.pos)

        elif tok.type == "TURN":
            self.consume("TURN")
            d = self.peek()
            if d.type not in ("LEFT", "RIGHT"):
                raise SyntaxError(f"Expected LEFT or RIGHT at pos {d.pos}")
            direction = self.consume().type
            self.consume("SEMICOLON")
            return Stmt("TURN", None, direction, tok.pos)

        elif tok.type == "JUMP":
            self.consume("JUMP")
            num = self.consume("NUMBER")
            self.consume("SEMICOLON")
            return Stmt("JUMP", int(num.value), None, tok.pos)

        elif tok.type == "ATTACK":
            self.consume("ATTACK")
            self.consume("SEMICOLON")
            return Stmt("ATTACK", None, None, tok.pos)

        else:
            raise SyntaxError(f"Unexpected token {tok.type} at pos {tok.pos}")

# ------------------------------------
# SEMANTIC ANALYSIS
# ------------------------------------
class SemanticError(Exception):
    pass

def semantic_check(program: Program):
    for s in program.statements:
        if s.kind in ("MOVE", "JUMP"):
            if s.arg < 0:
                raise SemanticError(
                    f"Argument must be >=0 at pos {s.pos} (got {s.arg})"
                )
        if s.kind == "TURN" and s.subkind not in ("LEFT", "RIGHT"):
            raise SemanticError(f"Invalid direction at pos {s.pos}")

# ------------------------------------
# THREE-ADDRESS CODE (TAC)
# ------------------------------------
@dataclass
class TACInstr:
    op: str
    arg: Optional[str] = None
    arg2: Optional[str] = None
    result: Optional[str] = None

    def __str__(self):
        parts = [self.op]
        if self.arg is not None: parts.append(str(self.arg))
        if self.arg2 is not None: parts.append(str(self.arg2))
        if self.result is not None: parts.append("-> " + str(self.result))
        return " ".join(parts)

def generate_tac(program: Program):
    tac = []
    tcount = 0

    def temp():
        nonlocal tcount
        tcount += 1
        return f"t{tcount}"

    for s in program.statements:

        if s.kind == "MOVE":
            t = temp()
            tac.append(TACInstr("assign", str(s.arg), result=t))
            tac.append(TACInstr("call", "move", arg2=t))

        elif s.kind == "JUMP":
            t = temp()
            tac.append(TACInstr("assign", str(s.arg), result=t))
            tac.append(TACInstr("call", "jump", arg2=t))

        elif s.kind == "TURN":
            tac.append(TACInstr("call", f"turn_{s.subkind.lower()}"))

        elif s.kind == "ATTACK":
            tac.append(TACInstr("call", "attack"))

    return tac
