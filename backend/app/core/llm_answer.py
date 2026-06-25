# -*- coding: utf-8 -*-
"""
llm_answer.py — 大模型 C-Minus 答案生成 + LL(1) 文法约束校验

核心功能：
1. generate_answer() — 调用 DeepSeek 生成题目答案代码
2. GrammarConstraintValidator — 用 LL(1) 预测分析表对生成的 Token 流做
   FIRST 集合法性校验，标记越界 Token 并给出修正建议。
"""

import asyncio
from typing import List, Dict, Tuple, Optional
from openai import AsyncOpenAI
from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME
from ..compiler.lexer import tokenize
from ..compiler.ll_grammar import GRAMMAR_RULES, TERMINALS, NON_TERMINALS, START_SYMBOL

# 超时配置（秒）
_REQUEST_TIMEOUT = 90  # 单次 API 调用超时
_MAX_RETRIES = 3       # 文法约束模式最多重试次数

client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    timeout=_REQUEST_TIMEOUT,
    max_retries=1,  # SDK 层面最多重试 1 次
)

# ── 系统提示词：强制输出 C-Minus 代码 ──
ANSWER_SYSTEM_PROMPT = """你是一个 C-Minus 语言编程专家。请根据题目要求，输出一段完整可编译的 C-Minus 代码作为参考答案。

C-Minus 文法约束（必须严格遵守）：
- 程序入口必须是 int main(void) { ... } 或 void main(void) { ... }
- 支持数组声明：int a[10];（数组大小必须是 INTEGER 常量）
- 支持 if / if-else / while / for 语句
- for 循环格式：for (表达式; 表达式; 表达式) 语句 或 for (int i=0; ...; ...) 语句
- return 语句：return; 或 return 表达式;
- 运算符：+ - * / < > <= >= == != =
- 函数调用：foo(a, b+3)
- 不支持：++ -- += 等复合赋值、空参数函数声明、变长数组

- C Minus未定义输入输出，所以说不要用输入输出（比如scanf/printf等）
- 结果以main函数的返回给出（return）
- 输入在main函数的函数params中给出

输出要求：
1. 只输出 C-Minus 代码，不要输出任何解释、注释或 markdown 标记
2. 代码必须语法正确，能够通过 C-Minus 编译器解析
3. 不要使用 ``` 代码块包裹
"""

