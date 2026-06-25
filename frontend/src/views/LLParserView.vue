<template>
  <div class="pv-page">

    <el-scrollbar class="pv-body">
      <!-- FIRST + FOLLOW 两栏 -->
      <div class="dual">
        <div class="pv-col">
          <div class="col-header first-header"><span class="col-dot"></span> FIRST 集</div>
          <div class="col-inner">
            <div v-for="r in firstTable" :key="r.nt" class="set-row">
              <span class="set-nt">{{ r.nt }}</span>
              <span class="set-arrow">=</span>
              <span class="set-vals">{{ r.first.join(', ') }}</span>
            </div>
          </div>
        </div>
        <div class="pv-col">
          <div class="col-header follow-header"><span class="col-dot"></span> FOLLOW 集</div>
          <div class="col-inner">
            <div v-for="r in followTable" :key="r.nt" class="set-row">
              <span class="set-nt">{{ r.nt }}</span>
              <span class="set-arrow">=</span>
              <span class="set-vals">{{ r.follow.join(', ') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 预测分析表 -->
      <div class="table-section">
        <div class="section-header">LL(1) 预测分析表</div>
        <div class="table-hint">行为非终结符，列为终结符。单元格为对应的产生式右侧。</div>
        <div class="table-wrap">
          <table class="pred-table">
            <thead>
              <tr><th>非终结符</th><th v-for="t in allTerminals" :key="t" class="th-term">{{ t }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="nt in allNonTerminals" :key="nt">
                <td class="td-nt">{{ nt }}</td>
                <td v-for="t in allTerminals" :key="t" class="td-cell" :class="{ 'td-has': predictMap[nt]?.[t] }">
                  <code v-if="predictMap[nt]?.[t]">{{ predictMap[nt][t] }}</code>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { sharedState } from '../store.js'

const firstTable = ref([])
const followTable = ref([])
const predictTable = ref([])
const predictMap = ref({})

onMounted(async () => {
  // 优先使用 HomeView 实时数据
  if (sharedState.llResult?.first_sets) {
    const fs = sharedState.llResult.first_sets
    firstTable.value = Object.entries(fs).map(([nt, arr]) => ({ nt, first: arr }))
    followTable.value = Object.entries(sharedState.llResult.follow_sets || {}).map(([nt, arr]) => ({ nt, follow: arr }))
    predictTable.value = sharedState.llResult.predict_table || []
  }
  if (!firstTable.value.length) {
    try {
      const r = await axios.get('/api/grammar_info')
      firstTable.value = r.data.first_table.map(x => ({ nt: x.nt, first: Array.isArray(x.first) ? x.first : x.first.split(', ') }))
      followTable.value = r.data.follow_table.map(x => ({ nt: x.nt, follow: Array.isArray(x.follow) ? x.follow : x.follow.split(', ') }))
      predictTable.value = r.data.predict_table || []
    } catch {}
  }

  // 构建预测表映射
  const map = {}
  for (const row of predictTable.value) {
    if (!map[row.non_terminal]) map[row.non_terminal] = {}
    map[row.non_terminal][row.terminal] = row.production
  }
  predictMap.value = map
})

const allTerminals = computed(() => {
  const s = new Set()
  for (const row of predictTable.value) s.add(row.terminal)
  return [...s].sort()
})
const allNonTerminals = computed(() => {
  const s = new Set()
  for (const row of predictTable.value) s.add(row.non_terminal)
  return [...s].sort()
})
</script>

<style scoped>
.pv-page { height: 100%; display: flex; flex-direction: column; background: #f8fafc; border-radius: 8px; overflow: hidden; }
.pv-title { font-size: 17px; font-weight: 700; color: #1e293b; padding: 14px 20px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; }
.pv-body { flex: 1; padding: 12px 20px; min-height: 0; }

.dual { display: flex; gap: 12px; margin-bottom: 16px; }
.pv-col { flex: 1; background: #fff; border: 1px solid #e8ecf1; border-radius: 10px; overflow: hidden; }

.col-header { display: flex; align-items: center; gap: 8px; padding: 10px 14px; font-size: 13px; font-weight: 600; }
.col-dot { width: 8px; height: 8px; border-radius: 50%; }
.first-header { background: linear-gradient(135deg, #eff6ff, #dbeafe); color: #1e40af; }
.first-header .col-dot { background: #3b82f6; }
.follow-header { background: linear-gradient(135deg, #f0fdf4, #dcfce7); color: #166534; }
.follow-header .col-dot { background: #22c55e; }

.col-inner { padding: 10px 14px; max-height: 360px; overflow-y: auto; }
.set-row { display: flex; gap: 6px; padding: 3px 0; font-size: 11px; border-bottom: 1px solid #fafafa; align-items: baseline; }
.set-nt { color: #6366f1; font-weight: 700; min-width: 160px; font-family: 'Fira Code', monospace; }
.set-arrow { color: #94a3b8; }
.set-vals { color: #475569; font-family: 'Fira Code', monospace; font-size: 10px; }

/* 预测表 */
.table-section { background: #fff; border: 1px solid #e8ecf1; border-radius: 10px; overflow: hidden; }
.section-header { padding: 10px 14px; font-size: 13px; font-weight: 600; color: #5b21b6; background: linear-gradient(135deg, #f5f3ff, #ede9fe); }
.table-hint { font-size: 11px; color: #94a3b8; padding: 6px 14px; }
.table-wrap { overflow-x: auto; padding: 0 14px 10px; }
.pred-table { border-collapse: collapse; font-size: 10px; width: 100%; }
.pred-table th, .pred-table td { border: 1px solid #e2e8f0; padding: 3px 6px; text-align: center; white-space: nowrap; }
.pred-table th { background: #f8fafc; font-weight: 600; color: #475569; font-size: 10px; position: sticky; top: 0; }
.td-nt { background: #f1f5f9; font-weight: 600; color: #6366f1; font-family: 'Fira Code', monospace; text-align: left !important; }
.td-cell { color: #cbd5e1; }
.td-has { background: #fefce8; }
.td-has code { font-family: 'Fira Code', monospace; color: #334155; font-size: 9px; }
.th-term { font-family: 'Fira Code', monospace; font-size: 9px; }
</style>
