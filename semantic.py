import sys
from collections import namedtuple

from dsl_lexer import tokenize


# We re-do parsing here as a recursive-descent parser so we can build an AST
# alongside it. The grammar is exactly the LL(1) one in grammar.txt; the
# table-driven parser in dsl_parser.py only validates syntax, while here we
# also collect structured nodes for semantic analysis.

Token = namedtuple("Token", ["type", "value", "line", "column"])
# This defines what a token looks like: every token has a type 
# (like "agent", "ID", "{", etc.), a value (the actual text), and line/column for error reporting.


class SemanticError(Exception):
    pass
# Whenever parsing fails (unexpected token), this gets raised with a descriptive message.



# Recursive-descent parser producing an AST
# This recursive-descent parser follows the same grammar from grammar.txt but produces an AST
# (nested dictionaries) that the semantic analyzer can walk.

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens + [Token("$", "$", 0, 0)]         # The parser stores the token list and appends a sentinel $ token at the end (the end-of-input marker from your grammar).
        self.i = 0        # self.i is the current position — which token we're looking at.


    def peek(self, k=0):
        return self.tokens[self.i + k]
    # Look at the current token (or k tokens ahead) without consuming it. This is how the parser decides which grammar production to use
    # it peeks at the next token and branches.

    def eat(self, type_):
        tok = self.tokens[self.i]
        if tok.type != type_:
            raise SemanticError(
                f"Syntax error at line {tok.line}, column {tok.column}: "
                f"expected '{type_}', got '{tok.value}'"
            )
        self.i += 1
        return tok
    # This consumes a token. It checks that the current token matches what we expect. If not, it raises an error.
    # If yes, it advances self.i by 1 and returns the token (so we can grab its value/line later).



    # Parsing the top-level: parse_program
    # Program -> Agent_Program System_Program
    def parse_program(self):
        # so we keep parsing agents as long as the next token is agent.
        # This handles both one agent and many agents (and zero agents, since the while just doesn't execute).
        # Agent_Program -> Agent Agent_Program | epsilon
        agents = []
        while self.peek().type == "agent":
            agents.append(self.parse_agent())

        
        system = self.parse_system() # we expect system {...}


        if self.peek().type != "$":  # here it handles an error if the next token isnt $ 
            tok = self.peek()
            raise SemanticError(
                f"Syntax error at line {tok.line}, column {tok.column}: "
                f"trailing token '{tok.value}'"
            )
        return {"agents": agents, "system": system}
    # After parsing everything, the next token should be $ (end of input). 
    # If there's anything left over, it's an error. 
    # The return value is the root of the AST — a dictionary with all agents and the system block.



    # Agent -> agent ID { Agent_List }
    def parse_agent(self):
        kw = self.eat("agent") # consume the "agent" keyword
        name = self.eat("ID")  # consumes the agnet name
        self.eat("{")          # consumes the {
        tools = []
        tasks = []
        while self.peek().type in ("tool", "task"): # Agent_List
            if self.peek().type == "tool":
                self.eat("tool")
                tool_id = self.eat("ID")
                tools.append({"name": tool_id.value, "line": tool_id.line})
            else:
                tasks.append(self.parse_task()) 
        self.eat("}") # consume closing brace
        return {
            "name": name.value,
            "line": name.line,
            "tools": tools,
            "tasks": tasks,
        }

    # task_def -> task ID ( ParamList ) -> Var_type ID { Action_List }
    def parse_task(self):
        self.eat("task")
        name = self.eat("ID")
        self.eat("(")
        params = self.parse_param_list()
        self.eat(")")
        self.eat("->")
        ret_type = self.parse_var_type()
        ret_name = self.eat("ID")
        self.eat("{")
        actions = []
        while self.peek().type == "action":
            actions.append(self.parse_action())
        self.eat("}")


        return {
            "name": name.value,
            "line": name.line,
            "params": params,
            "return_type": ret_type,
            "return_name": ret_name.value,
            "actions": actions,
        }

    # ParamList  -> Param ParamTail | epsilon
    # ParamTail  -> , Param ParamTail | epsilon
    def parse_param_list(self):
        # If the next token is a type keyword, there's at least one parameter. 
        # Then it checks for commas — each comma means another parameter follows.
        # If the next token is ) right away, we get epsilon (empty list).
        params = []
        if self.peek().type in ("string", "int", "bool", "list"):
            params.append(self.parse_param())
            while self.peek().type == ",":
                self.eat(",")
                params.append(self.parse_param())
        return params

    # Param -> Var_type ID
    def parse_param(self):
        ptype = self.parse_var_type()
        pid = self.eat("ID")
        return {"type": ptype, "name": pid.value, "line": pid.line}
    
    # Var_type -> string | int | bool | list
    def parse_var_type(self):
        tok = self.peek()
        if tok.type in ("string", "int", "bool", "list"):
            self.i += 1
            return tok.value
        raise SemanticError(
            f"Syntax error at line {tok.line}, column {tok.column}: "
            f"expected a type, got '{tok.value}'"
        )

        # Each action calls a tool by name and passes arguments. The "tool" key in the returned 
        # dict is what the semantic analyzer later checks against the agent's declared tools.
    # Action -> action : ID ( argumentList )
    def parse_action(self):
        kw = self.eat("action")
        self.eat(":")
        name = self.eat("ID") # this is the tool name being called
        self.eat("(")
        args = self.parse_argument_list(end="(")
        self.eat(")")
        return {"tool": name.value, "line": name.line, "args": args}

        # argumentList -> Exp argumentTail | epsilon
        # If the next token can start an expression, parse one. 
        # Then keep going for each comma. The end parameter isn't actually used in the logic 
        # — it's just there for documentation.
    def parse_argument_list(self, end):
        args = []
        if self.peek().type in ("NUM", "(", "ID", "Bool_literal", "String_literal"):
            args.append(self.parse_exp())
            while self.peek().type == ",":
                self.eat(",")
                args.append(self.parse_exp())
        return args

    # System_Program -> system { System_List }
    def parse_system(self):
        self.eat("system")
        self.eat("{")
        stmts = self.parse_system_list(end="}")
        self.eat("}")
        return stmts
    
    # System_List -> System_stmt System_List | epsilon
    def parse_system_list(self, end):
        stmts = []
        while self.peek().type != end:
            stmts.append(self.parse_system_stmt())
        return stmts
