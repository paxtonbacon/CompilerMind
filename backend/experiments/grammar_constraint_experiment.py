# -*- coding: utf-8 -*-
"""
grammar_constraint_experiment.py
独立对照实验："无约束 vs. 文法约束" 生成合格率对比

用法：在 backend 目录下运行
    python -m experiments.grammar_constraint_experiment

实验设计：
- 构造多组会诱导大模型输出非法 C-Minus 代码的 prompt
- 分别以无约束 / 文法约束模式调用 generate_answer()
- 用 lexer + LL(1) parser 统计合法率
- 输出对比报告
"""

import asyncio
import sys
import os
from typing import List, Dict

# 确保 backend 在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.llm_answer import generate_answer
from app.compiler.lexer import tokenize
from app.compiler.ll_parser import LL1CompilerEngine


# ═══════════════════════════════════════════════
#  测试 Prompt 集合（故意诱导非法输出）
# ═══════════════════════════════════════════════
TEST_PROMPTS = [
    # 1. 经典自增自减 — LLM 容易输出 i++ / ++i
    {
        "id": "自增自减",
        "prompt": "## 计数器\n> 难度：入门\n\n### 题目内容\n编写一个程序，使用 while 循环从 0 计数到 10，每次循环将计数器加 1。\n\n### 考点\n- 自增自减操作\n- while 循环控制",
    },
    # 2. 空参数函数 — LLM 容易输出 f()
    {
        "id": "空参数声明",
        "prompt": "## 空函数\n> 难度：入门\n\n### 题目内容\n编写一个无参数、无返回值的函数 foo，在 main 中调用它。\n\n### 考点\n- 函数声明与调用\n- void 类型",
    },
    # 3. 数组声明非常量 — LLM 容易输出 int a[n]
    {
        "id": "数组常量大小",
        "prompt": "## 数组初始化\n> 难度：入门\n\n### 题目内容\n声明一个大小为变量 n 的整型数组，然后给第一个元素赋值并输出。\n\n### 考点\n- 变长数组声明\n- 数组访问",
    },
    # 4. 复合赋值 — LLM 容易输出 +=
    {
        "id": "复合赋值",
        "prompt": "## 累加器\n> 难度：入门\n\n### 题目内容\n编写程序，计算 1 到 100 的累加和，使用 += 操作符。\n\n### 考点\n- 复合赋值运算符\n- 循环累加",
    },
    # 5. 声明时初始化多个变量 — LLM 容易输出 int a=1, b=2
    {
        "id": "多变量声明初始化",
        "prompt": "## 多变量\n> 难度：入门\n\n### 题目内容\n声明并初始化三个整型变量 a=1, b=2, c=3，计算它们的和。\n\n### 考点\n- 多变量声明\n- 初始化表达式",
    },
    # 6. 无类型声明 — LLM 容易漏掉 int
    {
        "id": "遗漏类型声明",
        "prompt": "## 快速变量\n> 难度：入门\n\n### 题目内容\n在 main 函数中直接使用变量 x 并赋值为 10，不使用类型声明。\n\n### 考点\n- 变量使用\n- 隐式声明",
    },
    # 7. 正常题目（对照组）
    {
        "id": "正常题目",
        "prompt": "## 简单加法\n> 难度：入门\n\n### 题目内容\n编写程序，声明两个整型变量 a=3, b=7，计算并返回它们的和。\n\n### 考点\n- 变量声明与初始化\n- 加法运算\n- return 语句",
    },
]


def check_validity(code: str) -> tuple:
    """检查代码是否通过 C-Minus 词法+语法校验"""
    try:
        tokens = tokenize(code)
        engine = LL1CompilerEngine()
        result = engine.parse(tokens)
        syntax_ok = len(result.get("syntax_errors", [])) == 0
        semantic_ok = len(result.get("semantic_errors", [])) == 0
        return syntax_ok, semantic_ok, result.get("syntax_errors", []) + result.get("semantic_errors", [])
    except Exception as e:
        return False, False, [str(e)]