# ═══════════════════════════════════════════════
#  文法约束校验器
# ═══════════════════════════════════════════════
class GrammarConstraintValidator:
    """
    利用已构造的 LL(1) 预测分析表，对 Token 流逐 Token 校验。
    在 LLM 输出后进行后处理：标记越界 Token 并尝试修复。
    """

    def __init__(self):
        # 导入 LL 引擎以复用 FIRST/FOLLOW/预测表
        from ..compiler.ll_parser import LL1CompilerEngine
        self.engine = LL1CompilerEngine()
        self.predict_table = self.engine.predict_table
        self.first_sets = self.engine.first_sets
        self.follow_sets = self.engine.follow_sets
        self.non_terminals = self.engine.non_terminals
        self.terminals = self.engine.terminals

    def validate_and_correct(self, code: str) -> Dict:
        """
        对生成的代码做 Token 级校验，返回：
        {
            "original_code": str,
            "corrected_code": str,
            "is_valid": bool,
            "corrections": [{"line": int, "token": str, "issue": str, "suggestion": str}, ...],
            "validation_log": [str, ...]
        }
        """
        tokens = tokenize(code)
        log: List[str] = []
        corrections: List[Dict] = []

        # 简化校验：用 LL(1) 解析器解析一遍，捕获语法错误
        result = self.engine.parse(tokens)
        syntax_errors = result.get("syntax_errors", [])

        for err in syntax_errors:
            log.append(f"[语法错误] {err}")
            # 尝试提取 Token 信息
            parts = err.split("'")
            if len(parts) >= 3:
                problem_token = parts[3] if len(parts) > 3 else parts[1]
                corrections.append({
                    "token": problem_token,
                    "issue": err,
                    "suggestion": self._suggest_fix(problem_token, tokens)
                })

        # 如果没有语法错误，再做更细粒度的 FIRST 集校验
        if not syntax_errors and tokens:
            first_log = self._validate_first_sets(tokens)
            log.extend(first_log)

        is_valid = len(syntax_errors) == 0 and not any(
            "FIRST 集越界" in l for l in first_log
        ) if not syntax_errors else False

        # 尝试自动修复（简单策略：删除越界 Token）
        corrected = code
        if corrections:
            corrected = self._attempt_auto_fix(code, tokens, syntax_errors)

        return {
            "original_code": code,
            "corrected_code": corrected,
            "is_valid": is_valid,
            "corrections": corrections,
            "validation_log": log,
        }

    def _validate_first_sets(self, tokens) -> List[str]:
        """
        用 LL(1) 分析表逐 Token 做 FIRST 集合法性校验。
        模拟非终结符的展开路径，检查每个终结符是否在对应的 FIRST 集中。
        """
        log: List[str] = []
        # 模拟 LL(1) 解析栈
        token_types = [(t.type, t.value, t.line) for t in tokens] + [("$", "$", -1)]
        stack = [START_SYMBOL]
        idx = 0

        while stack and idx < len(token_types):
            top = stack.pop()
            tok_type, tok_val, tok_line = token_types[idx]

            if top in self.terminals or top == "$":
                if top == tok_type:
                    idx += 1
                else:
                    log.append(
                        f"FIRST 集越界: 期待 '{top}'，遇到 '{tok_type}'"
                        f"({tok_val}) 行 {tok_line}"
                    )
                    idx += 1  # 跳过
            elif top in self.non_terminals:
                prod = self.predict_table.get(top, {}).get(tok_type)
                if prod:
                    # 逆序压栈
                    for sym in reversed(prod):
                        if sym != "ε":
                            stack.append(sym)
                else:
                    # 检查 FOLLOW 集
                    if tok_type in self.follow_sets.get(top, set()):
                        log.append(
                            f"FIRST 集越界: [{top}] 在 '{tok_type}' 处无产生式，"
                            f"但 tok 在 FOLLOW({top}) 中，跳过（行 {tok_line}）"
                        )
                    else:
                        # 真正的越界：该 Token 既不在 FIRST 也不在 FOLLOW
                        valid_set = set(self.predict_table.get(top, {}).keys())
                        log.append(
                            f"FIRST 集越界: [{top}] 无法接收 '{tok_type}'({tok_val}) "
                            f"行 {tok_line}。合法 Token: {sorted(valid_set)[:8]}"
                        )
                        idx += 1  # 跳过错误 Token
        return log

    def _suggest_fix(self, problem_token: str, tokens) -> str:
        """根据越界的上下文给出修正建议"""
        # 简单映射常见错误
        common_fixes = {
            "++": "建议改为 i = i + 1",
            "--": "建议改为 i = i - 1",
            "+=": "建议改为 i = i + 表达式",
            "-=": "建议改为 i = i - 表达式",
        }
        return common_fixes.get(problem_token, f"Token '{problem_token}' 不在 C-Minus 文法中，建议删除或替换")

    def _attempt_auto_fix(self, code: str, tokens, syntax_errors: List[str]) -> str:
        """尝试自动修复：删除明显越界的 Token（如 ++）"""
        # 简单策略：删除常见不支持的操作符
        replacements = {
            "++": "",
            "--": "",
        }
        fixed = code
        for old, new in replacements.items():
            fixed = fixed.replace(old, new)
        return fixed


# ═══════════════════════════════════════════════
#  对外 API
# ═══════════════════════════════════════════════

def _clean_code(raw: str) -> str:
    """清理 LLM 输出中的 markdown 代码块包裹"""
    code = raw.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)
    return code.strip()


async def _call_llm(messages: list) -> str:
    """单次 LLM 调用，带超时"""
    response = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
        timeout=_REQUEST_TIMEOUT,
    )
    return _clean_code(response.choices[0].message.content)


