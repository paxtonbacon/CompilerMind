# -*- coding: utf-8 -*-
"""
LR_grammar.py
优化后的 C-Minus 语法定义文件。
支持特性：
1. int a, b, c; / float a, b, c; (多变量声明)
2. int a = 8; / float a = 8; (变量声明并初始化)
3. for (int i = 0; i < k; i = i + 1) {} (for循环内直接声明并初始化局部变量)
"""

# 增广文法的起始符号
START_SYMBOL = "program"

# 完整的优化版 C-Minus 上下文无关文法 (CFG)
C_MINUS_GRAMMAR = """
program → declaration-list

declaration-list → declaration-list declaration | declaration

declaration → var-declaration | fun-declaration

var-declaration → type-specifier init-declarator-list ;

init-declarator-list → init-declarator-list , init-declarator | init-declarator

init-declarator → ID 
                | ID = expression 
                | ID [ INTEGER ]

type-specifier → int | float | void

fun-declaration → type-specifier ID ( params ) compound-stmt

params → param-list | void

param-list → param-list , param | param

param → type-specifier ID | type-specifier ID [ ]

compound-stmt → { statement-list }

statement-list → statement-list statement | empty

statement → compound-stmt | var-declaration | expression-stmt | selection-stmt | iteration-stmt | return-stmt

expression-stmt → expression ; | ;

selection-stmt → if ( expression ) statement | if ( expression ) statement else statement

iteration-stmt → while ( expression ) statement 
               | for ( for-init-stmt ; expression-or-empty ; expression-or-empty ) statement

for-init-stmt → type-specifier init-declarator-list | expression | empty

expression-or-empty → expression | empty

return-stmt → return ; | return expression ;

expression → var = expression | simple-expression

var → ID | ID [ expression ]

simple-expression → additive-expression relop additive-expression | additive-expression

relop → <= | < | > | >= | == | !=

additive-expression → additive-expression addop term | term

addop → + | -

term → term mulop factor | factor

mulop → * | /

factor → ( expression ) | var | call | INTEGER | FLOAT

call → ID ( args )

args → arg-list | empty

arg-list → arg-list , expression | expression
"""