# System_stmt -> ListDec | VarDec | Assignment | RunStmt | ifStmt | ForLoop
    def parse_system_stmt(self):
        #  it peeks at the next token to decide which production to use.
        t = self.peek().type
        if t == "list":
            return self.parse_list_dec()
        if t in ("int", "string", "bool"):
            return self.parse_var_dec()
        if t == "ID":
            return self.parse_assignment()
        if t == "run":
            stmt = self.parse_run_stmt()
            stmt["stmt"] = "run"
            return stmt
        if t == "if":
            return self.parse_if()
        if t == "for":
            return self.parse_for()
        tok = self.peek()
        raise SemanticError(
            f"Syntax error at line {tok.line}, column {tok.column}: "
            f"unexpected token '{tok.value}'"
        )
    # ListDec -> list ID = [ argumentList ]
    def parse_list_dec(self):
        kw = self.eat("list")  
        name = self.eat("ID")
        self.eat("=")
        self.eat("[")
        items = self.parse_argument_list(end="[")
        self.eat("]")
        return {
            "stmt": "list_dec",
            "name": name.value,
            "line": name.line,
            "items": items,
        }

    def parse_var_dec(self):
        ttok = self.peek()
        vtype = self.parse_var_type()  # int/string/bool only at this level (grammar)
        name = self.eat("ID")
        self.eat("=")
        if self.peek().type == "run":
            value = self.parse_run_stmt()
            value["kind"] = "run"
        else:
            value = {"kind": "exp", "exp": self.parse_exp()}
        return {
            "stmt": "var_dec",
            "type": vtype,
            "name": name.value,
            "line": name.line,
            "value": value,
        }

    def parse_assignment(self):
        name = self.eat("ID")
        self.eat("=")
        exp = self.parse_exp()
        return {
            "stmt": "assign",
            "name": name.value,
            "line": name.line,
            "exp": exp,
        }

    def parse_run_stmt(self):
        kw = self.eat("run")
        agent = self.eat("ID")
        self.eat(".")
        task = self.eat("ID")
        self.eat("(")
        args = self.parse_argument_list(end="(")
        self.eat(")")
        return {
            "kind": "run",
            "agent": agent.value,
            "task": task.value,
            "args": args,
            "line": agent.line,
        }

    def parse_if(self):
        kw = self.eat("if")
        left = self.parse_exp()
        op_tok = self.peek()
        if op_tok.type not in ("==", "!=", "<", ">", "<=", ">="):
            raise SemanticError(
                f"Syntax error at line {op_tok.line}, column {op_tok.column}: "
                f"expected comparison operator"
            )
        self.i += 1
        right = self.parse_exp()
        self.eat("{")
        body = self.parse_system_list(end="}")
        self.eat("}")
        return {
            "stmt": "if",
            "left": left,
            "op": op_tok.type,
            "right": right,
            "body": body,
            "line": kw.line,
        }

    def parse_for(self):
        kw = self.eat("for")
        var = self.eat("ID")
        self.eat("in")
        coll = self.eat("ID")
        self.eat("{")
        body = self.parse_system_list(end="}")
        self.eat("}")
        return {
            "stmt": "for",
            "var": var.value,
            "collection": coll.value,
            "body": body,
            "line": kw.line,
            "coll_line": coll.line,
        }

    # Expressions — keep enough info to type-check
    def parse_exp(self):
        left = self.parse_term()
        while self.peek().type in ("+", "-"):
            op = self.peek().type
            self.i += 1
            right = self.parse_term()
            left = {"node": "binop", "op": op, "left": left, "right": right}
        return left

    def parse_term(self):
        left = self.parse_factor()
        while self.peek().type in ("*", "/"):
            op = self.peek().type
            self.i += 1
            right = self.parse_factor()
            left = {"node": "binop", "op": op, "left": left, "right": right}
        return left

    def parse_factor(self):
        tok = self.peek()
        if tok.type == "NUM":
            self.i += 1
            return {"node": "num", "value": tok.value, "line": tok.line}
        if tok.type == "(":
            self.eat("(")
            e = self.parse_exp()
            self.eat(")")
            return e
        if tok.type == "ID":
            self.i += 1
            return {"node": "id", "name": tok.value, "line": tok.line}
        if tok.type == "Bool_literal":
            self.i += 1
            return {"node": "bool", "value": tok.value, "line": tok.line}
        if tok.type == "String_literal":
            self.i += 1
            return {"node": "string", "value": tok.value, "line": tok.line}
        raise SemanticError(
            f"Syntax error at line {tok.line}, column {tok.column}: "
            f"unexpected token '{tok.value}' in expression"
        )


