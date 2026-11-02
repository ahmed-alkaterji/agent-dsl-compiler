import sys
from collections import namedtuple #for EOF token

from dsl_lexer import tokenize


# EOF token
Token = namedtuple("Token", ["type", "value", "line", "column"]) #mainly to create EOF token


# LL(1) Parsing Table
PARSING_TABLE = {
    "Program": {
        "agent": ["Agent_Program", "System_Program"],
        "system": ["Agent_Program", "System_Program"],
    },

    "Agent_Program": {
        "agent": ["Agent", "Agent_Program"],
        "system": [],  
    },

    "Agent": {
        "agent": ["agent", "ID", "{", "Agent_List", "}"],
    },

    "Agent_List": {
        "tool": ["Stmt", "Agent_List"],
        "task": ["Stmt", "Agent_List"],
        "}": [],  
    },

    "Stmt": {
        "tool": ["tool_dec"],
        "task": ["task_def"],
    },

    "tool_dec": {
        "tool": ["tool", "ID"],
    },

    "task_def": {
        "task": [
            "task", "ID", "(", "ParamList", ")",
            "->", "Var_type", "ID", "{", "Action_List", "}"
        ],
    },

    "ParamList": {
        "string": ["Param", "ParamTail"],
        "int": ["Param", "ParamTail"],
        "bool": ["Param", "ParamTail"],
        "list": ["Param", "ParamTail"],
        ")": [],  
    },

    "ParamTail": {
        ",": [",", "Param", "ParamTail"],
        ")": [],  
    },

    "Param": {
        "string": ["Var_type", "ID"],
        "int": ["Var_type", "ID"],
        "bool": ["Var_type", "ID"],
        "list": ["Var_type", "ID"],
    },

    "Var_type": {
        "string": ["string"],
        "int": ["int"],
        "bool": ["bool"],
        "list": ["list"],
    },

    "Action_List": {
        "action": ["Action", "Action_List"],
        "}": [],  
    },

    "Action": {
        "action": ["action", ":", "ID", "(", "argumentList", ")"],
    },

    "argumentList": {
        "NUM": ["Exp", "argumentTail"],
        "(": ["Exp", "argumentTail"],
        "ID": ["Exp", "argumentTail"],
        "Bool_literal": ["Exp", "argumentTail"],
        "String_literal": ["Exp", "argumentTail"],
        ")": [],  
    },

    "argumentTail": {
        ",": [",", "Exp", "argumentTail"],
        ")": [],     
        "]": [],   
    },

    "System_Program": {
        "system": ["system", "{", "System_List", "}"],
    },

    "System_List": {
        "list": ["System_stmt", "System_List"],
        "int": ["System_stmt", "System_List"],
        "string": ["System_stmt", "System_List"],
        "bool": ["System_stmt", "System_List"],
        "ID": ["System_stmt", "System_List"],
        "run": ["System_stmt", "System_List"],
        "if": ["System_stmt", "System_List"],
        "for": ["System_stmt", "System_List"],
        "}": [],  
    },

    "System_stmt": {
        "list": ["ListDec"],
        "int": ["VarDec"],
        "string": ["VarDec"],
        "bool": ["VarDec"],
        "ID": ["Assignment"],
        "run": ["RunStmt"],
        "if": ["ifStmt"],
        "for": ["ForLoop"],
    },

    "ListDec": {
        "list": ["list", "ID", "=", "[", "argumentList", "]"],
    },

    "VarDec": {
        "int": ["type", "ID", "=", "target_type"],
        "string": ["type", "ID", "=", "target_type"],
        "bool": ["type", "ID", "=", "target_type"],
    },

    "type": {
        "int": ["int"],
        "string": ["string"],
        "bool": ["bool"],
    },

    "target_type": {
        "NUM": ["Exp"],
        "(": ["Exp"],
        "ID": ["Exp"],
        "Bool_literal": ["Exp"],
        "String_literal": ["Exp"],
        "run": ["RunStmt"],
    },

    "RunStmt": {
        "run": ["run", "ID", ".", "ID", "(", "argumentList", ")"],
    },

    "Assignment": {
        "ID": ["ID", "=", "Exp"],
    },

    "Exp": {
        "NUM": ["term", "Exp'"],
        "(": ["term", "Exp'"],
        "ID": ["term", "Exp'"],
        "Bool_literal": ["term", "Exp'"],
        "String_literal": ["term", "Exp'"],
    },

    "Exp'": {
        "+": ["+", "term", "Exp'"],
        "-": ["-", "term", "Exp'"],

        ",": [],
        ")": [],
        "]": [],
        "==": [],
        "!=": [],
        "<": [],
        ">": [],
        "<=": [],
        ">=": [],
        "{": [],
        "list": [],
        "int": [],
        "string": [],
        "bool": [],
        "ID": [],
        "run": [],
        "if": [],
        "for": [],
        "}": [],
        "$": [],
    },

    "term": {
        "NUM": ["factor", "Term'"],
        "(": ["factor", "Term'"],
        "ID": ["factor", "Term'"],
        "Bool_literal": ["factor", "Term'"],
        "String_literal": ["factor", "Term'"],
    },

    "Term'": {
        "*": ["*", "factor", "Term'"],
        "/": ["/", "factor", "Term'"],

        "+": [],
        "-": [],
        ",": [],
        ")": [],
        "]": [],
        "==": [],
        "!=": [],
        "<": [],
        ">": [],
        "<=": [],
        ">=": [],
        "{": [],
        "list": [],
        "int": [],
        "string": [],
        "bool": [],
        "ID": [],
        "run": [],
        "if": [],
        "for": [],
        "}": [],
        "$": [],
    },

    "factor": {
        "NUM": ["NUM"],
        "(": ["(", "Exp", ")"],
        "ID": ["ID"],
        "Bool_literal": ["Bool_literal"],
        "String_literal": ["String_literal"],
    },

    "ifStmt": {
        "if": ["if", "Exp", "OP", "Exp", "{", "System_List", "}"],
    },

    "OP": {
        "==": ["=="],
        "!=": ["!="],
        "<": ["<"],
        ">": [">"],
        "<=": ["<="],
        ">=": [">="],
    },

    "ForLoop": {
        "for": ["for", "ID", "in", "ID", "{", "System_List", "}"],
    },
}