async def generate_answer(problem_markdown: str, use_grammar_constraint: bool = False) -> Dict:
    """
    调用大模型生成题目答案，可选文法约束校验 + 自动重试修正。

    返回：
    {
        "answer_code": str,           # 最终答案代码
        "raw_code": str,              # 大模型原始输出
        "use_constraint": bool,
        "is_valid": bool | None,
        "corrections": [...],
        "validation_log": [...],
        "retry_history": [            # 重试历史（仅约束模式）
            {"attempt": 1, "code": "...", "errors": [...], "is_valid": false},
            ...
        ],
    }
    """
    user_prompt = (
        f"请为以下 C-Minus 题目编写参考答案代码：\n\n{problem_markdown}\n\n"
        f"请输出完整可编译的 C-Minus 代码。"
    )

    system_msg = {"role": "system", "content": ANSWER_SYSTEM_PROMPT}
    user_msg = {"role": "user", "content": user_prompt}
    messages = [system_msg, user_msg]

    # ── 首次生成 ──
    raw_code = await _call_llm(messages)

    if not use_grammar_constraint:
        return {
            "answer_code": raw_code,
            "raw_code": raw_code,
            "use_constraint": False,
            "is_valid": None,
            "corrections": [],
            "validation_log": [],
            "retry_history": [],
        }

    # ── 文法约束模式：校验 + 重试 ──
    validator = GrammarConstraintValidator()
    retry_history: List[Dict] = []

    for attempt in range(1, _MAX_RETRIES + 1):
        validation = validator.validate_and_correct(raw_code)
        is_valid = validation["is_valid"]
        errors = validation["validation_log"]
        corrections = validation["corrections"]

        retry_history.append({
            "attempt": attempt,
            "code": raw_code,
            "errors": errors,
            "corrections": corrections,
            "is_valid": is_valid,
        })

        if is_valid:
            # 校验通过，直接返回
            return {
                "answer_code": raw_code,
                "raw_code": retry_history[0]["code"],
                "use_constraint": True,
                "is_valid": True,
                "corrections": corrections,
                "validation_log": errors,
                "retry_history": retry_history,
            }

        # 未通过：构造纠错 prompt 重试
        if attempt < _MAX_RETRIES:
            error_summary = "\n".join(f"  - {e}" for e in errors[:5])
            correction_hints = "\n".join(
                f"  - {c['suggestion']}" for c in corrections[:5]
            )

            fix_prompt = (
                f"你之前输出的代码存在以下 C-Minus 文法错误，请修正后重新输出完整代码：\n\n"
                f"【原始错误代码】\n{raw_code}\n\n"
                f"【文法校验错误】\n{error_summary}\n\n"
                f"【修正建议】\n{correction_hints}\n\n"
                f"请只输出修正后的完整 C-Minus 代码，不要解释。"
            )

            messages.append({"role": "assistant", "content": raw_code})
            messages.append({"role": "user", "content": fix_prompt})

            try:
                raw_code = await _call_llm(messages)
            except Exception as e:
                retry_history[-1]["errors"].append(f"[重试失败] API 调用异常: {str(e)}")
                break

    # 最后一次校验
    final_validation = validator.validate_and_correct(raw_code)
    final_valid = final_validation["is_valid"]
    final_errors = final_validation["validation_log"]
    final_corrections = final_validation["corrections"]

    retry_history.append({
        "attempt": _MAX_RETRIES + 1,
        "code": raw_code,
        "errors": final_errors,
        "corrections": final_corrections,
        "is_valid": final_valid,
    })

    return {
        "answer_code": raw_code if final_valid else final_validation.get("corrected_code", raw_code),
        "raw_code": retry_history[0]["code"] if retry_history else raw_code,
        "use_constraint": True,
        "is_valid": final_valid,
        "corrections": final_corrections,
        "validation_log": final_errors,
        "retry_history": retry_history,
    }


# ═══════════════════════════════════════════════
#  大模型输出报告
# ═══════════════════════════════════════════════

REPORT_SYSTEM_PROMPT = """你是一个 C-Minus 编译原理教学专家。你需要根据学生提交的代码及其编译分析结果，生成一份结构化的诊断报告。

输出必须严格按照以下格式（FEEDBACK 块），不要输出任何额外内容：

FEEDBACK {
  SCORE: <0~100 整数>;
  LEVEL: <easy|medium|hard>;
  COMMENT {
    TEXT: "<一句话总体评价>";
    SUGGESTION: "<一句改进建议>";
  }
  ERRORS ["""


async def generate_report(
    student_code: str,
    problem_markdown: str,
    syntax_errors: List[str],
    semantic_errors: List[str],
    ast_similarity: float,
    ast_edit_ops: List[Dict],
) -> Dict:
    """
    调用大模型生成诊断报告。

    返回：
    {
        "raw_report": str,                # LLM 原始输出
        "parsed": {                       # 结构化解析结果
            "score": int,
            "level": str,
            "comment_text": str,
            "suggestion": str,
            "errors": [{"line": int, "type": str, "msg": str}, ...],
        }
    }
    """
    # 构造上下文
    error_summary = ""
    all_errors = list(syntax_errors) + list(semantic_errors)
    if all_errors:
        error_summary = "检测到以下错误：\n" + "\n".join(f"  - {e}" for e in all_errors[:10])
    else:
        error_summary = "语法和语义分析均通过，未检测到错误。"

    ast_summary = f"AST 相似度: {ast_similarity}%"
    if ast_edit_ops:
        ops_text = "; ".join(
            f"{op.get('op', '?')}: {op.get('node', '?')}"
            for op in ast_edit_ops[:5]
        )
        ast_summary += f"。主要差异操作: {ops_text}"

    user_prompt = f"""请根据以下信息，生成 C-Minus 学生代码诊断报告：

【题目描述】
{problem_markdown[:500]}

【学生提交代码】
{student_code[:1000]}

【编译分析结果】
{error_summary}

【AST 对比】
{ast_summary}

请按 FEEDBACK 格式输出报告。SCORE 根据错误数量和 AST 相似度综合评定。"""

    raw = await _call_llm([
        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])

    # ── 解析 FEEDBACK 格式 ──
    parsed = _parse_feedback(raw, ast_similarity)

    return {
        "raw_report": raw,
        "parsed": parsed,
    }