# Semantic analyser

class Analyser:
    def __init__(self):
        self.agents = {}        # agent name -> { tools: {name: line}, tasks: {name: task_node} }
        self.variables = {}     # system-scope variable name -> type
        self.errors = []
        # self.agents — the agents symbol table 
        # self.variables — the system variables table 
        # self.errors — accumulates all semantic errors instead of stopping at the first one
    
    def err(self, line, msg):
        self.errors.append(f"Semantic error at line {line}: {msg}")


    # --- Pass 1: collect agents, tools, tasks
    def collect_agents(self, program):
        for agent in program["agents"]:
            if agent["name"] in self.agents:
                self.err(agent["line"], f"agent '{agent['name']}' redeclared")
                continue
            # Walk every agent in the AST. If an agent name already exists → duplicate agent error. 
            # The continue skips processing it further so we don't overwrite.



            tools = {}
            for t in agent["tools"]:
                if t["name"] in tools:
                    self.err(t["line"], f"tool '{t['name']}' redeclared in agent '{agent['name']}'")
                else:
                    tools[t["name"]] = t["line"]
            # Build the tools table for this agent.
            # If the same tool name appears twice inside one agent → error. 
            # This dict maps tool name → line number.


            tasks = {}
            for task in agent["tasks"]:
                if task["name"] in tasks:
                    self.err(task["line"], f"task '{task['name']}' redeclared in agent '{agent['name']}'")
                else:
                    tasks[task["name"]] = task
            # Build the tasks table for this agent. 
            # Maps task name → the full task AST node (so we can later check parameters and return types).


            self.agents[agent["name"]] = {"tools": tools, "tasks": tasks}
            # Store everything in the agents symbol table.

    # --- Pass 2: validate each agent body (actions reference declared tools)
    def check_agents(self, program):
        for agent in program["agents"]:
            entry = self.agents.get(agent["name"])
            if entry is None:
                continue
            tools = entry["tools"]
            for task in agent["tasks"]:
                # parameter scope is local to the task
                local_vars = {p["name"]: p["type"] for p in task["params"]}
                # the named return is also a local
                local_vars[task["return_name"]] = task["return_type"]
                # For each task, build a local scope containing the task's parameters and its return variable. 
                # For example, task gather(string topic) -> string data creates {"topic": "string", "data": "string"}

                for action in task["actions"]:
                    if action["tool"] not in tools:
                        self.err(
                            action["line"],
                            f"tool '{action['tool']}' used in action is not declared in agent '{agent['name']}'",
                        )
                        # Tool declaration check: if an action references a tool name that isn't in this agent's tools dict → error. For example,
                        # if action: calculator(x) but calculator was never declared with tool calculator.


                    # type-check args against ... well, we don't know the tool signature,
                    # but we can at least make sure every ID referenced exists in scope.
                    for arg in action["args"]:
                        self.check_exp(arg, local_vars)  # Also check that any variables used in action arguments actually exist in scope.

    # --- Pass 3: walk the system block
    def check_system(self, program):
        self.walk_stmts(program["system"], self.variables)

    def walk_stmts(self, stmts, scope):   #
        for s in stmts:                   #
            self.walk_stmt(s, scope)      #

    def walk_stmt(self, s, scope): # the core statment checker 
        kind = s["stmt"]
        # List declaration:  
        if kind == "list_dec":
            if s["name"] in scope:
                self.err(s["line"], f"variable '{s['name']}' redeclared")
            for item in s["items"]:
                self.check_exp(item, scope)
            scope[s["name"]] = "list"
            # Check for variable redeclaration. 
            # Check each item expression is valid. 
            # Then add the variable to the scope as type "list".

        # Variable declaration:
        elif kind == "var_dec":
            if s["name"] in scope:
                self.err(s["line"], f"variable '{s['name']}' redeclared")
            value = s["value"]
            if value["kind"] == "exp":
                etype = self.check_exp(value["exp"], scope)
                if etype is not None and etype != s["type"]:
                    self.err(
                        s["line"],
                        f"type mismatch: variable '{s['name']}' declared {s['type']} "
                        f"but assigned {etype}",
                    )
                    # This is the type checking rule. 
                    # If you write int topic = "AI", check_exp returns "string", 
                    # the declared type is "int", they don't match → error.



            else:
                rtype = self.check_run(value, scope)
                if rtype is not None and rtype != s["type"]:
                    self.err(
                        s["line"],
                        f"type mismatch: variable '{s['name']}' declared {s['type']} "
                        f"but run returns {rtype}",
                    )
            scope[s["name"]] = s["type"]
            # If the value is a run statement, check_run returns the task's return type. 
            # Same type mismatch check.



        elif kind == "assign":
            if s["name"] not in scope:
                self.err(s["line"], f"variable '{s['name']}' used before declaration")
                self.check_exp(s["exp"], scope)
            else:
                etype = self.check_exp(s["exp"], scope)
                declared = scope[s["name"]]
                if etype is not None and etype != declared:
                    self.err(
                        s["line"],
                        f"type mismatch: cannot assign {etype} to {declared} variable '{s['name']}'",
                    )

        elif kind == "run":
            self.check_run(s, scope)

        elif kind == "if":
            lt = self.check_exp(s["left"], scope)
            rt = self.check_exp(s["right"], scope)
            if lt is not None and rt is not None and lt != rt:
                self.err(
                    s["line"],
                    f"type mismatch in if comparison: {lt} {s['op']} {rt}",
                )
            self.walk_stmts(s["body"], scope)

        elif kind == "for":
            if s["collection"] not in scope:
                self.err(
                    s["coll_line"],
                    f"variable '{s['collection']}' used before declaration",
                )
            elif scope[s["collection"]] != "list":
                self.err(
                    s["coll_line"],
                    f"for-loop expects a list, but '{s['collection']}' is {scope[s['collection']]}",
                )
            inner = dict(scope)
            # element type is unknown statically — give the loop variable a sentinel
            inner[s["var"]] = "any"
            self.walk_stmts(s["body"], inner)
            # bindings made inside the loop are local; do not leak

    # --- run Agent.task(...)
    def check_run(self, node, scope):
        agent_name = node["agent"]
        task_name = node["task"]
        line = node["line"]

        agent = self.agents.get(agent_name)
        if agent is None:
            self.err(line, f"agent '{agent_name}' is not defined")
            for a in node["args"]:
                self.check_exp(a, scope)
            return None
        # Agent existence: if run Editor.process(data) but Editor was never declared as an agent → error.



        task = agent["tasks"].get(task_name)
        if task is None:
            self.err(line, f"task '{task_name}' is not defined in agent '{agent_name}'")
            for a in node["args"]:
                self.check_exp(a, scope)
            return None
        # Task existence: if run Researcher.search(topic) but there's no task called search in Researcher → error.

        params = task["params"]
        if len(node["args"]) != len(params):
            self.err(
                line,
                f"call to {agent_name}.{task_name} expects {len(params)} argument(s), got {len(node['args'])}",
            )
            # Parameter count check: number of arguments must match number of parameters.
        for arg, param in zip(node["args"], params):
            atype = self.check_exp(arg, scope)
            if atype is not None and atype != "any" and atype != param["type"]:
                self.err(
                    line,
                    f"argument type mismatch on parameter '{param['name']}' "
                    f"of {agent_name}.{task_name}: expected {param['type']}, got {atype}",
                )
        return task["return_type"]
    # Parameter type checking from Section G: 
    # each argument's type must match the corresponding parameter's
    # declared type. Finally returns the task's return type so the 
    # caller can do type checking on the result.

    # --- expressions
    def check_exp(self, node, scope):
        n = node.get("node")
        if n == "num":
            return "int"
        if n == "string":
            return "string"
        if n == "bool":
            return "bool"
        
        if n == "id":
            if node["name"] not in scope:
                self.err(node["line"], f"variable '{node['name']}' used before declaration")
                return None
            return scope[node["name"]]
        # Variable declaration check: if a variable is used in an expression but isn't in scope → error. 
        # Otherwise return its type from the symbol table.

        if n == "binop":
            lt = self.check_exp(node["left"], scope)
            rt = self.check_exp(node["right"], scope)
            op = node["op"]
            if lt == "any" or rt == "any":
                return lt if rt == "any" else rt
            # For "any" types (from loop variables), be lenient — assume the other side's type.


            if op in ("+",) and lt == "string" and rt == "string":
                return "string"
            if lt == "int" and rt == "int":
                return "int"
            if lt is not None and rt is not None:
                self.err(
                    node["left"].get("line", 0) or 0,
                    f"type mismatch in '{op}' expression: {lt} {op} {rt}",
                )
            return None
        # Type checking in expressions: string + string is allowed (concatenation), 
        # int op int is allowed for all arithmetic. Anything else (like int + string) is a type mismatch.

        return None

    def analyse(self, program):
        self.collect_agents(program) # Pass 1: build symbol tables
        self.check_agents(program)   # Pass 2: validate agent bodies
        self.check_system(program)   # Pass 3: validate system block
        return self.errors

