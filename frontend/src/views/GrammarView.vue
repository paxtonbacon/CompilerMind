<template>
  <div class="gv-page">

    <div class="gv-body">
      <!-- 第一栏：LL(1) 文法 -->
      <div class="gv-col scroll-col">
        <div class="scroll-header ll-header">
          <span class="scroll-dot"></span>
          <span>LL(1) 文法（已消除左递归）</span>
        </div>
        <div class="scroll-body">
          <div v-for="(prods, nt) in llG" :key="nt" class="prod-item">
            <span class="nt-name">{{ nt }}</span>
            <span class="nt-arrow">→</span>
            <span v-for="(rhs, i) in prods" :key="i">
              <span v-if="i > 0" class="nt-or"> | </span>
              <code class="rhs-text">{{ rhs.join(' ') }}</code>
            </span>
          </div>
        </div>
      </div>

      <!-- 第二栏：LR 文法 -->
      <div class="gv-col scroll-col">
        <div class="scroll-header lr-header">
          <span class="scroll-dot"></span>
          <span>LR 文法（原始 CFG）</span>
        </div>
        <div class="scroll-body">
          <div v-for="(rhs_list, nt) in lrG" :key="nt" class="prod-item">
            <span class="nt-name">{{ nt }}</span>
            <span class="nt-arrow">→</span>
            <span v-for="(rhs, i) in rhs_list" :key="i">
              <span v-if="i > 0" class="nt-or"> | </span>
              <code class="rhs-text">{{ rhs }}</code>
            </span>
          </div>
        </div>
      </div>

      <!-- 第三栏：知识点卡片 -->
      <div class="gv-col cards-col">
        <div class="cards-title">文法知识点</div>
        <div class="cards-grid">
          <div v-for="card in learnCards" :key="card.title" class="lcard" @click="card.open=!card.open">
            <div class="lc-head">
              <span class="lc-icon">{{ card.icon }}</span>
              <span class="lc-title">{{ card.title }}</span>
              <span class="lc-arrow">{{ card.open ? '▾' : '▸' }}</span>
            </div>
            <div v-if="card.open" class="lc-body" v-html="card.body"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { marked } from 'marked'

const llG = ref({})
const lrG = ref({})

onMounted(async () => {
  try {
    const r = await axios.get('/api/grammar_info')
    llG.value = r.data.ll_grammar
    lrG.value = r.data.lr_grammar
  } catch {}
})

const learnCards = reactive([
  { title: '什么是上下文无关文法 (CFG)？', icon: '', open: true, body: marked.parse('**CFG** 由四元组 (V, Σ, R, S) 定义。C-Minus 的每一条产生式 `NT → α` 构成规则集 R。LL(1) 和 LR(1) 都是基于 CFG 的分析算法。') },
  { title: '左递归为什么必须消除？', icon: '', open: true, body: marked.parse('LL(1) 是**自顶向下**分析。若文法含左递归 `A → Aα`，解析器会无限递归。消除方法：`A → βA\'`，`A\' → αA\' | ε`。LR 分析则天然支持左递归。') },
  { title: 'FIRST 集如何计算？', icon: '', open: true, body: marked.parse('FIRST(α) = 可从 α 推导出的**第一个终结符**集合。\n\n1. 若 α 以终结符 a 开头 → FIRST = {a}\n2. 若 α 以非终结符 A 开头 → FIRST = FIRST(A)\n3. 若 A 可推导 ε → 继续看下一个符号') },
  { title: 'FOLLOW 集如何计算？', icon: '', open: true, body: marked.parse('FOLLOW(A) = 在句型中**紧跟在 A 之后**的终结符集合。用于 LL(1) 预测表中处理 ε 产生式，以及 SLR(1) 中确定规约位置。') },
  { title: 'LL(1) vs LR(1) 对比', icon: '', open: true, body: marked.parse('| 特性 | LL(1) | LR(1) |\n|------|-------|-------|\n| 分析方向 | 自顶向下 | 自底向上 |\n| 左递归 | ❌ 必须消除 | ✅ 天然支持 |\n| 分析表大小 | 较小 | 较大 |\n| 实现难度 | 递归下降 | 状态机 |\n| 表达能力 | LR(1) > LL(1) |') },
  { title: '文法冲突如何解决？', icon: '', open: true, body: marked.parse('**FIRST/FIRST 冲突**：同一非终结符的两个产生式 FIRST 集有交集 → 需左因子分解\n\n**FIRST/FOLLOW 冲突**：ε 产生式的 FOLLOW 与其他产生式 FIRST 交集 → 调整文法\n\n**Shift/Reduce 冲突**（LR）：如悬空 else → 默认 shift 优先') },
])
</script>

