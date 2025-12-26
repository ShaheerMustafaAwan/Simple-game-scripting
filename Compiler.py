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
# AST NODES (Abstract Syntax Tree)
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

# ------------------------------------
# OPTIMIZATION (PHASE 5)
# ------------------------------------
def optimize_tac(tac: List[TACInstr]) -> List[TACInstr]:
    """
    Performs:
    1. Redundant Turn Elimination (LEFT followed by RIGHT)
    2. Dead Code Elimination (MOVE 0 or JUMP 0)
    """
    if not tac:
        return tac
    
    optimized = []
    i = 0
    while i < len(tac):
        curr = tac[i]

        # --- 1. Dead Code Elimination (MOVE 0 / JUMP 0) ---
        # If we see an 'assign 0 -> tX', and the next instr is a call using that tX
        if curr.op == "assign" and curr.arg == "0":
            if i + 1 < len(tac):
                nxt = tac[i+1]
                if nxt.op == "call" and nxt.arg in ("move", "jump") and nxt.arg2 == curr.result:
                    print(f"[OPT] Removing dead code: {nxt.arg} 0")
                    i += 2 # Skip the assign AND the call
                    continue

        # --- 2. Redundant Turn Elimination ---
        if i + 1 < len(tac):
            nxt = tac[i+1]
            is_cancel = (
                (curr.arg == "turn_left" and nxt.arg == "turn_right") or
                (curr.arg == "turn_right" and nxt.arg == "turn_left")
            )
            if is_cancel:
                print(f"[OPT] Removing redundant: {curr.arg} & {nxt.arg}")
                i += 2
                continue
        
        optimized.append(curr)
        i += 1
    return optimized

# ------------------------------------
# CODE GENERATION / EXECUTION
# ------------------------------------
def exec_TAC(tac: List[TACInstr]):
    env = {}

    for instr in tac:
        if instr.op == "assign":
            env[instr.result] = int(instr.arg)

        elif instr.op == "call":
            func = instr.arg
            x = env.get(instr.arg2) if instr.arg2 else None

            if func == "move":
                print(f"[SIM] MOVE {x}")
            elif func == "jump":
                print(f"[SIM] JUMP {x}")
            elif func == "turn_left":
                print("[SIM] TURN LEFT")
            elif func == "turn_right":
                print("[SIM] TURN RIGHT")
            elif func == "attack":
                print("[SIM] ATTACK")
            else:
                raise RuntimeError(f"Unknown call {func}")

# ------------------------------------
# DRIVER
# ------------------------------------
def run_demo():
    print("=== BASIC Movement DSL Demo ===\n")
    print("Source:")
    print(SAMPLE.strip())
    print("\n=== AST ===")
    program, tac = compile_and_run(SAMPLE, show_ast=True, show_tac=False)

def print_ast(program: Program):
    print("\n=== AST ===")
    for s in program.statements:
        print(f"  Stmt(kind={s.kind}, subkind={s.subkind}, arg={s.arg})")

def compile_and_run(text: str, show_ast=False, show_tac=False):

    text = text.lstrip() 

    # --- LEXING ---
    tokens = lex(text)

    # NEW: Print tokens
    print("=== TOKENS ===")
    for t in tokens:
        print(f"  Token(type={t.type}, value={t.value}, pos={t.pos})")

    # --- PARSING ---
    parser = Parser(tokens)
    program = parser.parse()

    
    print("\n=== PARSE TREE ===")
    for stmt in program.statements:
        print("Stmt")
        print(f" ├── kind: {stmt.kind}")
        if stmt.arg is not None:
            print(f" ├── arg: {stmt.arg}")
        if stmt.subkind is not None:
            print(f" ├── subkind: {stmt.subkind}")
        print(f" └── pos: {stmt.pos}")

    
    if show_ast:
        print_ast(program)

    # --- SEMANTIC ANALYSIS ---
    semantic_check(program)

    # --- TAC GENERATION ---
    tac = generate_tac(program)

    # --- OPTIMIZATION (NEW PHASE) ---
    print("\n=== OPTIMIZATION ===")
    optimized_tac = optimize_tac(tac)

    print("\n=== FINAL OPTIMIZED TAC ===")
    for i, t in enumerate(optimized_tac):
        print(f"{i:03}: {t}")

    # --- EXECUTION ---
    print("\n=== EXECUTION ===")
    exec_TAC(optimized_tac) # Run the optimized version!

    print("\n=== End Demo ===")

    return program, tac

SAMPLE = """
TURN LEFT; TURN RIGHT; MOVE 0; Attack;
"""

if __name__ == "__main__":

    parser_cli = argparse.ArgumentParser(description="Game Movement DSL Compiler (No Regex)")
    parser_cli.add_argument("file", nargs="?", help="Path to input .gm source file")
    parser_cli.add_argument("--show-ast", action="store_true", help="Show AST")
    parser_cli.add_argument("--show-tac", action="store_true", help="Show TAC")
    parser_cli.add_argument("--demo", action="store_true", help="Run built-in demo program")

    args = parser_cli.parse_args()

    # --- If user runs demo ---
    if args.demo or (args.file is None):
        print("=== Running Demo Mode ===\n")
        compile_and_run(SAMPLE, show_ast=True, show_tac=True)
        sys.exit(0)

    # --- If file is provided ---
    try:
        with open(args.file, "r") as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"ERROR: File '{args.file}' not found.")
        sys.exit(1)

    print(f"=== Compiling file: {args.file} ===\n")

    try:
        compile_and_run(source_code, show_ast=args.show_ast, show_tac=args.show_tac)
    except SyntaxError as e:
        print("Syntax Error:", e)
    except SemanticError as e:
        print("Semantic Error:", e)
    except Exception as e:
        print("Runtime Error:", e)
