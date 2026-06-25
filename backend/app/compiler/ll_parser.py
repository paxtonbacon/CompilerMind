# -*- coding: utf-8 -*-
"""
ll_parser.py — 手写递归下降 LL(1) 解析器
配合 ll_grammar.py 使用，同时计算 FIRST/FOLLOW/预测分析表供前端展示。
"""

from typing import List, Dict, Any, Set, Tuple, Optional
from .ll_grammar import GRAMMAR_RULES, TERMINALS, NON_TERMINALS, START_SYMBOL
from .semantic import SemanticAnalyzer
from .pcode import PCodeGenerator


# ═══════════════════════════════════════════════
#  AST 节点
# ═══════════════════════════════════════════════
class ASTNode:
    def __init__(self, name: str, value: str = None):
        self.name = name
        self.value = value
        self.children: List['ASTNode'] = []

    def to_dict(self) -> Dict[str, Any]:
        label = f"{self.name}({self.value})" if self.value else self.name
        return {
            "name": label,
            "children": [c.to_dict() for c in self.children]
        }

    def to_text_tree(self, prefix: str = "", is_last: bool = True) -> str:
        connector = "└── " if is_last else "├── "
        label = f"{self.name}[{self.value}]" if self.value else self.name
        result = prefix + connector + label + "\n"
        extension = "    " if is_last else "│   "
        for i, child in enumerate(self.children):
            result += child.to_text_tree(prefix + extension, i == len(self.children) - 1)
        return result


