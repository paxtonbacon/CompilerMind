# -*- coding: utf-8 -*-
"""
pcode.py — P-Code 中间代码生成器
遍历 AST，生成三地址码风格的中间表示。
"""

from typing import List, Optional


class PCodeGenerator:
    """基于 AST 节点树的 P-Code 生成器"""

    def __init__(self):
        self.code: List[str] = []
        self._temp_counter = 0
        self._label_counter = 0

    def _new_temp(self) -> str:
        self._temp_counter += 1
        return f"t{self._temp_counter}"

    def _new_label(self) -> str:
        self._label_counter += 1
        return f"L{self._label_counter}"

    def _emit(self, instr: str):
        self.code.append(instr)

    # ────────── 入口 ──────────
    def generate(self, ast_node) -> List[str]:
        """返回 P-Code 指令列表"""
        self.code.clear()
        self._temp_counter = 0
        self._label_counter = 0
        self._walk(ast_node)
        return list(self.code)

    # ────────── 递归遍历 ──────────
    def _walk(self, node):
        if node is None:
            return None
        name = node.name if hasattr(node, 'name') else str(node)
        method = getattr(self, f'_visit_{name.replace("-", "_").replace(chr(39), "p")}', None)
        if method:
            return method(node)
        else:
            results = []
            for child in getattr(node, 'children', []):
                r = self._walk(child)
                if r is not None:
                    results.append(r)
            return results[-1] if results else None

    # ────────── 顶层 ──────────
    def _visit_program(self, node):
        self._emit("; === P-Code 中间代码 ===")
        for child in node.children:
            self._walk(child)
        self._emit("; === 结束 ===")

    # ────────── 函数声明 ──────────
    def _visit_fun_declaration(self, node):
        # 提取函数名
        func_name = "main"
        for ch in node.children:
            if hasattr(ch, 'name') and ch.name == "ID" and ch.value:
                func_name = ch.value
                break
        self._emit(f"\n; --- 函数: {func_name} ---")
        self._emit(f"FUNC_BEGIN {func_name}")
        for child in node.children:
            self._walk(child)
        self._emit(f"FUNC_END {func_name}")

    # ────────── 变量声明 ──────────
    def _visit_var_declaration(self, node):
        var_type = "int"
        for child in node.children:
            if child.name == "type-specifier":
                for tc in child.children:
                    if hasattr(tc, 'name'):
                        var_type = tc.name.lower()
                        break

        # 提取变量名
        names = []
        self._collect_var_names(node, names)

        for name in names:
            self._emit(f"DECL {name}, {var_type}")

        # 处理初始化赋值
        self._handle_init(node, names)

    def _collect_var_names(self, node, names: list):
        for child in getattr(node, 'children', []):
            if hasattr(child, 'name') and child.name == "ID" and child.value:
                names.append(child.value)
            elif child.name in ("init-declarator-list", "init-declarator-list'",
                                "init-declarator"):
                self._collect_var_names(child, names)

    def _handle_init(self, node, names: list):
        """处理变量初始化赋值：int x = expr → x = expr"""
        name_idx = 0
        self._handle_init_recursive(node, names, [0])

    def _handle_init_recursive(self, node, names: list, idx_ref: list):
        for child in getattr(node, 'children', []):
            if child.name == "ASSIGN":
                # 下一个兄弟是 expression
                if idx_ref[0] < len(names):
                    result = None
                    # 找 expression 子节点
                    siblings = getattr(node, 'children', [])
                    for i, sib in enumerate(siblings):
                        if sib is child and i + 1 < len(siblings):
                            result = self._walk(siblings[i + 1])
                            break
                    if result:
                        self._emit(f"ASSIGN {names[idx_ref[0]]}, {result}")
                    idx_ref[0] += 1
            elif hasattr(child, 'children'):
                self._handle_init_recursive(child, names, idx_ref)

    # ────────── 复合语句 ──────────
    def _visit_compound_stmt(self, node):
        self._emit("BEGIN_BLOCK")
        for child in node.children:
            self._walk(child)
        self._emit("END_BLOCK")

    # ────────── 选择语句 (if / if-else) ──────────
    def _visit_selection_stmt(self, node):
        # IF, LPAREN, expression, RPAREN, statement, [ELSE, statement]
        children = node.children
        cond_result = None
        stmt_start = 0

        for i, ch in enumerate(children):
            if ch.name == "expression":
                cond_result = self._walk(ch)
            elif ch.name == "LPAREN":
                stmt_start = i + 1

        label_else = self._new_label()
        label_end = self._new_label()

        if cond_result:
            self._emit(f"IF_FALSE {cond_result}, GOTO {label_else}")

        # then 分支
        # 找到 RPAREN 之后的 statement
        rparen_idx = -1
        for i, ch in enumerate(children):
            if hasattr(ch, 'name') and ch.name == "RPAREN":
                rparen_idx = i
                break
        if rparen_idx >= 0 and rparen_idx + 1 < len(children):
            self._walk(children[rparen_idx + 1])

        # 检查是否有 else
        has_else = any(hasattr(ch, 'name') and ch.name == "ELSE" for ch in children)
        if has_else:
            self._emit(f"GOTO {label_end}")

        self._emit(f"LABEL {label_else}")

        if has_else:
            # else 分支
            else_idx = -1
            for i, ch in enumerate(children):
                if hasattr(ch, 'name') and ch.name == "ELSE":
                    else_idx = i
                    break
            if else_idx >= 0 and else_idx + 1 < len(children):
                self._walk(children[else_idx + 1])
            self._emit(f"LABEL {label_end}")

    # ────────── 迭代语句 (while) ──────────
    def _visit_iteration_stmt(self, node):
        children = node.children
        is_while = any(hasattr(ch, 'name') and ch.name == "WHILE" for ch in children)

        if is_while:
            label_begin = self._new_label()
            label_end = self._new_label()

            self._emit(f"LABEL {label_begin}")

            cond_result = None
            body_start = 0
            for i, ch in enumerate(children):
                if ch.name == "expression" and cond_result is None:
                    cond_result = self._walk(ch)
                elif hasattr(ch, 'name') and ch.name == "RPAREN":
                    body_start = i + 1
                    break

            if cond_result:
                self._emit(f"IF_FALSE {cond_result}, GOTO {label_end}")

            if body_start < len(children):
                self._walk(children[body_start])

            self._emit(f"GOTO {label_begin}")
            self._emit(f"LABEL {label_end}")
        else:
            # for 循环简化处理
            self._emit("; for-loop (simplified)")
            for child in children:
                self._walk(child)

    # ────────── return 语句 ──────────
    def _visit_return_stmt(self, node):
        result = None
        for child in node.children:
            if child.name == "expression":
                result = self._walk(child)
        if result:
            self._emit(f"RETURN {result}")
        else:
            self._emit("RETURN")

    # ────────── expression-stmt ──────────
    def _visit_expression_stmt(self, node):
        for child in node.children:
            self._walk(child)

    # ────────── 表达式 ──────────
    def _visit_expression(self, node):
        children = node.children
        # ID expression'
        # 或 LPAREN expression RPAREN simple-expression-tail
        # 或 INTEGER/FLOAT simple-expression-tail

        if len(children) >= 2 and hasattr(children[0], 'value') and children[0].value:
            # ID path
            id_name = children[0].value
            if len(children) >= 2 and children[1].name == "expression'":
                return self._visit_expression_prime(id_name, children[1])
            return id_name
        elif len(children) >= 1 and children[0].name in ("INTEGER", "FLOAT"):
            lit_val = children[0].value
            if len(children) >= 2:
                tail = self._walk(children[-1])  # simple-expression-tail
                if tail:
                    return f"{lit_val} {tail}"
            return lit_val
        else:
            results = [self._walk(ch) for ch in children]
            results = [r for r in results if r is not None]
            return results[-1] if results else None

    def _visit_expression_prime(self, id_name, node):
        """处理 expression' 的各种分支"""
        children = node.children
        if not children:
            return id_name

        first = children[0]
        if hasattr(first, 'name') and first.name == "ASSIGN":
            rhs = None
            for ch in children[1:]:
                r = self._walk(ch)
                if r:
                    rhs = r
            if rhs:
                self._emit(f"ASSIGN {id_name}, {rhs}")
            return id_name
        elif hasattr(first, 'name') and first.name == "LBRACKET":
            # 数组访问：ID[expr] = expr 或 ID[expr]
            idx_result = None
            for ch in children:
                if ch.name == "expression":
                    idx_result = self._walk(ch)
                    break
            arr_temp = f"{id_name}[{idx_result}]" if idx_result else f"{id_name}[?]"

            # 检查是否有赋值
            for ch in children:
                if hasattr(ch, 'name') and ch.name == "expression-bracket-tail":
                    for gc in ch.children:
                        if hasattr(gc, 'name') and gc.name == "ASSIGN":
                            rhs = None
                            for gcc in ch.children[1:]:
                                r = self._walk(gcc)
                                if r:
                                    rhs = r
                            if rhs:
                                self._emit(f"ASSIGN {arr_temp}, {rhs}")
                            return arr_temp
            return arr_temp
        elif hasattr(first, 'name') and first.name == "LPAREN":
            # 函数调用
            args = []
            for ch in children:
                if ch.name == "args":
                    self._collect_args(ch, args)
            arg_str = ", ".join(args)
            self._emit(f"CALL {id_name}({arg_str})")
            return f"CALL_{id_name}"
        else:
            # simple-expression-tail
            tail = self._visit_simple_expression_tail(node)
            if tail:
                return f"{id_name} {tail}"
            return id_name

    def _visit_expression_bracket_tail(self, node):
        return self._visit_simple_expression_tail(node)

    def _visit_simple_expression_tail(self, node):
        """处理二元运算符链"""
        parts = []
        for child in node.children:
            if child.name == "term'":
                r = self._walk(child)
                if r:
                    parts.append(r)
            elif child.name == "additive-expression'":
                r = self._walk(child)
                if r:
                    parts.append(r)
            elif child.name == "simple-expression'":
                r = self._walk(child)
                if r:
                    parts.append(r)
        return " ".join(parts) if parts else None

    def _collect_args(self, node, args: list):
        for child in getattr(node, 'children', []):
            if child.name == "expression":
                r = self._walk(child)
                if r:
                    args.append(r)
            elif hasattr(child, 'children'):
                self._collect_args(child, args)

    # ────────── 算术表达式 ──────────
    def _visit_additive_expression(self, node):
        return self._process_binary_chain(node, {"PLUS": "ADD", "MINUS": "SUB"})

    def _visit_term(self, node):
        return self._process_binary_chain(node, {"STAR": "MUL", "DIV": "DIV"})

    def _visit_additive_expressionp(self, node):
        return self._process_binary_chain(node, {"PLUS": "ADD", "MINUS": "SUB"})

    def _visit_termp(self, node):
        return self._process_binary_chain(node, {"STAR": "MUL", "DIV": "DIV"})

    def _visit_simple_expressionp(self, node):
        return self._process_binary_chain(node, {"LE": "LE", "LT": "LT", "GT": "GT",
                                                  "GE": "GE", "EQ": "EQ", "NE": "NE"})

    def _process_binary_chain(self, node, op_map: dict) -> Optional[str]:
        """处理二元运算符链，生成临时变量和三地址码"""
        children = node.children
        if not children:
            return None

        # 找左操作数
        left = None
        for ch in children:
            if ch.name in ("factor", "term", "additive-expression"):
                left = self._walk(ch)
                break
            elif hasattr(ch, 'value') and ch.value:
                left = ch.value
                break
            elif ch.name in ("ID", "INTEGER", "FLOAT"):
                left = ch.value
                break

        if left is None:
            return None

        # 处理后续的 op factor/term 对
        i = 0
        while i < len(children):
            ch = children[i]
            op_name = None
            if hasattr(ch, 'name') and ch.name in op_map:
                continue  # 会在下面统一处理
            elif hasattr(ch, 'value') and ch.value in op_map:
                op_name = ch.value
            elif hasattr(ch, 'name') and ch.name == "addop":
                op_name = self._extract_op(ch)
            elif hasattr(ch, 'name') and ch.name == "mulop":
                op_name = self._extract_op(ch)
            elif hasattr(ch, 'name') and ch.name == "relop":
                op_name = self._extract_op(ch)

            if op_name and i + 1 < len(children):
                right = self._walk(children[i + 1])
                if right:
                    instr = op_map.get(op_name, op_name)
                    temp = self._new_temp()
                    self._emit(f"{instr} {temp}, {left}, {right}")
                    left = temp
                i += 2
            else:
                r = self._walk(ch)
                if r:
                    left = r
                i += 1

        return left

    def _extract_op(self, node) -> Optional[str]:
        for child in getattr(node, 'children', []):
            if hasattr(child, 'value') and child.value:
                return child.value
            elif hasattr(child, 'name') and child.name != "addop" and child.name != "mulop" and child.name != "relop":
                return child.name
        return None

    # ────────── factor ──────────
    def _visit_factor(self, node):
        children = node.children
        for ch in children:
            if hasattr(ch, 'name') and ch.name in ("INTEGER", "FLOAT") and ch.value:
                return ch.value
            elif hasattr(ch, 'name') and ch.name == "ID" and ch.value:
                # ID factor'
                id_name = ch.value
                if len(children) >= 2 and children[-1].name == "factor'":
                    factor_prime = children[-1]
                    fp_children = factor_prime.children
                    if fp_children and hasattr(fp_children[0], 'name') and fp_children[0].name == "LBRACKET":
                        # 数组访问
                        idx = None
                        for fc in fp_children:
                            if fc.name == "expression":
                                idx = self._walk(fc)
                        return f"{id_name}[{idx}]" if idx else f"{id_name}[?]"
                    elif fp_children and hasattr(fp_children[0], 'name') and fp_children[0].name == "LPAREN":
                        # 函数调用
                        args = []
                        for fc in fp_children:
                            if fc.name == "args":
                                self._collect_args(fc, args)
                        self._emit(f"CALL {id_name}({', '.join(args)})")
                        return f"CALL_{id_name}"
                return id_name
            elif hasattr(ch, 'name') and ch.name == "LPAREN":
                # ( expression )
                for cc in children:
                    if cc.name == "expression":
                        return self._walk(cc)
        return None