<style scoped>
.gv-page { height: 100%; display: flex; flex-direction: column; background: #f8fafc; border-radius: 8px; overflow: hidden; }
.gv-title { font-size: 17px; font-weight: 700; color: #1e293b; padding: 14px 20px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; }

/* 三栏主体 */
.gv-body { flex: 1; display: flex; gap: 12px; padding: 12px; min-height: 0; overflow: hidden; }
.gv-col { background: #fff; border: 1px solid #e8ecf1; border-radius: 10px; display: flex; flex-direction: column; }
.scroll-col { flex: 1; min-width: 0; }
.cards-col { flex: 1.1; min-width: 0; overflow-y: auto; padding: 14px; }

/* 书卷头 */
.scroll-header { display: flex; align-items: center; gap: 8px; padding: 10px 14px; font-size: 13px; font-weight: 600; border-bottom: 1px solid #f1f5f9; border-radius: 10px 10px 0 0; flex-shrink: 0; }
.ll-header { background: linear-gradient(135deg, #eff6ff, #dbeafe); color: #1e40af; }
.lr-header { background: linear-gradient(135deg, #f0fdf4, #dcfce7); color: #166534; }
.scroll-dot { width: 8px; height: 8px; border-radius: 50%; }
.ll-header .scroll-dot { background: #3b82f6; }
.lr-header .scroll-dot { background: #22c55e; }

/* 书卷体 */
.scroll-body { flex: 1; overflow-y: auto; padding: 10px 14px; font-size: 12px; line-height: 1.8; text-align: left; }
.prod-item { margin-bottom: 5px; }
.nt-name { color: #6366f1; font-weight: 700; }
.nt-arrow { color: #94a3b8; margin: 0 6px; }
.nt-or { color: #cbd5e1; font-weight: 700; }
.rhs-text { background: #f8fafc; padding: 1px 6px; border-radius: 3px; font-size: 11px; color: #334155; border: 1px solid #f1f5f9; }

/* FIRST/FOLLOW 折叠 */
.sets-collapse { border-top: 1px solid #f1f5f9; flex-shrink: 0; }
.sets-collapse :deep(.el-collapse-item__header) { font-size: 12px; padding: 6px 14px; }
.sets-collapse :deep(.el-collapse-item__content) { padding: 0 14px 8px; }
.sets-grid { display: flex; gap: 12px; }
.set-block { flex: 1; }
.set-label { font-size: 11px; font-weight: 600; color: #64748b; margin-bottom: 4px; }
.set-row { font-size: 10px; color: #475569; line-height: 1.7; font-family: 'Fira Code', monospace; }
.set-row b { color: #6366f1; }

/* 知识点卡片 */
.cards-title { font-size: 14px; font-weight: 600; color: #1e293b; margin-bottom: 10px; }
.cards-grid { display: flex; flex-direction: column; gap: 8px; }
.lcard { background: #fafbfc; border: 1px solid #e8ecf1; border-radius: 8px; padding: 10px 12px; cursor: pointer; transition: all .15s; }
.lcard:hover { border-color: #93c5fd; box-shadow: 0 2px 8px rgba(59,130,246,.08); }
.lc-head { display: flex; align-items: center; gap: 8px; text-align: left; }
.lc-icon { font-size: 17px; }
.lc-title { font-size: 12px; font-weight: 600; color: #334155; flex: 1; text-align: left; }
.lc-arrow { color: #94a3b8; font-size: 10px; }
.lc-body { font-size: 11px; color: #475569; line-height: 1.7; padding-top: 8px; border-top: 1px solid #f1f5f9; margin-top: 8px; text-align: left; }
.lc-body :deep(p) { margin: 3px 0; }
.lc-body :deep(code) { background: #f1f5f9; padding: 1px 5px; border-radius: 3px; font-size: 10px; }
.lc-body :deep(ul), .lc-body :deep(ol) { padding-left: 16px; margin: 3px 0; }
.lc-body :deep(table) { font-size: 10px; border-collapse: collapse; width: 100%; margin: 4px 0; }
.lc-body :deep(td), .lc-body :deep(th) { border: 1px solid #e2e8f0; padding: 3px 6px; }
</style>