# ═══════════════════════════════════════════════
#  LL(1) 解析引擎（递归下降 + FIRST/FOLLOW/表）
# ═══════════════════════════════════════════════
class LL1CompilerEngine:
    def __init__(self):
        self.rules = GRAMMAR_RULES
        self.start_symbol = START_SYMBOL
        self.non_terminals = NON_TERMINALS
        self.terminals = TERMINALS

        # 计算 FIRST / FOLLOW / 预测表（供前端展示）
        self.first_sets: Dict[str, Set[str]] = {}
        self.follow_sets: Dict[str, Set[str]] = {}
        self.predict_table: Dict[str, Dict[str, List[str]]] = {}
        self.conflicts: List[str] = []

        self._compute_first_sets()
        self._compute_follow_sets()
        self._build_predict_table()

    # ────── FIRST 集 ──────
    def _compute_first_sets(self):
        for nt in self.non_terminals:
            self.first_sets[nt] = set()
        for t in self.terminals:
            self.first_sets[t] = {t}
        self.first_sets["ε"] = {"ε"}

        changed = True
        while changed:
            changed = False
            for nt, prods in self.rules.items():
                for prod in prods:
                    before = len(self.first_sets[nt])
                    if prod == ["ε"]:
                        self.first_sets[nt].add("ε")
                    else:
                        for sym in prod:
                            self.first_sets[nt].update(self.first_sets.get(sym, {sym}) - {"ε"})
                            if "ε" not in self.first_sets.get(sym, {sym}):
                                break
                        else:
                            self.first_sets[nt].add("ε")
                    if len(self.first_sets[nt]) > before:
                        changed = True

    # ────── FOLLOW 集 ──────
    def _compute_follow_sets(self):
        for nt in self.non_terminals:
            self.follow_sets[nt] = set()
        self.follow_sets[self.start_symbol].add("$")

        changed = True
        while changed:
            changed = False
            for nt, prods in self.rules.items():
                for prod in prods:
                    if prod == ["ε"]:
                        continue
                    for i, sym in enumerate(prod):
                        if sym not in self.non_terminals:
                            continue
                        before = len(self.follow_sets[sym])
                        tail = prod[i + 1:]
                        if not tail:
                            self.follow_sets[sym].update(self.follow_sets[nt])
                        else:
                            all_nullable = True
                            for nxt in tail:
                                self.follow_sets[sym].update(
                                    self.first_sets.get(nxt, {nxt}) - {"ε"}
                                )
                                if "ε" not in self.first_sets.get(nxt, {nxt}):
                                    all_nullable = False
                                    break
                            if all_nullable:
                                self.follow_sets[sym].update(self.follow_sets[nt])
                        if len(self.follow_sets[sym]) > before:
                            changed = True

    # ────── 预测分析表 ──────
    def _build_predict_table(self):
        for nt in self.non_terminals:
            self.predict_table[nt] = {}

        for nt, prods in self.rules.items():
            for prod in prods:
                prod_first: Set[str] = set()
                if prod == ["ε"]:
                    prod_first.add("ε")
                else:
                    for sym in prod:
                        prod_first.update(self.first_sets.get(sym, {sym}) - {"ε"})
                        if "ε" not in self.first_sets.get(sym, {sym}):
                            break
                    else:
                        prod_first.add("ε")

                for t in prod_first:
                    if t != "ε":
                        if t in self.predict_table[nt]:
                            self.conflicts.append(
                                f"FIRST/FIRST 冲突 [{nt}][{t}]: "
                                f"{self.predict_table[nt][t]} vs {prod}"
                            )
                        self.predict_table[nt][t] = prod

                if "ε" in prod_first:
                    for t in self.follow_sets[nt]:
                        if t in self.predict_table[nt] and self.predict_table[nt][t] != prod:
                            if nt == "selection-stmt'" and t == "ELSE" and prod == ["ε"]:
                                continue  # 悬空 else 默认 shift 优先
                            self.conflicts.append(
                                f"FIRST/FOLLOW 冲突 [{nt}][{t}]: "
                                f"{self.predict_table[nt][t]} vs {prod}"
                            )
                        self.predict_table[nt][t] = prod

    # ────── 扁平化分析表 ──────
    def get_serializable_table(self) -> List[Dict[str, str]]:
        rows = []
        for nt, row in self.predict_table.items():
            for t, prod in row.items():
                rows.append({
                    "non_terminal": nt,
                    "terminal": t,
                    "production": f"{nt} → {' '.join(prod)}"
                })
        return rows

    # ═══════════════════════════════════════════════
    #  主解析入口
    # ═══════════════════════════════════════════════
    def parse(self, tokens) -> Dict[str, Any]:
        """
        接收 Token 对象列表或 (type, value) 元组列表，
        返回与 SyntaxResponse 匹配的字典。
        """
        # ── 1. 规范化 Token ──
        if tokens and hasattr(tokens[0], 'type'):
            self._tokens = [(t.type, t.value, t.line) for t in tokens]
        else:
            self._tokens = [(t[0], t[1], -1) for t in tokens]
        # 补结束符
        self._tokens.append(("$", "$", -1))

        self._pos = 0
        self._derivation: List[str] = []
        self._errors: List[str] = []
        self._panic_sync = {  # 恐慌模式同步符号
            "SEMICOLON", "RBRACE", "RPAREN", "RBRACKET",
            "INT", "FLOAT", "VOID", "IF", "ELSE", "WHILE", "FOR", "RETURN",
        }

        # ── 2. 递归下降解析 ──
        ast = self._parse_program()

        # ── 3. 语义分析（即使有语法错误也尽力分析已构建的 AST） ──
        semantic = SemanticAnalyzer()
        sem_result = semantic.analyze(ast) if ast else {
            "symbol_table": [], "semantic_errors": ["解析失败，跳过语义分析"]
        }

        # ── 4. P-Code 生成（即使有语法错误也尽力生成） ──
        pcode_gen = PCodeGenerator()
        pcode = pcode_gen.generate(ast) if ast else [
            "; 解析失败，无法生成中间代码"
        ]

        # ── 5. 构建返回（只要有 AST 就生成文本树） ──
        text_tree = ast.to_text_tree() if ast else "解析失败，无法构建语法树"

        return {
            "first_sets": {k: sorted(list(v)) for k, v in self.first_sets.items()
                           if k in self.non_terminals},
            "follow_sets": {k: sorted(list(v)) for k, v in self.follow_sets.items()},
            "predict_table": self.get_serializable_table(),
            "conflicts": self.conflicts,
            "ast": ast.to_dict() if ast else None,
            "derivation_steps": self._derivation,
            "text_tree": text_tree,
            "syntax_errors": self._errors,
            "symbol_table": sem_result["symbol_table"],
            "semantic_errors": sem_result["semantic_errors"],
            "pcode": pcode,
        }

    # ────── Token 辅助方法 ──────
    def _peek_type(self) -> str:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos][0]
        return "$"

    def _peek_val(self) -> str:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos][1]
        return ""

    def _advance(self) -> Tuple[str, str, int]:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _match(self, expected_type: str) -> Optional[ASTNode]:
        """消费一个终结符，返回叶子节点；失败则记录错误并返回 None"""
        if self._peek_type() == expected_type:
            tok_type, tok_val, _ = self._advance()
            return ASTNode(tok_type, tok_val)
        else:
            self._errors.append(
                f"语法错误：期待 '{expected_type}'，实际遇到 "
                f"'{self._peek_type()}'({self._peek_val()})"
            )
            # 恐慌模式：跳过直到同步符号
            self._panic_skip()
            return None

    def _panic_skip(self):
        """恐慌模式：跳过 Token 直到遇到同步符号或结束"""
        while self._pos < len(self._tokens) and self._peek_type() != "$":
            if self._peek_type() in self._panic_sync:
                break
            self._pos += 1

    def _record_derivation(self, lhs: str, rhs: List[str]):
        self._derivation.append(f"{lhs} → {' '.join(rhs)}")

    # ═══════════════════════════════════════════════
    #  递归下降解析函数（每个非终结符一个方法）
    # ═══════════════════════════════════════════════

    def _parse_program(self) -> ASTNode:
        node = ASTNode("program")
        self._record_derivation("program", ["declaration-list"])
        node.children.append(self._parse_declaration_list())
        return node

    # ── declaration-list ──
    def _parse_declaration_list(self) -> ASTNode:
        node = ASTNode("declaration-list")
        self._record_derivation("declaration-list",
                                ["declaration", "declaration-list'"])
        node.children.append(self._parse_declaration())
        # 循环处理 declaration-list' → declaration declaration-list' | ε
        while self._peek_type() in self.first_sets.get("declaration", set()):
            node.children.append(self._parse_declaration())
        return node

    # ── declaration ──
    def _parse_declaration(self) -> ASTNode:
        node = ASTNode("declaration")
        t = self._peek_type()

        if t in {"INT", "FLOAT", "VOID"}:
            # 需要前瞻：type-specifier ID ( → fun-declaration
            #           type-specifier ID ... → var-declaration
            saved = self._pos
            self._advance()  # 跳过 type-specifier
            has_id = (self._peek_type() == "ID")
            if has_id:
                id_saved = self._pos
                self._advance()  # 跳过 ID
                is_func = (self._peek_type() == "LPAREN")
                self._pos = saved
                if is_func:
                    self._record_derivation("declaration", ["fun-declaration"])
                    node.children.append(self._parse_fun_declaration())
                else:
                    self._record_derivation("declaration", ["var-declaration"])
                    node.children.append(self._parse_var_declaration())
            else:
                self._pos = saved
                self._record_derivation("declaration", ["var-declaration"])
                node.children.append(self._parse_var_declaration())
        else:
            self._errors.append(f"语法错误：declaration 无法以 '{t}'({self._peek_val()}) 开头")
            self._panic_skip()
        return node

    # ── var-declaration ──
    def _parse_var_declaration(self) -> ASTNode:
        node = ASTNode("var-declaration")
        self._record_derivation("var-declaration",
                                ["type-specifier", "init-declarator-list", "SEMICOLON"])
        node.children.append(self._parse_type_specifier())
        node.children.append(self._parse_init_declarator_list())
        node.children.append(self._match("SEMICOLON"))
        return node

    # ── init-declarator-list ──
    def _parse_init_declarator_list(self) -> ASTNode:
        node = ASTNode("init-declarator-list")
        self._record_derivation("init-declarator-list",
                                ["init-declarator", "init-declarator-list'"])
        node.children.append(self._parse_init_declarator())
        while self._peek_type() == "COMMA":
            self._match("COMMA")
            node.children.append(self._parse_init_declarator())
        return node

    def _parse_init_declarator(self) -> ASTNode:
        node = ASTNode("init-declarator")
        self._record_derivation("init-declarator", ["ID", "init-declarator'"])
        node.children.append(self._match("ID"))
        t = self._peek_type()
        if t == "ASSIGN":
            self._record_derivation("init-declarator'", ["ASSIGN", "expression"])
            node.children.append(self._match("ASSIGN"))
            node.children.append(self._parse_expression())
        elif t == "LBRACKET":
            self._record_derivation("init-declarator'",
                                    ["LBRACKET", "INTEGER", "RBRACKET"])
            node.children.append(self._match("LBRACKET"))
            node.children.append(self._match("INTEGER"))
            node.children.append(self._match("RBRACKET"))
        # else: ε
        return node

    # ── type-specifier ──
    def _parse_type_specifier(self) -> ASTNode:
        node = ASTNode("type-specifier")
        t = self._peek_type()
        if t in {"INT", "FLOAT", "VOID"}:
            self._record_derivation("type-specifier", [t])
            node.children.append(self._match(t))
        else:
            self._errors.append(f"语法错误：type-specifier 无法匹配 '{t}'")
            self._panic_skip()
        return node

    # ── fun-declaration ──
    def _parse_fun_declaration(self) -> ASTNode:
        node = ASTNode("fun-declaration")
        self._record_derivation("fun-declaration",
                                ["type-specifier", "ID", "LPAREN", "params",
                                 "RPAREN", "compound-stmt"])
        node.children.append(self._parse_type_specifier())
        node.children.append(self._match("ID"))
        node.children.append(self._match("LPAREN"))
        node.children.append(self._parse_params())
        node.children.append(self._match("RPAREN"))
        node.children.append(self._parse_compound_stmt())
        return node

    # ── params ──
    def _parse_params(self) -> ASTNode:
        node = ASTNode("params")
        t = self._peek_type()
        if t == "VOID":
            self._record_derivation("params", ["VOID"])
            node.children.append(self._match("VOID"))
        else:
            self._record_derivation("params", ["param-list"])
            node.children.append(self._parse_param_list())
        return node

    def _parse_param_list(self) -> ASTNode:
        node = ASTNode("param-list")
        self._record_derivation("param-list", ["param", "param-list'"])
        node.children.append(self._parse_param())
        while self._peek_type() == "COMMA":
            self._match("COMMA")
            node.children.append(self._parse_param())
        return node

    def _parse_param(self) -> ASTNode:
        node = ASTNode("param")
        self._record_derivation("param", ["type-specifier", "ID", "param'"])
        node.children.append(self._parse_type_specifier())
        node.children.append(self._match("ID"))
        if self._peek_type() == "LBRACKET":
            self._record_derivation("param'", ["LBRACKET", "RBRACKET"])
            node.children.append(self._match("LBRACKET"))
            node.children.append(self._match("RBRACKET"))
        return node

    # ── compound-stmt ──
    def _parse_compound_stmt(self) -> ASTNode:
        node = ASTNode("compound-stmt")
        self._record_derivation("compound-stmt",
                                ["LBRACE", "statement-list", "RBRACE"])
        node.children.append(self._match("LBRACE"))
        node.children.append(self._parse_statement_list())
        node.children.append(self._match("RBRACE"))
        return node

    # ── statement-list ──
    def _parse_statement_list(self) -> ASTNode:
        node = ASTNode("statement-list")
        stmt_first = self.first_sets.get("statement", set())
        while self._peek_type() in stmt_first:
            self._record_derivation("statement-list",
                                    ["statement", "statement-list'"])
            node.children.append(self._parse_statement())
        return node

    # ── statement ──
    def _parse_statement(self) -> ASTNode:
        node = ASTNode("statement")
        t = self._peek_type()

        if t == "LBRACE":
            self._record_derivation("statement", ["compound-stmt"])
            node.children.append(self._parse_compound_stmt())
        elif t in {"INT", "FLOAT", "VOID"}:
            self._record_derivation("statement", ["var-declaration"])
            node.children.append(self._parse_var_declaration())
        elif t == "IF":
            self._record_derivation("statement", ["selection-stmt"])
            node.children.append(self._parse_selection_stmt())
        elif t in {"WHILE", "FOR"}:
            self._record_derivation("statement", ["iteration-stmt"])
            node.children.append(self._parse_iteration_stmt())
        elif t == "RETURN":
            self._record_derivation("statement", ["return-stmt"])
            node.children.append(self._parse_return_stmt())
        elif t in {"SEMICOLON", "ID", "LPAREN", "INTEGER", "FLOAT"}:
            self._record_derivation("statement", ["expression-stmt"])
            node.children.append(self._parse_expression_stmt())
        else:
            self._errors.append(
                f"语法错误：statement 无法以 '{t}'({self._peek_val()}) 开头"
            )
            self._panic_skip()
        return node

    # ── expression-stmt ──
    def _parse_expression_stmt(self) -> ASTNode:
        node = ASTNode("expression-stmt")
        if self._peek_type() == "SEMICOLON":
            self._record_derivation("expression-stmt", ["SEMICOLON"])
            node.children.append(self._match("SEMICOLON"))
        else:
            self._record_derivation("expression-stmt",
                                    ["expression", "SEMICOLON"])
            node.children.append(self._parse_expression())
            node.children.append(self._match("SEMICOLON"))
        return node

    # ── selection-stmt ──
    def _parse_selection_stmt(self) -> ASTNode:
        node = ASTNode("selection-stmt")
        self._record_derivation("selection-stmt",
                                ["IF", "LPAREN", "expression", "RPAREN",
                                 "statement", "selection-stmt'"])
        node.children.append(self._match("IF"))
        node.children.append(self._match("LPAREN"))
        node.children.append(self._parse_expression())
        node.children.append(self._match("RPAREN"))
        node.children.append(self._parse_statement())
        if self._peek_type() == "ELSE":
            self._record_derivation("selection-stmt'", ["ELSE", "statement"])
            node.children.append(self._match("ELSE"))
            node.children.append(self._parse_statement())
        return node

    # ── iteration-stmt ──
    def _parse_iteration_stmt(self) -> ASTNode:
        node = ASTNode("iteration-stmt")
        t = self._peek_type()
        if t == "WHILE":
            self._record_derivation("iteration-stmt",
                                    ["WHILE", "LPAREN", "expression", "RPAREN",
                                     "statement"])
            node.children.append(self._match("WHILE"))
            node.children.append(self._match("LPAREN"))
            node.children.append(self._parse_expression())
            node.children.append(self._match("RPAREN"))
            node.children.append(self._parse_statement())
        elif t == "FOR":
            self._record_derivation("iteration-stmt",
                                    ["FOR", "LPAREN", "for-init-stmt",
                                     "SEMICOLON", "expression-or-empty",
                                     "SEMICOLON", "expression-or-empty",
                                     "RPAREN", "statement"])
            node.children.append(self._match("FOR"))
            node.children.append(self._match("LPAREN"))
            node.children.append(self._parse_for_init_stmt())
            node.children.append(self._match("SEMICOLON"))
            node.children.append(self._parse_expression_or_empty())
            node.children.append(self._match("SEMICOLON"))
            node.children.append(self._parse_expression_or_empty())
            node.children.append(self._match("RPAREN"))
            node.children.append(self._parse_statement())
        return node

    def _parse_for_init_stmt(self) -> ASTNode:
        node = ASTNode("for-init-stmt")
        t = self._peek_type()
        if t == "SEMICOLON":
            return node  # ε
        elif t in {"INT", "FLOAT", "VOID"}:
            self._record_derivation("for-init-stmt",
                                    ["type-specifier", "init-declarator-list"])
            node.children.append(self._parse_type_specifier())
            node.children.append(self._parse_init_declarator_list())
        else:
            self._record_derivation("for-init-stmt", ["expression"])
            node.children.append(self._parse_expression())
        return node

    def _parse_expression_or_empty(self) -> ASTNode:
        node = ASTNode("expression-or-empty")
        if self._peek_type() == "SEMICOLON":
            return node  # ε
        self._record_derivation("expression-or-empty", ["expression"])
        node.children.append(self._parse_expression())
        return node

    # ── return-stmt ──
    def _parse_return_stmt(self) -> ASTNode:
        node = ASTNode("return-stmt")
        self._record_derivation("return-stmt", ["RETURN", "return-stmt'"])
        node.children.append(self._match("RETURN"))
        if self._peek_type() == "SEMICOLON":
            self._record_derivation("return-stmt'", ["SEMICOLON"])
            node.children.append(self._match("SEMICOLON"))
        else:
            self._record_derivation("return-stmt'",
                                    ["expression", "SEMICOLON"])
            node.children.append(self._parse_expression())
            node.children.append(self._match("SEMICOLON"))
        return node

    # ── expression ──
    def _parse_expression(self) -> ASTNode:
        """左因子分解后的表达式解析"""
        node = ASTNode("expression")
        t = self._peek_type()

        if t == "ID":
            self._record_derivation("expression", ["ID", "expression'"])
            node.children.append(self._match("ID"))
            node.children.append(self._parse_expression_prime())
        elif t == "LPAREN":
            self._record_derivation("expression",
                                    ["LPAREN", "expression", "RPAREN",
                                     "simple-expression-tail"])
            node.children.append(self._match("LPAREN"))
            node.children.append(self._parse_expression())
            node.children.append(self._match("RPAREN"))
            node.children.append(self._parse_simple_expression_tail())
        elif t in {"INTEGER", "FLOAT"}:
            self._record_derivation("expression",
                                    [t, "simple-expression-tail"])
            node.children.append(self._match(t))
            node.children.append(self._parse_simple_expression_tail())
        else:
            self._errors.append(f"语法错误：expression 无法以 '{t}' 开头")
            self._panic_skip()
        return node

    def _parse_expression_prime(self) -> ASTNode:
        """expression' → ASSIGN expression
                       | LBRACKET expression RBRACKET expression-bracket-tail
                       | LPAREN args RPAREN simple-expression-tail
                       | simple-expression-tail"""
        node = ASTNode("expression'")
        t = self._peek_type()

        if t == "ASSIGN":
            self._record_derivation("expression'", ["ASSIGN", "expression"])
            node.children.append(self._match("ASSIGN"))
            node.children.append(self._parse_expression())
        elif t == "LBRACKET":
            self._record_derivation("expression'",
                                    ["LBRACKET", "expression", "RBRACKET",
                                     "expression-bracket-tail"])
            node.children.append(self._match("LBRACKET"))
            node.children.append(self._parse_expression())
            node.children.append(self._match("RBRACKET"))
            if self._peek_type() == "ASSIGN":
                self._record_derivation("expression-bracket-tail",
                                        ["ASSIGN", "expression"])
                node.children.append(self._match("ASSIGN"))
                node.children.append(self._parse_expression())
            else:
                node.children.append(self._parse_simple_expression_tail())
        elif t == "LPAREN":
            self._record_derivation("expression'",
                                    ["LPAREN", "args", "RPAREN",
                                     "simple-expression-tail"])
            node.children.append(self._match("LPAREN"))
            node.children.append(self._parse_args())
            node.children.append(self._match("RPAREN"))
            node.children.append(self._parse_simple_expression_tail())
        else:
            # simple-expression-tail
            child = self._parse_simple_expression_tail()
            if child.children:
                node.children.append(child)
        return node

    def _parse_simple_expression_tail(self) -> ASTNode:
        """
        simple-expression-tail → term' additive-expression' simple-expression'
        处理二元运算符链：mulop → addop → relop（按优先级从高到低）
        注意：这里不构建完整 AST，而是返回尾部节点供父级组装
        """
        node = ASTNode("simple-expression-tail")
        t = self._peek_type()

        # term': mulop factor term'  （处理 * /）
        while t in {"STAR", "DIV"}:
            child = ASTNode("term'")
            child.children.append(self._parse_mulop())
            child.children.append(self._parse_factor())
            node.children.append(child)
            t = self._peek_type()

        # additive-expression': addop term additive-expression'  （处理 + -）
        while t in {"PLUS", "MINUS"}:
            child = ASTNode("additive-expression'")
            child.children.append(self._parse_addop())
            child.children.append(self._parse_term())
            node.children.append(child)
            t = self._peek_type()

        # simple-expression': relop additive-expression  （处理比较）
        if t in {"LE", "LT", "GT", "GE", "EQ", "NE"}:
            child = ASTNode("simple-expression'")
            child.children.append(self._parse_relop())
            child.children.append(self._parse_additive_expression())
            node.children.append(child)

        return node

    # ── simple-expression ──
    def _parse_simple_expression(self) -> ASTNode:
        node = ASTNode("simple-expression")
        self._record_derivation("simple-expression",
                                ["additive-expression", "simple-expression'"])
        node.children.append(self._parse_additive_expression())
        t = self._peek_type()
        if t in {"LE", "LT", "GT", "GE", "EQ", "NE"}:
            self._record_derivation("simple-expression'",
                                    ["relop", "additive-expression"])
            node.children.append(self._parse_relop())
            node.children.append(self._parse_additive_expression())
        return node

    # ── additive-expression ──
    def _parse_additive_expression(self) -> ASTNode:
        node = ASTNode("additive-expression")
        self._record_derivation("additive-expression",
                                ["term", "additive-expression'"])
        node.children.append(self._parse_term())
        while self._peek_type() in {"PLUS", "MINUS"}:
            self._record_derivation("additive-expression'",
                                    ["addop", "term", "additive-expression'"])
            node.children.append(self._parse_addop())
            node.children.append(self._parse_term())
        return node

    # ── term ──
    def _parse_term(self) -> ASTNode:
        node = ASTNode("term")
        self._record_derivation("term", ["factor", "term'"])
        node.children.append(self._parse_factor())
        while self._peek_type() in {"STAR", "DIV"}:
            self._record_derivation("term'",
                                    ["mulop", "factor", "term'"])
            node.children.append(self._parse_mulop())
            node.children.append(self._parse_factor())
        return node

    # ── factor ──
    def _parse_factor(self) -> ASTNode:
        node = ASTNode("factor")
        t = self._peek_type()

        if t == "LPAREN":
            self._record_derivation("factor",
                                    ["LPAREN", "expression", "RPAREN"])
            node.children.append(self._match("LPAREN"))
            node.children.append(self._parse_expression())
            node.children.append(self._match("RPAREN"))
        elif t == "ID":
            self._record_derivation("factor", ["ID", "factor'"])
            node.children.append(self._match("ID"))
            nxt = self._peek_type()
            if nxt == "LBRACKET":
                self._record_derivation("factor'",
                                        ["LBRACKET", "expression", "RBRACKET"])
                node.children.append(self._match("LBRACKET"))
                node.children.append(self._parse_expression())
                node.children.append(self._match("RBRACKET"))
            elif nxt == "LPAREN":
                self._record_derivation("factor'",
                                        ["LPAREN", "args", "RPAREN"])
                node.children.append(self._match("LPAREN"))
                node.children.append(self._parse_args())
                node.children.append(self._match("RPAREN"))
            # else: ε
        elif t in {"INTEGER", "FLOAT"}:
            self._record_derivation("factor", [t])
            node.children.append(self._match(t))
        else:
            self._errors.append(f"语法错误：factor 无法以 '{t}' 开头")
            self._panic_skip()
        return node

    # ── call ──
    def _parse_call(self) -> ASTNode:
        node = ASTNode("call")
        self._record_derivation("call", ["ID", "LPAREN", "args", "RPAREN"])
        node.children.append(self._match("ID"))
        node.children.append(self._match("LPAREN"))
        node.children.append(self._parse_args())
        node.children.append(self._match("RPAREN"))
        return node

    # ── args / arg-list ──
    def _parse_args(self) -> ASTNode:
        node = ASTNode("args")
        t = self._peek_type()
        if t in self.first_sets.get("expression", set()):
            self._record_derivation("args", ["arg-list"])
            node.children.append(self._parse_arg_list())
        # else: ε
        return node

    def _parse_arg_list(self) -> ASTNode:
        node = ASTNode("arg-list")
        self._record_derivation("arg-list", ["expression", "arg-list'"])
        node.children.append(self._parse_expression())
        while self._peek_type() == "COMMA":
            self._match("COMMA")
            node.children.append(self._parse_expression())
        return node

    # ── 叶子级非终结符 ──
    def _parse_relop(self) -> ASTNode:
        t = self._peek_type()
        self._record_derivation("relop", [t])
        return self._match(t)

    def _parse_addop(self) -> ASTNode:
        t = self._peek_type()
        self._record_derivation("addop", [t])
        return self._match(t)

    def _parse_mulop(self) -> ASTNode:
        t = self._peek_type()
        self._record_derivation("mulop", [t])
        return self._match(t)
