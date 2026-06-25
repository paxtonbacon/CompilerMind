<template>
  <div class="lv-page">

    <div class="lv-body">
      <!-- 左栏：5 大类词法规则 -->
      <div class="lv-col">
        <div class="col-header regex-header"><span class="col-dot"></span> 词法规则分类</div>
        <div class="col-body">

          <!-- 1. 关键字 -->
          <div class="cat-block">
            <div class="cat-title">关键字 (Keywords)</div>
            <div class="cat-desc">保留字，必须小写。词法分析时将 ID 匹配后查表转换</div>
            <div class="cat-items">
              <code v-for="kw in keywords" :key="kw" class="kw-tag">{{ kw }}</code>
            </div>
          </div>

          <!-- 2. 标识符 -->
          <div class="cat-block">
            <div class="cat-title">标识符 (ID)</div>
            <div class="cat-desc">以字母或下划线开头，后跟字母/数字/下划线</div>
            <code class="regex-big">letter ( letter | digit )*</code>
          </div>

          <!-- 3. 常数 -->
          <div class="cat-block">
            <div class="cat-title">常数 (Constants)</div>
            <div class="sub-item"><b>字母</b> (letter)</div>
            <code class="regex-big">a | b | ... | z | A | B | ... | Z</code>
            <div class="sub-item"><b>数字</b> (digit)</div>
            <code class="regex-big">0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9</code>
            <div class="sub-item"><b>整数</b> (INTEGER)</div>
            <code class="regex-big">digit+</code>
            <div class="sub-item"><b>浮点数</b> (FLOAT)</div>
            <code class="regex-big">(digit+ . digit*) | (digit* . digit+)</code>
            <div class="cat-desc" style="margin-top:6px">
              ␣ 空白字符（空格、换行、制表符）— 词法分析时忽略<br/>
              💬 注释：<code>/* ... */</code>（可跨行，不可嵌套）及 <code>// ...</code>（单行）
            </div>
          </div>

          <!-- 4. 运算符 -->
          <div class="cat-block">
            <div class="cat-title">运算符 (Operators)</div>
            <div class="cat-items">
              <code v-for="op in operators" :key="op" class="op-tag">{{ op }}</code>
            </div>
          </div>

          <!-- 5. 界符 -->
          <div class="cat-block">
            <div class="cat-title">界符 (Delimiters)</div>
            <div class="cat-items">
              <code v-for="d in delimiters" :key="d" class="del-tag">{{ d }}</code>
            </div>
          </div>
        </div>
      </div>

      <!-- 右栏：完整 DFA 状态转换图 -->
      <div class="lv-col">
        <div class="col-header dfa-header"><span class="col-dot"></span> DFA 状态转换图</div>
        <div class="col-body dfa-body">
          <div v-for="(line, i) in dfaLines" :key="i" class="dfa-line">{{ line }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const keywords = ['else', 'if', 'int', 'return', 'void', 'while', 'for', 'float']
const operators = ['+', '-', '*', '/', '<', '<=', '>', '>=', '==', '!=', '=']
const delimiters = [';', ',', '(', ')', '[', ']', '{', '}', '/* */', '//']

const dfaLines = [
  '                              ╔═══════════╗',
  '           ──── 字母 ──────▶  ║  ID 状态   ║ ── 其他 ──▶ ( 接受: ID )',
  '          │                   ╚═══════════╝',
  '          │                   ╔═══════════╗',
  '  ╔═══════╧══════╗  ── 数字 ──▶ ║ INT 状态  ║ ── . ──▶ [FLOAT] ── 数字 ──▶ ( 接受: FLOAT )',
  '  ║    起始     ║            ╚═════╤═════╝  否则 ──▶ ( 接受: INTEGER )',
  '  ╚═══════╤══════╝                  │',
  '          │                   ╔═════╧═════╗',
  '          ├── < ──▶           ║  LT 状态  ║ ── = ──▶ ( 接受: LE   )',
  '          │                   ╚═══════════╝  否则 ──▶ ( 接受: LT   )',
  '          │                   ╔═══════════╗',
  '          ├── > ──▶           ║  GT 状态  ║ ── = ──▶ ( 接受: GE   )',
  '          │                   ╚═══════════╝  否则 ──▶ ( 接受: GT   )',
  '          │                   ╔═══════════╗',
  '          ├── = ──▶           ║ ASSIGN状态 ║ ── = ──▶ ( 接受: EQ   )',
  '          │                   ╚═══════════╝  否则 ──▶ ( 接受: ASSIGN)',
  '          │                   ╔═══════════╗',
  '          ├── ! ──▶           ║  NOT 状态  ║ ── = ──▶ ( 接受: NE   )',
  '          │                   ╚═══════════╝',
  '          │',
  '          ├── + ──▶ ( 接受: PLUS       )',
  '          ├── - ──▶ ( 接受: MINUS      )',
  '          ├── * ──▶ ( 接受: STAR       )',
  '          ├── / ──▶ ( 接受: DIV        )',
  '          ├── ; ──▶ ( 接受: SEMICOLON  )',
  '          ├── , ──▶ ( 接受: COMMA      )',
  '          ├── ( ──▶ ( 接受: LPAREN     )',
  '          ├── ) ──▶ ( 接受: RPAREN     )',
  '          ├── [ ──▶ ( 接受: LBRACKET   )',
  '          ├── ] ──▶ ( 接受: RBRACKET   )',
  '          ├── { ──▶ ( 接受: LBRACE     )',
  '          └── } ──▶ ( 接受: RBRACE     )',
  '',
  '  ═══ 注释处理 ═══',
  '  起始 ── / ──▶ [SLASH] ── * ──▶ [COMMENT] ── * ──▶ [STAR] ── / ──▶ 忽略',
  '                                     │                    │',
  '                                     └──── 其他 ── 回 ───┘',
  '  起始 ── / ──▶ [SLASH] ── / ──▶ 忽略至行尾 (// 单行注释)',
  '',
  '  ═══ 空白与换行 ═══',
  '  起始 ── 空格/\\t/\\n/\\r ──▶ 忽略，继续扫描',
]
</script>

<style scoped>
.lv-page { height: 100%; display: flex; flex-direction: column; background: #f8fafc; border-radius: 8px; overflow: hidden; }
.lv-title { font-size: 17px; font-weight: 700; color: #1e293b; padding: 14px 20px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; }

.lv-body { flex: 1; display: flex; gap: 12px; padding: 12px 20px; min-height: 0; overflow: hidden; }
.lv-col { flex: 1; background: #fff; border: 1px solid #e8ecf1; border-radius: 10px; display: flex; flex-direction: column; min-width: 0; }

.col-header { display: flex; align-items: center; gap: 8px; padding: 10px 14px; font-size: 13px; font-weight: 600; border-bottom: 1px solid #f1f5f9; border-radius: 10px 10px 0 0; flex-shrink: 0; }
.regex-header { background: linear-gradient(135deg, #fefce8, #fef9c3); color: #854d0e; }
.dfa-header { background: linear-gradient(135deg, #f5f3ff, #ede9fe); color: #5b21b6; }
.col-dot { width: 8px; height: 8px; border-radius: 50%; }
.regex-header .col-dot { background: #eab308; }
.dfa-header .col-dot { background: #8b5cf6; }

.col-body { flex: 1; overflow-y: auto; padding: 12px 14px; text-align: left; }

/* 分类块 */
.cat-block { margin-bottom: 14px; }
.cat-title { font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 3px; }
.cat-desc { font-size: 11px; color: #64748b; line-height: 1.6; margin-bottom: 6px; }
.cat-desc code { background: #f1f5f9; padding: 1px 5px; border-radius: 3px; font-size: 10px; }
.cat-items { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.sub-item { font-size: 11px; color: #475569; font-weight: 500; margin-top: 6px; }

.kw-tag { background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-family: 'Fira Code', monospace; }
.op-tag { background: #fce7f3; color: #9d174d; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-family: 'Fira Code', monospace; }
.del-tag { background: #e0e7ff; color: #3730a3; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-family: 'Fira Code', monospace; }
.regex-big { display: block; background: #f5f3ff; color: #6366f1; padding: 2px 10px; border-radius: 4px; font-size: 12px; font-family: 'Fira Code', monospace; margin-top: 2px; }

/* DFA */
.dfa-body { overflow: auto; }
.dfa-line { font-family: 'Fira Code', monospace; font-size: 10.5px; color: #334155; line-height: 1.2; white-space: pre; }
</style>
