# backend/app/compiler/lexer.py
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

# ---------- Token 定义 ----------
@dataclass
class Token:
    type: str
    value: str
    line: int
    column: int

# 关键字映射：将 ID 的值转换为对应的关键字类型
KEYWORDS = {
    'int': 'INT',
    'float': 'FLOAT',
    'void': 'VOID',
    'if': 'IF',
    'else': 'ELSE',
    'while': 'WHILE',
    'for': 'FOR',
    'return': 'RETURN',
}

# 模式列表：(token类型, 正则表达式, 是否跳过)
# 顺序很重要：越具体的模式应放在越前面（例如 <= 先于 <，浮点数先于整数）
PATTERNS: List[Tuple[str, str, bool]] = [
    # 跳过类
    ('WHITESPACE', r'\s+', True),
    ('COMMENT', r'//[^\n]*|/\*.*?\*/', True),   # 单行或多行注释

    # 双字符运算符（必须在单字符之前）
    ('LE', r'<=', False),
    ('GE', r'>=', False),
    ('EQ', r'==', False),
    ('NE', r'!=', False),

    # 浮点数（必须在整数之前）
    ('FLOAT', r'\d+\.\d+', False),

    # 单字符运算符/界符
    ('ASSIGN', r'=', False),
    ('LT', r'<', False),
    ('GT', r'>', False),
    ('PLUS', r'\+', False),
    ('MINUS', r'-', False),
    ('STAR', r'\*', False),
    ('DIV', r'/', False),
    ('SEMICOLON', r';', False),
    ('COMMA', r',', False),
    ('LPAREN', r'\(', False),
    ('RPAREN', r'\)', False),
    ('LBRACKET', r'\[', False),
    ('RBRACKET', r'\]', False),
    ('LBRACE', r'\{', False),
    ('RBRACE', r'\}', False),

    # 整数和标识符
    ('INTEGER', r'\d+', False),
    ('ID', r'[a-zA-Z_][a-zA-Z0-9_]*', False),

    # 非法字符（必须最后）
    ('ILLEGAL', r'.', False),
]

# 预编译正则（合并所有模式，使用命名分组）
# 为了效率，我们分别编译每个模式，然后在循环中逐模式尝试匹配，这样更容易控制顺序
# 但更好的方式：按顺序尝试匹配第一个成功的模式
def tokenize(code: str) -> List[Token]:
    """
    对输入的源代码字符串进行词法分析，返回 Token 列表。
    行号从 1 开始，列号从 1 开始。
    """
    tokens: List[Token] = []
    pos = 0
    line = 1
    column = 1
    n = len(code)

    while pos < n:
        # 记录当前起始位置的行列（用于错误 Token）
        start_line = line
        start_col = column
        matched = False

        for token_type, pattern, skip in PATTERNS:
            regex = re.compile(pattern)
            m = regex.match(code, pos)
            if m:
                matched = True
                text = m.group(0)
                new_pos = m.end()

                # 更新行列位置（用于下一个 Token）
                # 先计算当前匹配文本中的换行符数量及末尾列
                lines_in_text = text.count('\n')
                if lines_in_text > 0:
                    # 匹配文本跨多行：新行号增加，新列号 = 最后一个换行符后的字符数 + 1
                    last_line_part = text.split('\n')[-1]
                    new_line = line + lines_in_text
                    new_col = len(last_line_part) + 1
                else:
                    # 单行：列号增加文本长度
                    new_line = line
                    new_col = column + len(text)

                # 如果不是跳过类型，则添加 Token
                if not skip:
                    # 对于 ID 类型，判断是否为关键字
                    if token_type == 'ID' and text in KEYWORDS:
                        token_type = KEYWORDS[text]
                    tokens.append(Token(
                        type=token_type,
                        value=text,
                        line=start_line,
                        column=start_col
                    ))

                # 更新全局位置和行列
                pos = new_pos
                line = new_line
                column = new_col
                break   # 匹配到第一个模式后退出循环

        if not matched:
            # 理论上不应该走到这里，因为最后的 ILLEGAL 会匹配任意字符
            # 但为了安全，处理未匹配情况（例如空字符串）
            pos += 1
            column += 1

    return tokens