# ═══════════════════════════════════════════════
#  个性化指导建议
# ═══════════════════════════════════════════════

GUIDANCE_SYSTEM_PROMPT = """你是一个 C-Minus 编译原理课程助教。你需要根据学生的代码和编译分析结果，以 Markdown 格式输出一份个性化指导建议。

请从以下维度进行评价（每个维度用 ### 标题）：

### 代码水平
- 评价语法正确性、语义规范性
- 指出具体的语法/语义错误及改进方向

### 代码风格
- 评价缩进、命名规范、结构清晰度
- 给出风格改进建议

### 数学思维
- 评价算法逻辑、表达式使用是否合理
- 分析时间复杂度或逻辑优化空间

### 综合建议
- 总结该同学的强项和薄弱点
- 给出下一步学习建议

输出要求：
1. 纯 Markdown 格式，不要用代码块包裹
2. 语气亲切、鼓励为主，批评为辅
3. 结合学生之前的表现（如有），给出成长性评价
4. 字数控制在 300-500 字"""


async def generate_guidance(
    student_code: str,
    problem_markdown: str,
    syntax_errors: List[str],
    semantic_errors: List[str],
    ast_similarity: float,
    history_summaries: List[str],
) -> str:
    """
    生成个性化指导建议（Markdown 格式）。

    参数：
    - history_summaries: 之前评价的摘要列表，用于给出成长性评价
    """
    error_text = ""
    all_errors = list(syntax_errors) + list(semantic_errors)
    if all_errors:
        error_text = "检测到以下问题：\n" + "\n".join(f"- {e}" for e in all_errors[:8])
    else:
        error_text = "语法和语义分析均通过。"

    history_text = ""
    if history_summaries:
        history_text = "该同学之前的评价摘要：\n" + "\n".join(
            f"- {s[:120]}" for s in history_summaries[-5:]
        )

    user_prompt = f"""请为以下 C-Minus 学生代码生成个性化指导：

【题目】
{problem_markdown[:400]}

【学生代码】
{student_code[:800]}

【编译结果】
{error_text}

【AST 相似度】
{ast_similarity}%

【历史评价】
{history_text if history_text else "(首次评价)"}

请输出 Markdown 格式的个性化指导。"""

    raw = await _call_llm([
        {"role": "system", "content": GUIDANCE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])

    return raw.strip()


def _parse_feedback(raw: str, fallback_score: float) -> Dict:
    """解析 FEEDBACK { SCORE: ...; ... } 格式，回退到默认值"""
    import re

    score = int(fallback_score)
    m = re.search(r'SCORE\s*:\s*(\d+)', raw)
    if m:
        score = max(0, min(100, int(m.group(1))))

    level = "medium"
    m = re.search(r'LEVEL\s*:\s*(\w+)', raw)
    if m:
        level = m.group(1).strip().lower()

    comment_text = ""
    m = re.search(r'TEXT\s*:\s*"([^"]*)"', raw)
    if not m:
        m = re.search(r'TEXT\s*:\s*([^;]+);', raw)
    if m:
        comment_text = m.group(1).strip().strip('"')

    suggestion = ""
    m = re.search(r'SUGGESTION\s*:\s*"([^"]*)"', raw)
    if not m:
        m = re.search(r'SUGGESTION\s*:\s*([^;}]+)', raw)
    if m:
        suggestion = m.group(1).strip().strip('"')

    errors = []
    for m in re.finditer(r'ERROR\s*\(line\s*:\s*(\d+)\s*,\s*type\s*:\s*(\w+)\s*,\s*msg\s*:\s*"([^"]*)"\)', raw):
        errors.append({
            "line": int(m.group(1)),
            "type": m.group(2),
            "msg": m.group(3),
        })

    return {
        "score": score,
        "level": level,
        "comment_text": comment_text,
        "suggestion": suggestion,
        "errors": errors,
    }
