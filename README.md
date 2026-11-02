<div align="center">

# 🤖 Agent DSL Compiler

**A hand-written lexer, recursive-descent parser and semantic analyser for a domain-specific language that describes AI agents, tools and tasks.**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Compilers](https://img.shields.io/badge/Compilers-Lexer%20%7C%20Parser%20%7C%20Semantics-8A2BE2?style=for-the-badge)

</div>

---

## ✨ What it does

The DSL lets you declare `agent`s, `tool`s, `task`s and `action`s, and then orchestrate them in a `system` block with `run`, `if`, `for … in`, typed variables (`int`, `string`, `bool`, `list`) and expressions.

| Stage | File | Highlights |
|-------|------|-----------|
| **Lexing** | `dsl_lexer.py` | Ordered regex token table, keywords before identifiers, line/column tracking, comment stripping |
| **Parsing** | `dsl_parser.py` | Recursive descent with lookahead (`peek`/`eat`), one method per grammar rule |
| **Semantics** | `semantic.py` | Symbol tables, type checking, declaration-before-use and scope rules, with clear `SemanticError`s |

## 🚀 Run it

```bash
python dsl_lexer.py program.dsl     # print the token stream
python dsl_parser.py program.dsl    # parse
python semantic.py program.dsl      # full semantic check
```

---

<sub>EECE 334 (Programming Languages) project, American University of Beirut.</sub>