# Non-terminals
NON_TERMINALS = set(PARSING_TABLE.keys())
#used to catch all non-terminals in grammar 


# Parser
def parse(tokens):
    if tokens:
        eof_line = tokens[-1].line
        eof_col = tokens[-1].column + len(tokens[-1].value)
    else:
        eof_line = 1
        eof_col = 1

    tokens = tokens + [Token("$", "$", eof_line, eof_col)] # just adding the EOF token to the list

    stack = ["$", "Program"]
    index = 0

    while stack:
        top = stack[-1]  # peek, do not pop yet
        current_token = tokens[index]
        current_type = current_token.type

        # Accept
        if top == "$" and current_type == "$":
            print("Parse successful")
            return True

        # Terminal
        if top not in NON_TERMINALS:
            if top == current_type:
                stack.pop()
                index += 1
            else:
                print(
                    f"Syntax error at line {current_token.line}, column {current_token.column}: "
                    f"unexpected token '{current_token.value}'"
                )
                return False

        # Non-terminal
        else:
            production = PARSING_TABLE.get(top, {}).get(current_type) #table[top][current_type]

            if production is None:
                print(
                    f"Syntax error at line {current_token.line}, column {current_token.column}: "
                    f"unexpected token '{current_token.value}'"
                )
                return False

            stack.pop()  

            for symbol in reversed(production): #reverse since we are pushing onto the stack, and we want the first symbol of the production to be on top
                if symbol != "ε":
                    stack.append(symbol)

    current_token = tokens[index]
    print(
        f"Syntax error at line {current_token.line}, column {current_token.column}: "
        f"unexpected token '{current_token.value}'"
    )
    return False
#this is just defensive, if the stack correctly matched everything, then return true would have been hit.


# Main
def main():
    if len(sys.argv) != 2:
        print("Usage: python dsl_parser.py <source_file>")
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
        print(f"Lexical error: {error}")
        sys.exit(1)

    success = parse(tokens)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
