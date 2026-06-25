# -*- coding: utf-8 -*-
"""
ll_grammar.py
由 lr_grammar.py 消除左递归 + 左因子分解后得到的 LL(1) 文法。
Token 类型名与 lexer.py 输出完全一致。
"""

START_SYMBOL = "program"

# ── 终结符集合（与 lexer.py 输出 Token 类型一致） ──
TERMINALS = {
    # 关键字
    "INT", "FLOAT", "VOID", "IF", "ELSE", "WHILE", "FOR", "RETURN",
    # 标识符 / 字面量
    "ID", "INTEGER",
    # 运算符
    "ASSIGN", "LE", "LT", "GT", "GE", "EQ", "NE", "PLUS", "MINUS", "STAR", "DIV",
    # 界符
    "SEMICOLON", "COMMA", "LPAREN", "RPAREN", "LBRACKET", "RBRACKET", "LBRACE", "RBRACE",
}

# ── 非终结符集合 ──
NON_TERMINALS = {
    "program",
    "declaration-list", "declaration-list'",
    "declaration",
    "var-declaration", "fun-declaration",
    "init-declarator-list", "init-declarator-list'",
    "init-declarator", "init-declarator'",
    "type-specifier",
    "params", "param-list", "param-list'", "param", "param'",
    "compound-stmt",
    "statement-list", "statement-list'",
    "statement",
    "expression-stmt",
    "selection-stmt", "selection-stmt'",
    "iteration-stmt",
    "for-init-stmt", "expression-or-empty",
    "return-stmt", "return-stmt'",
    "expression", "expression'",
    "expression-bracket-tail",
    "var", "var'",
    "simple-expression", "simple-expression'",
    "simple-expression-tail",
    "additive-expression", "additive-expression'",
    "term", "term'",
    "relop", "addop", "mulop",
    "factor", "factor'",
    "call",
    "args", "arg-list", "arg-list'",
}

# ── LL(1) 产生式（已消除左递归、已左因子分解） ──
# ε 表示空串
GRAMMAR_RULES = {
    # ────────── 1. 程序结构 ──────────
    "program": [["declaration-list"]],

    "declaration-list": [["declaration", "declaration-list'"]],
    "declaration-list'": [["declaration", "declaration-list'"], ["ε"]],

    "declaration": [
        ["var-declaration"],
        ["fun-declaration"],
    ],

    # ────────── 2. 变量声明 ──────────
    "var-declaration": [["type-specifier", "init-declarator-list", "SEMICOLON"]],

    "init-declarator-list": [["init-declarator", "init-declarator-list'"]],
    "init-declarator-list'": [["COMMA", "init-declarator", "init-declarator-list'"], ["ε"]],

    "init-declarator": [["ID", "init-declarator'"]],
    "init-declarator'": [
        ["ASSIGN", "expression"],
        ["LBRACKET", "INTEGER", "RBRACKET"],
        ["ε"],
    ],

    # ────────── 3. 类型与函数 ──────────
    "type-specifier": [["INT"], ["FLOAT"], ["VOID"]],

    "fun-declaration": [["type-specifier", "ID", "LPAREN", "params", "RPAREN", "compound-stmt"]],

    "params": [["param-list"], ["VOID"]],
    "param-list": [["param", "param-list'"]],
    "param-list'": [["COMMA", "param", "param-list'"], ["ε"]],
    "param": [["type-specifier", "ID", "param'"]],
    "param'": [["LBRACKET", "RBRACKET"], ["ε"]],

    # ────────── 4. 语句 ──────────
    "compound-stmt": [["LBRACE", "statement-list", "RBRACE"]],

    "statement-list": [["statement", "statement-list'"]],
    "statement-list'": [["statement", "statement-list'"], ["ε"]],

    "statement": [
        ["compound-stmt"],
        ["var-declaration"],
        ["expression-stmt"],
        ["selection-stmt"],
        ["iteration-stmt"],
        ["return-stmt"],
    ],

    "expression-stmt": [["expression", "SEMICOLON"], ["SEMICOLON"]],

    "selection-stmt": [["IF", "LPAREN", "expression", "RPAREN", "statement", "selection-stmt'"]],
    "selection-stmt'": [["ELSE", "statement"], ["ε"]],

    "iteration-stmt": [
        ["WHILE", "LPAREN", "expression", "RPAREN", "statement"],
        ["FOR", "LPAREN", "for-init-stmt", "SEMICOLON", "expression-or-empty",
         "SEMICOLON", "expression-or-empty", "RPAREN", "statement"],
    ],

    "for-init-stmt": [
        ["type-specifier", "init-declarator-list"],
        ["expression"],
        ["ε"],
    ],
    "expression-or-empty": [["expression"], ["ε"]],

    "return-stmt": [["RETURN", "return-stmt'"]],
    "return-stmt'": [["SEMICOLON"], ["expression", "SEMICOLON"]],

    # ────────── 5. 表达式（左因子分解后） ──────────
    "expression": [
        ["ID", "expression'"],
        ["LPAREN", "expression", "RPAREN", "simple-expression-tail"],
        ["INTEGER", "simple-expression-tail"],
        ["FLOAT", "simple-expression-tail"],
    ],

    "expression'": [
        ["ASSIGN", "expression"],                                        # ID = expr
        ["LBRACKET", "expression", "RBRACKET", "expression-bracket-tail"],  # ID[expr]
        ["LPAREN", "args", "RPAREN", "simple-expression-tail"],          # ID(args)
        ["simple-expression-tail"],                                       # ID 作为因子
    ],

    "expression-bracket-tail": [
        ["ASSIGN", "expression"],           # ID[expr] = expr
        ["simple-expression-tail"],         # ID[expr] 作为因子
    ],

    "var": [["ID", "var'"]],
    "var'": [["LBRACKET", "expression", "RBRACKET"], ["ε"]],

    "simple-expression": [["additive-expression", "simple-expression'"]],
    "simple-expression'": [["relop", "additive-expression"], ["ε"]],

    "simple-expression-tail": [["term'", "additive-expression'", "simple-expression'"]],

    "additive-expression": [["term", "additive-expression'"]],
    "additive-expression'": [["addop", "term", "additive-expression'"], ["ε"]],

    "term": [["factor", "term'"]],
    "term'": [["mulop", "factor", "term'"], ["ε"]],

    "relop": [["LE"], ["LT"], ["GT"], ["GE"], ["EQ"], ["NE"]],
    "addop": [["PLUS"], ["MINUS"]],
    "mulop": [["STAR"], ["DIV"]],

    "factor": [
        ["LPAREN", "expression", "RPAREN"],
        ["ID", "factor'"],
        ["INTEGER"],
        ["FLOAT"],
    ],

    "factor'": [
        ["LBRACKET", "expression", "RBRACKET"],   # ID[expr]
        ["LPAREN", "args", "RPAREN"],              # ID(args)
        ["ε"],
    ],

    "call": [["ID", "LPAREN", "args", "RPAREN"]],

    "args": [["arg-list"], ["ε"]],
    "arg-list": [["expression", "arg-list'"]],
    "arg-list'": [["COMMA", "expression", "arg-list'"], ["ε"]],
}
