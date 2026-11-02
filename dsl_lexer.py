import re # for regex 
import sys  # to read command-line arguments
from collections import namedtuple  # to define a simple Token class


# Token definition
Token = namedtuple("Token", ["type", "value", "line", "column"])



# an ordered list of (TOKEN_NAME, REGEX) pairs.
# ORDER MATTERS because earlier rules have priority.
# The lexer tries patterns from top to bottom, and the first matching rule wins.
TOKEN_SPECIFICATION = [
    # Comments
    ("COMMENT", r"//.*|/\*[\s\S]*?\*/"),

    # Keywords
    ("AGENT", r"\bagent\b"),
    ("TOOL", r"\btool\b"),
    ("TASK", r"\btask\b"),
    ("ACTION", r"\baction\b"),
    ("SYSTEM", r"\bsystem\b"),
    ("RUN", r"\brun\b"),
    ("IF", r"\bif\b"),
    ("FOR", r"\bfor\b"),
    ("IN", r"\bin\b"),
    ("LIST", r"\blist\b"),
    ("INT", r"\bint\b"),
    ("STRING", r"\bstring\b"),
    ("BOOL", r"\bbool\b"),
    ("BOOL_LITERAL", r"\b(true|false)\b"), # since we defined Bool_literal before ID, true and false will be matched as BOOL_LITERAL in the grammar, thus to match it we define it being either true or false

    # note: we define all kewords before identifiers, so that they get matched as keywords and not as generic IDs.

    # Literals
    ("STRING_LITERAL", r'"([^"\\]|\\.)*"'),
    ("NUM", r"(0|[1-9][0-9]*)\b"),

    # Identifiers
    ("ID", r"[a-zA-Z_][a-zA-Z0-9_]*"), # rejects 008 for example

    # Multi-character grammar terminals
    ("ARROW", r"->"),
    ("EQ", r"=="),
    ("NE", r"!="),
    ("LE", r"<="),
    ("GE", r">="),

    # we match multi-char operators before singe-cahr operators so that they dont get matcehd as single ones.
    # for example, == would be matched as two separate = tokens.

    # Single-character grammar terminals
    ("ASSIGN", r"="),
    ("PLUS", r"\+"),
    ("MINUS", r"-"),
    ("MULT", r"\*"),
    ("DIV", r"/"),
    ("LT", r"<"),
    ("GT", r">"),
    ("COLON", r":"),
    ("DOT", r"\."),
    ("COMMA", r","),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("LBRACE", r"\{"),
    ("RBRACE", r"\}"),
    ("LBRACKET", r"\["),
    ("RBRACKET", r"\]"),

    # Whitespace
    ("WHITESPACE", r"[ \t\r\n]+"),

    # Any other character
    ("MISMATCH", r"."),
]



# joins all the patterns into one giant regex and complies once.
master_pattern = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECIFICATION)
)

# Internal regex group names must be valid Python identifiers since we are using python re.
# This map converts them into the exact token names used by the grammar, thus we match internaly , then convert externaly to comply with the grammar.
TOKEN_NAME_MAP = {
    "AGENT": "agent",
    "TOOL": "tool",
    "TASK": "task",
    "ACTION": "action",
    "SYSTEM": "system",
    "RUN": "run",
    "IF": "if",
    "FOR": "for",
    "IN": "in",
    "LIST": "list",
    "INT": "int",
    "STRING": "string",
    "BOOL": "bool",
    "BOOL_LITERAL": "Bool_literal",
    "STRING_LITERAL": "String_literal",
    "ARROW": "->",
    "EQ": "==",
    "NE": "!=",
    "LE": "<=",
    "GE": ">=",
    "LT": "<",
    "GT": ">",
    "ASSIGN": "=",
    "PLUS": "+",
    "MINUS": "-",
    "MULT": "*",
    "DIV": "/",
    "COLON": ":",
    "DOT": ".",
    "COMMA": ",",
    "LPAREN": "(",
    "RPAREN": ")",
    "LBRACE": "{",
    "RBRACE": "}",
    "LBRACKET": "[",
    "RBRACKET": "]",
}

# takes input code as a string and produces a list of tokens.
def tokenize(code):
    if code.startswith("\ufeff"):
        code = code[1:]

    tokens = []
    line_num = 1
    line_start = 0

    # finditer():
    # starts at position 0
    # applies the regex
    # finds a match
    # advances the input pointer
    # repeats until EOF
    for match in master_pattern.finditer(code):
        kind = match.lastgroup # this is the name of the matched regex group
        token_type = TOKEN_NAME_MAP.get(kind, kind) # convert internal group name to grammar token name, if not found, use the internal name
        value = match.group() # the actual text that was matched
        column = match.start() - line_start + 1
        #match.start() is where is it in the whole file
        #line_start is where does this line begin
        # so when we substract them, we get how far into the line we are, and then we add 1 because column numbers start at 1, not 0.

        if token_type == "WHITESPACE":
            if "\n" in value:
                line_num += value.count("\n")
                last_newline = value.rfind("\n")
                line_start = match.start() + last_newline + 1   
                # this is to account for whitespace that contains newlines.
            continue

        if token_type == "COMMENT":
            if "\n" in value:
                line_num += value.count("\n")
                last_newline = value.rfind("\n")
                line_start = match.start() + last_newline + 1
                #same logic as above
            continue

        if token_type == "MISMATCH":
            raise SyntaxError(
                f"Unexpected character {value!r} at line {line_num}, column {column}"
            )

        tokens.append(Token(token_type, value, line_num, column))

    return tokens



def main():
    if len(sys.argv) != 2:
        print("Usage: python dsl_lexer.py <source_file>")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename, "r", encoding="utf-8") as file:
            code = file.read()
    except FileNotFoundError:
        print(f"Error: file '{filename}' not found.")
        sys.exit(1)

    try:
        tokens = tokenize(code)
    except SyntaxError as error:
        print("Lexical error:", error)
        sys.exit(1)

    for token in tokens:
        print(
            f"{token.type:<15} {token.value:<15} " #just for formatting output in a nice table
            f"(line {token.line}, col {token.column})"
        )


if __name__ == "__main__":
    main()