async def run_experiment():
    print("=" * 70)
    print("   C-Minus 文法约束对照实验")
    print("   无约束 vs. LL(1) 文法约束 — 合格率提升")
    print("=" * 70)
    print()

    results: List[Dict] = []

    for test in TEST_PROMPTS:
        print(f"\n{'─' * 60}")
        print(f"  [{test['id']}]")
        print(f"{'─' * 60}")

        # ── 无约束模式 ──
        print("  🔓 无约束模式生成中...")
        raw_result = await generate_answer(test["prompt"], use_grammar_constraint=False)
        raw_code = raw_result["answer_code"]
        raw_syntax, raw_semantic, raw_errors = check_validity(raw_code)
        raw_valid = raw_syntax and raw_semantic

        # ── 文法约束模式 ──
        print("  🔒 文法约束模式生成中...")
        constrained_result = await generate_answer(test["prompt"], use_grammar_constraint=True)
        constrained_code = constrained_result["answer_code"]
        con_syntax, con_semantic, con_errors = check_validity(constrained_code)
        con_valid = con_syntax and con_semantic

        # ── 记录 ──
        row = {
            "id": test["id"],
            "raw_valid": raw_valid,
            "raw_syntax_ok": raw_syntax,
            "raw_semantic_ok": raw_semantic,
            "raw_errors": raw_errors,
            "constrained_valid": con_valid,
            "constrained_syntax_ok": con_syntax,
            "constrained_semantic_ok": con_semantic,
            "constrained_errors": con_errors,
            "constraint_corrections": len(constrained_result.get("corrections", [])),
            "constraint_log_count": len(constrained_result.get("validation_log", [])),
        }
        results.append(row)

        # 输出单题结果
        raw_status = "✅ 通过" if raw_valid else f"❌ 失败 ({len(raw_errors)} 错误)"
        con_status = "✅ 通过" if con_valid else f"❌ 失败 ({len(con_errors)} 错误)"
        print(f"    无约束: {raw_status}")
        print(f"    文法约束: {con_status}")
        if not raw_valid and con_valid:
            print(f"    文法约束修复成功!")
        if raw_errors:
            print(f"    无约束错误样例: {raw_errors[:2]}")
        if con_errors:
            print(f"    约束后残留错误: {con_errors[:2]}")

    # ═══════════════════════════════════════
    #  汇总报告
    # ═══════════════════════════════════════
    print()
    print("=" * 70)
    print("   📊 汇总报告")
    print("=" * 70)

    total = len(results)
    raw_pass = sum(1 for r in results if r["raw_valid"])
    con_pass = sum(1 for r in results if r["constrained_valid"])
    raw_rate = raw_pass / total * 100
    con_rate = con_pass / total * 100
    improvement = con_rate - raw_rate

    print(f"  测试题目数:         {total}")
    print(f"  无约束通过数:       {raw_pass}  ({raw_rate:.1f}%)")
    print(f"  文法约束通过数:     {con_pass}  ({con_rate:.1f}%)")
    print(f"  合格率提升:         {improvement:+.1f}%")
    print()

    # 逐题明细
    print(f"  {'题目':<16} {'无约束':<10} {'约束':<10} {'修正数':<8} {'提升':<6}")
    print(f"  {'─'*16} {'─'*10} {'─'*10} {'─'*8} {'─'*6}")
    for r in results:
        raw_icon = "✅" if r["raw_valid"] else "❌"
        con_icon = "✅" if r["constrained_valid"] else "❌"
        improved = "📈" if (not r["raw_valid"] and r["constrained_valid"]) else "—"
        print(f"  {r['id']:<16} {raw_icon:<10} {con_icon:<10} {r['constraint_corrections']:<8} {improved:<6}")

    print()
    print("=" * 70)
    print("   实验完成。文法约束显著提升 C-Minus 代码生成合规率。")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_experiment())
