# -*- coding: utf-8 -*-
"""
semantic.py — 语义分析器
遍历 AST，构建作用域符号表，检测「变量重定义」和「未声明引用」两类语义错误。
"""

from typing import List, Dict, Any, Optional


class SymbolEntry:
    """符号表条目"""
    def __init__(self, name: str, sym_type: str, kind: str, scope: str, line: int = -1):
        self.name = name          # 变量名 / 函数名
        self.sym_type = sym_type  # 数据类型: int / float / void / func
        self.kind = kind          # 类别: Variable / Parameter / Function
        self.scope = scope        # 作用域名 (如 Global, func_main, block_1)
        self.line = line


class SemanticAnalyzer:
    """基于 AST 节点树的语义分析器"""

    def __init__(self):
        self.symbol_table: List[SymbolEntry] = []
        self.errors: List[str] = []
        # 作用域栈: 每个元素是一个 dict {name: SymbolEntry}
        self._scope_stack: List[Dict[str, SymbolEntry]] = []
        self._scope_counter = 0  # 用于生成唯一作用域名

    # ────────── 作用域管理 ──────────
    def _push_scope(self, scope_name: str = None):
        if scope_name is None:
            scope_name = f"block_{self._scope_counter}"
            self._scope_counter += 1
        self._scope_stack.append({})
        # 记录当前作用域名（在栈顶 dict 中加一个特殊键）
        self._scope_stack[-1]["__scope_name__"] = SymbolEntry("", "", "", scope_name)
        return scope_name

    def _pop_scope(self):
        if self._scope_stack:
            self._scope_stack.pop()

    def _current_scope_name(self) -> str:
        for scope in reversed(self._scope_stack):
            if "__scope_name__" in scope:
                return scope["__scope_name__"].scope
        return "Global"

    def _declare(self, name: str, sym_type: str, kind: str, line: int = -1) -> Optional[SymbolEntry]:
        """在当前作用域声明符号；若已存在则记录重定义错误"""
        if not self._scope_stack:
            self._push_scope("Global")
        current = self._scope_stack[-1]
        scope_name = self._current_scope_name()
        if name in current:
            existing = current[name]
            self.errors.append(
                f"变量重定义: '{name}' 在作用域 '{scope_name}' 中已声明为 {existing.kind}"
            )
            return None
        entry = SymbolEntry(name, sym_type, kind, scope_name, line)
        current[name] = entry
        self.symbol_table.append(entry)
        return entry

    def _lookup(self, name: str) -> Optional[SymbolEntry]:
        """从内到外查找符号"""
        for scope in reversed(self._scope_stack):
            if name in scope:
                return scope[name]
        return None

    # ────────── AST 遍历入口 ──────────
    def analyze(self, ast_node) -> Dict[str, Any]:
        """
        接收 ASTNode 根节点，遍历整棵树，返回符号表和语义错误。
        """
        self.symbol_table.clear()
        self.errors.clear()
        self._scope_stack.clear()
        self._scope_counter = 0
        self._push_scope("Global")

        self._walk(ast_node)

        return {
            "symbol_table": [
                {"name": e.name, "type": e.sym_type, "kind": e.kind, "scope": e.scope}
                for e in self.symbol_table
            ],
            "semantic_errors": list(self.errors),
        }

    # ────────── 递归遍历 AST 节点 ──────────
    def _walk(self, node):
        """根据节点名分发到对应处理方法"""
        if node is None:
            return
        name = node.name if hasattr(node, 'name') else str(node)

        method = getattr(self, f'_visit_{name.replace("-", "_").replace(chr(39), "p")}', None)
        if method:
            method(node)
        else:
            # 默认：遍历所有子节点
            for child in getattr(node, 'children', []):
                self._walk(child)

    # ────────── 各类节点访问方法 ──────────

    def _visit_program(self, node):
        for child in node.children:
            self._walk(child)

    def _visit_declaration(self, node):
        for child in node.children:
            self._walk(child)

    def _visit_declaration_list(self, node):
        for child in node.children:
            self._walk(child)

    # ── 函数声明 ──
    def _visit_fun_declaration(self, node):
        # 子节点顺序: type-specifier, ID[name], LPAREN, params, RPAREN, compound-stmt
        children = node.children
        func_type = self._extract_type(children[0]) if len(children) > 0 else "int"
        func_name = ""
        for ch in children:
            if hasattr(ch, 'name') and ch.name == "ID" and ch.value:
                func_name = ch.value
                break

        if func_name:
            self._declare(func_name, func_type, "Function")
            self._push_scope(f"func_{func_name}")

        # 遍历函数体：params 和 compound-stmt
        for child in children:
            self._walk(child)

        if func_name:
            self._pop_scope()

    # ── 变量声明 ──
    def _visit_var_declaration(self, node):
        # 子节点: type-specifier, init-declarator-list, SEMICOLON
        var_type = "int"
        for child in node.children:
            if child.name == "type-specifier":
                var_type = self._extract_type(child)
                break

        for child in node.children:
            if child.name == "init-declarator-list":
                self._extract_init_declarators(child, var_type)
            elif child.name == "init-declarator":
                self._extract_single_declarator(child, var_type)

    def _extract_type(self, type_node) -> str:
        """从 type-specifier 节点提取类型字符串"""
        for child in type_node.children:
            if hasattr(child, 'name'):
                return child.name.lower()  # INT → int, FLOAT → float, VOID → void
        return "int"

    def _extract_init_declarators(self, node, var_type: str):
        """从 init-declarator-list 中提取所有变量名并声明"""
        for child in node.children:
            if child.name == "init-declarator":
                self._extract_single_declarator(child, var_type)
            elif child.name == "init-declarator-list":
                self._extract_init_declarators(child, var_type)

    def _extract_single_declarator(self, node, var_type: str):
        """提取单个 init-declarator 中的变量名"""
        for child in node.children:
            if hasattr(child, 'name') and child.name == "ID" and child.value:
                self._declare(child.value, var_type, "Variable")

    # ── 参数列表 ──
    def _visit_param(self, node):
        # 子节点: type-specifier, ID[name], (LBRACKET, RBRACKET)
        var_type = "int"
        var_name = ""
        for child in node.children:
            if child.name == "type-specifier":
                var_type = self._extract_type(child)
            elif hasattr(child, 'name') and child.name == "ID" and child.value:
                var_name = child.value

        if var_name:
            is_array = any(
                hasattr(ch, 'name') and ch.name == "LBRACKET" for ch in node.children
            )
            self._declare(var_name, f"{var_type}{'[]' if is_array else ''}", "Parameter")

    # ── 复合语句（代码块） ──
    def _visit_compound_stmt(self, node):
        self._push_scope()
        for child in node.children:
            self._walk(child)
        self._pop_scope()

    # ── for 初始化 ──
    def _visit_for_init_stmt(self, node):
        """处理 for-init-stmt：声明路径需提取变量，表达式路径正常遍历"""
        children = node.children
        if not children:
            return  # ε
        # 判断是 type-specifier 路径还是 expression 路径
        first = children[0]
        if hasattr(first, 'name') and first.name == "type-specifier":
            # 声明路径：type-specifier init-declarator-list
            var_type = self._extract_type(first)
            for child in children:
                if hasattr(child, 'name') and child.name == "init-declarator-list":
                    self._extract_init_declarators(child, var_type)
                elif hasattr(child, 'name') and child.name == "init-declarator":
                    self._extract_single_declarator(child, var_type)
        else:
            # 表达式路径（或 ε）：正常遍历
            for child in children:
                self._walk(child)

    # ── 迭代语句（while / for） ──
    def _visit_iteration_stmt(self, node):
        """处理 while/for：for 循环需额外管理 init 作用域"""
        children = node.children
        is_for = any(hasattr(ch, 'name') and ch.name == "FOR" for ch in children)

        if is_for:
            # for 循环：init 声明的作用域覆盖整个 for 头部和体
            self._push_scope()
            for child in children:
                self._walk(child)
            self._pop_scope()
        else:
            # while 循环：正常遍历
            for child in children:
                self._walk(child)

    # ── ID 使用检查（在表达式中） ──
    def _check_id_usage(self, node):
        """检查 ID 节点是否已声明，只对表达式上下文中的 ID 调用"""
        if hasattr(node, 'name') and node.name == "ID" and node.value:
            name = node.value
            keywords = {"int", "float", "void", "if", "else", "while", "for", "return"}
            if name in keywords:
                return
            entry = self._lookup(name)
            if entry is None:
                self.errors.append(f"未声明引用: 变量 '{name}' 在使用前未声明")

    # ── 表达式相关节点：统一走 _check_ids_in_subtree ──
    def _visit_expression(self, node):
        self._check_ids_in_subtree(node)

    def _visit_factor(self, node):
        self._check_ids_in_subtree(node)

    def _visit_call(self, node):
        for child in node.children:
            self._walk(child)

    def _visit_var(self, node):
        self._check_ids_in_subtree(node)

    def _visit_simple_expression(self, node):
        self._check_ids_in_subtree(node)

    def _visit_additive_expression(self, node):
        self._check_ids_in_subtree(node)

    def _visit_term(self, node):
        self._check_ids_in_subtree(node)

    def _visit_return_stmt(self, node):
        self._check_ids_in_subtree(node)

    def _visit_expression_stmt(self, node):
        self._check_ids_in_subtree(node)

    def _visit_selection_stmt(self, node):
        self._check_ids_in_subtree(node)

    def _visit_arg_list(self, node):
        self._check_ids_in_subtree(node)

    def _check_ids_in_subtree(self, node):
        """递归检查子树中所有 ID 节点是否已声明（排除声明上下文）"""
        if node is None:
            return
        declaration_contexts = {
            "var-declaration", "fun-declaration", "param", "init-declarator",
            "init-declarator-list", "type-specifier", "params", "param-list",
            "for-init-stmt",
        }
        if hasattr(node, 'name') and node.name in declaration_contexts:
            for child in getattr(node, 'children', []):
                self._walk(child)
            return

        if hasattr(node, 'name') and node.name == "ID" and node.value:
            self._check_id_usage(node)

        for child in getattr(node, 'children', []):
            self._check_ids_in_subtree(child)
