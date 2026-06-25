import json

# 语法符号 → 词法分析器 Token 类型映射
# 文法中使用人类可读的符号，但词法分析器输出标准化的 Token 类型名
_TOKEN_TYPE_MAP = {
    # 关键字：小写 → 大写
    'int': 'INT', 'float': 'FLOAT', 'void': 'VOID',
    'if': 'IF', 'else': 'ELSE', 'while': 'WHILE', 'for': 'FOR', 'return': 'RETURN',
    # 运算符
    '+': 'PLUS', '-': 'MINUS', '*': 'STAR', '/': 'DIV',
    '=': 'ASSIGN',
    '<': 'LT', '>': 'GT', '<=': 'LE', '>=': 'GE', '==': 'EQ', '!=': 'NE',
    # 界符
    ';': 'SEMICOLON', ',': 'COMMA',
    '(': 'LPAREN', ')': 'RPAREN',
    '{': 'LBRACE', '}': 'RBRACE',
    '[': 'LBRACKET', ']': 'RBRACKET',
}

def _map_token(symbol: str) -> str:
    """将文法中的人类可读符号映射为词法分析器的 Token 类型"""
    return _TOKEN_TYPE_MAP.get(symbol, symbol)


class ASTNode:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value
        self.children = []

    def to_dict(self):
        """转换为可序列化的字典，供前端D3.js或Echarts渲染AST"""
        return {
            "name": f"{self.name} ({self.value})" if self.value else self.name,
            "children": [child.to_dict() for child in self.children]
        }

    def to_text_tree(self, prefix="", is_last=True):
        """生成树状文本结构"""
        result = prefix + ("└── " if is_last else "├── ") + (f"{self.name}[{self.value}]" if self.value else self.name) + "\n"
        prefix += "    " if is_last else "│   "
        child_count = len(self.children)
        for i, child in enumerate(self.children):
            result += child.to_text_tree(prefix, i == child_count - 1)
        return result