# This formats the symbol tables for display — printing agents, their tools, their tasks 
# (with signatures), and system variables. 
# This matches the project requirement to show symbol tables.
def format_symbol_tables(analyser):
    lines = []
    lines.append("Symbol tables:")
    lines.append("  agents = {")
    for name in analyser.agents:
        lines.append(f"    {name!r},")
    lines.append("  }")
    for name, entry in analyser.agents.items():
        lines.append(f"  tools[{name}] = {{")
        for t in entry["tools"]:
            lines.append(f"    {t!r},")
        lines.append("  }")
        lines.append(f"  tasks[{name}] = {{")
        for tname, t in entry["tasks"].items():
            sig = ", ".join(f"{p['type']} {p['name']}" for p in t["params"])
            lines.append(f"    {tname!r}: ({sig}) -> {t['return_type']},")
        lines.append("  }")
    lines.append("  variables = {")
    for v, t in analyser.variables.items():
        lines.append(f"    {v!r}: {t!r},")
    lines.append("  }")
    return "\n".join(lines)


def main():
    if len(sys.argv) != 2:
        print("Usage: python dsl_semantic.py <source_file>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, "r", encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: file '{filename}' not found.")
        sys.exit(1)

    try:
        tokens = tokenize(code)
    except SyntaxError as e:
        print(f"Lexical error: {e}")
        sys.exit(1)

    parser = Parser(tokens)
    try:
        program = parser.parse_program()
    except SemanticError as e:
        print(e)
        sys.exit(1)

    analyser = Analyser()
    errors = analyser.analyse(program)

    print(format_symbol_tables(analyser))
    print()

    if errors:
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("Semantic analysis successful")


if __name__ == "__main__":
    main()