class LRParserEngine:
    def __init__(self, grammar_str, start_symbol="program"):
        self.grammar_str = grammar_str
        self.start_symbol = start_symbol
        self.productions = []  # 存储元组: (LHS, [RHS_list])
        self.terminals = set()
        self.non_terminals = set()
        self.first = {}
        self.follow = {}
        self.states = []       # 项目集规范族 [set(Item)]
        self.lr_table = {}     # {state_id: {symbol: action_str}}
        self.conflicts = []    # 冲突记录
        
        self._parse_grammar()
        self._compute_first_follow()
        self._build_item_sets()
        self._build_lr_table()

    def _parse_grammar(self):
        """解析增广文法，支持多行 | 候选式，并映射 Token 类型"""
        # 自动添加增广文法起始规则
        self.productions.append((f"{self.start_symbol}'", [self.start_symbol]))
        self.non_terminals.add(f"{self.start_symbol}'")

        lines = self.grammar_str.strip().split('\n')
        current_lhs = None  # 当前正在解析的左部非终结符

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if '→' in line:
                # 新产生式行
                lhs, rhs_part = line.split('→', 1)
                current_lhs = lhs.strip()
                self.non_terminals.add(current_lhs)
                # 处理该行的第一个候选式
                self._add_production_alternatives(current_lhs, rhs_part.strip())
            elif line.startswith('|') and current_lhs is not None:
                # 续行：多行 | 候选式
                self._add_production_alternatives(current_lhs, line[1:].strip())

        # 从终结符集合中移除非终结符和空串，添加结束符
        self.terminals = self.terminals - self.non_terminals
        self.terminals.discard('empty')
        self.terminals.add('$')

    def _add_production_alternatives(self, lhs: str, rhs_part: str):
        """解析右部的 | 分隔候选式，应用 Token 映射，添加到产生式列表"""
        for alternative in rhs_part.split('|'):
            rhs_tokens_raw = [t.strip() for t in alternative.strip().split() if t.strip()]
            if not rhs_tokens_raw:
                rhs_tokens = ['empty']
            else:
                # 应用 Token 类型映射
                rhs_tokens = [_map_token(t) for t in rhs_tokens_raw]
            self.productions.append((lhs, rhs_tokens))
            for t in rhs_tokens:
                if t != 'empty':
                    self.terminals.add(t)

    def _compute_first_follow(self):
        """计算 First 和 Follow 集 (SLR(1) 必需)"""
        for nt in self.non_terminals:
            self.first[nt] = set()
            self.follow[nt] = set()
        for t in self.terminals:
            self.first[t] = {t}
        self.first['empty'] = {'empty'}
        self.follow[f"{self.start_symbol}'"].add('$')

        # 迭代计算 First
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.productions[1:]:
                before_len = len(self.first[lhs])
                if rhs[0] == 'empty':
                    self.first[lhs].add('empty')
                else:
                    for sym in rhs:
                        self.first[lhs].update(self.first[sym] - {'empty'})
                        if 'empty' not in self.first[sym]:
                            break
                    else:
                        self.first[lhs].add('empty')
                if len(self.first[lhs]) != before_len:
                    changed = True

        # 迭代计算 Follow
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.productions:
                if rhs == ['empty']:
                    continue
                for i, B in enumerate(rhs):
                    if B in self.non_terminals:
                        before_len = len(self.follow[B])
                        # 找到 B 之后的符号串的 First 集
                        tail = rhs[i+1:]
                        if not tail:
                            self.follow[B].update(self.follow[lhs])
                        else:
                            first_tail = set()
                            for sym in tail:
                                first_tail.update(self.first[sym] - {'empty'})
                                if 'empty' not in self.first[sym]:
                                    break
                            else:
                                first_tail.add('empty')
                            
                            self.follow[B].update(first_tail - {'empty'})
                            if 'empty' in first_tail:
                                self.follow[B].update(self.follow[lhs])
                        if len(self.follow[B]) != before_len:
                            changed = True

    def _closure(self, item_set):
        """求项目集闭包"""
        closure_set = set(item_set)
        changed = True
        while changed:
            changed = False
            current_items = list(closure_set)
            for prod_idx, dot_pos in current_items:
                lhs, rhs = self.productions[prod_idx]
                if dot_pos < len(rhs) and rhs[dot_pos] in self.non_terminals:
                    B = rhs[dot_pos]
                    for p_idx, (p_lhs, p_rhs) in enumerate(self.productions):
                        if p_lhs == B:
                            new_item = (p_idx, 0)
                            if new_item not in closure_set:
                                closure_set.add(new_item)
                                changed = True
        return closure_set

    def _goto(self, item_set, symbol):
        """转换函数"""
        move_set = set()
        for prod_idx, dot_pos in item_set:
            lhs, rhs = self.productions[prod_idx]
            if dot_pos < len(rhs) and rhs[dot_pos] == symbol:
                move_set.add((prod_idx, dot_pos + 1))
        return self._closure(move_set)

    def _build_item_sets(self):
        """构建项目集规范族"""
        initial_set = self._closure({(0, 0)})  # Start' -> .Start
        self.states.append(initial_set)
        
        changed = True
        while changed:
            changed = False
            for state in list(self.states):
                all_symbols = self.terminals | self.non_terminals
                for sym in all_symbols:
                    if sym == '$' or sym == 'empty':
                        continue
                    next_set = self._goto(state, sym)
                    if next_set and next_set not in self.states:
                        self.states.append(next_set)
                        changed = True

    def _build_lr_table(self):
        """构建分析表并捕获冲突"""
        for i in range(len(self.states)):
            self.lr_table[i] = {}

        for i, state in enumerate(self.states):
            for prod_idx, dot_pos in state:
                lhs, rhs = self.productions[prod_idx]
                
                # 情况 A：点在最后，进行规约
                if dot_pos == len(rhs) or rhs == ['empty']:
                    if lhs == f"{self.start_symbol}'":
                        self._add_action(i, '$', "acc")
                    else:
                        # SLR(1) 根据 Follow 集放置 Reduce
                        for sym in self.follow[lhs]:
                            self._add_action(i, sym, f"r{prod_idx}")
                else:
                    # 情况 B：点不在最后，移进或状态转换
                    next_sym = rhs[dot_pos]
                    next_state_idx = self.states.index(self._goto(state, next_sym))
                    if next_sym in self.terminals:
                        self._add_action(i, next_sym, f"s{next_state_idx}")
                    elif next_sym in self.non_terminals:
                        self._add_action(i, next_sym, f"{next_state_idx}")

    def _add_action(self, state, symbol, action):
        """安全地添加动作，检测 Shift-Reduce / Reduce-Reduce 冲突"""
        if symbol in self.lr_table[state]:
            existing = self.lr_table[state][symbol]
            if existing != action:
                conflict_msg = f"Conflict in State {state} on '{symbol}': {existing} vs {action}"
                if conflict_msg not in self.conflicts:
                    self.conflicts.append(conflict_msg)
        else:
            self.lr_table[state][symbol] = action

    def get_serialized_states(self):
        """序列化状态集供前端显示，返回 Dict[int, List[str]]"""
        res = {}
        for i, state in enumerate(self.states):
            items_list = []
            for prod_idx, dot_pos in state:
                lhs, rhs = self.productions[prod_idx]
                rhs_copy = list(rhs)
                if rhs_copy == ['empty']:
                    rhs_copy = []
                rhs_copy.insert(dot_pos, '.')
                items_list.append(f"{lhs} → {' '.join(rhs_copy)}")
            res[i] = items_list
        return res

    def get_flat_table(self):
        """平坦化表格结构供前端呈现网格矩阵，返回 List[Dict[str, Any]]"""
        flat = []
        for state, actions in self.lr_table.items():
            row = {"state": state}
            row.update(actions)
            flat.append(row)
        return flat

    def parse(self, tokens):
        """对输入的Token序列执行最左规约(逆向最右导出)，构建AST"""
        # 统一格式：兼容 Token 对象和 (type, value) 元组
        if tokens and hasattr(tokens[0], 'type'):
            tokens = [(t.type, t.value) for t in tokens]
        tokens = tokens + [('$', '$')]  # 补全结束符
        stack = [0]
        symbol_stack = []
        node_stack = []  # 存储中间生成的 AST 节点
        steps = []
        errors = []
        
        step_cnt = 0
        idx = 0
        
        while True:
            state = stack[-1]
            tok_type, tok_val = tokens[idx]
            
            # 读取当前状态对该Token的动作
            action = self.lr_table[state].get(tok_type)
            
            # 构建步骤日志
            step_info = {
                "step": step_cnt,
                "state_stack": str(stack),
                "symbol_stack": " ".join(symbol_stack),
                "remaining_input": " ".join([t[1] for t in tokens[idx:]]),
                "action": action if action else "ERROR"
            }
            steps.append(step_info)
            step_cnt += 1

            if not action:
                errors.append(f"Syntax Error at step {step_cnt}: unexpected token '{tok_val}' in state {state}")
                break
                
            if action == "acc":
                break  # 接收成功
                
            elif action.startswith('s'):
                # 移进 (Shift)
                next_state = int(action[1:])
                stack.append(next_state)
                symbol_stack.append(tok_type)
                # 为终结符创建叶子节点
                node_stack.append(ASTNode(tok_type, tok_val))
                idx += 1
                
            elif action.startswith('r'):
                # 规约 (Reduce) - 最左规约核心
                prod_idx = int(action[1:])
                lhs, rhs = self.productions[prod_idx]
                
                parent_node = ASTNode(lhs)
                
                if rhs != ['empty']:
                    pop_len = len(rhs)
                    # 弹出状态和符号
                    del stack[-pop_len:]
                    del symbol_stack[-pop_len:]
                    # 弹出子节点连接到父节点
                    children = []
                    for _ in range(pop_len):
                        children.append(node_stack.pop())
                    parent_node.children = list(reversed(children)) # 保持从左到右顺序
                else:
                    # 空产生式生成一个 empty 虚拟叶子节点
                    parent_node.children.append(ASTNode("empty"))

                # 转换 Goto
                top_state = stack[-1]
                goto_state = int(self.lr_table[top_state][lhs])
                stack.append(goto_state)
                symbol_stack.append(lhs)
                node_stack.append(parent_node)

        final_ast = node_stack[0].to_dict() if node_stack else {}
        text_tree = node_stack[0].to_text_tree() if node_stack else ""
        
        return steps, final_ast, text_tree, errors

    def get_frontend_data(self, tokens):
        """统一返回给后端的标准接口字典数据"""
        serialized_states = self.get_serialized_states()
        flat_table = self.get_flat_table()
        steps, final_ast, text_tree, errors = self.parse(tokens)
        
        return {
            "item_sets": serialized_states,
            "lr_table": flat_table,
            "conflicts": self.conflicts,
            "parsing_steps": steps,
            "ast": final_ast,
            "text_tree": text_tree,
            "syntax_errors": errors
        }