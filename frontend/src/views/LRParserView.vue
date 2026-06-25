<template>
  <div class="pv-page">
    
    <el-scrollbar class="pv-body">
      <!-- 项目集族 -->
      <div class="section mb">
        <div class="section-header">LR(0) 项目集规范族</div>
        <div class="items-grid">
          <div v-for="(items, state) in itemSets" :key="state" class="item-card">
            <div class="item-state">State {{ state }}</div>
            <div class="item-list">
              <div v-for="(it, i) in items" :key="i" class="item-line">{{ it }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- LR 分析表 -->
      <div class="section">
        <div class="section-header">SLR(1) 分析表 (ACTION / GOTO)</div>
        <div class="table-hint">sN = 移进到状态 N，rN = 按产生式 N 规约，acc = 接受，数字 = GOTO 目标状态</div>
        <div class="table-wrap">
          <table class="lr-table">
            <thead>
              <tr><th>State</th><th v-for="c in tableCols" :key="c" class="th-col">{{ c }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in lrTable" :key="row.state">
                <td class="td-state">{{ row.state }}</td>
                <td v-for="c in tableCols" :key="c" class="td-cell" :class="cellClass(row[c])">
                  {{ row[c] || '' }}
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

const itemSets = ref({})
const lrTable = ref([])

onMounted(async () => {
  if (sharedState.lrResult?.item_sets) {
    itemSets.value = sharedState.lrResult.item_sets
    lrTable.value = sharedState.lrResult.lr_table || []
  }
  if (!Object.keys(itemSets.value).length) {
    try {
      const r = await axios.get('/api/grammar_info')
      itemSets.value = r.data.lr_item_sets || {}
      lrTable.value = r.data.lr_table || []
    } catch {}
  }
})

const tableCols = computed(() => {
  if (!lrTable.value.length) return []
  const s = new Set()
  lrTable.value.forEach(r => Object.keys(r).forEach(k => { if (k !== 'state') s.add(k) }))
  return [...s].sort()
})

const cellClass = (val) => {
  if (!val && val !== 0) return ''
  const s = String(val)
  if (s === 'acc') return 'td-acc'
  if (s.startsWith('s')) return 'td-shift'
  if (s.startsWith('r')) return 'td-reduce'
  return 'td-goto'
}
</script>

<style scoped>
.pv-page { height: 100%; display: flex; flex-direction: column; background: #f8fafc; border-radius: 8px; overflow: hidden; }
.pv-title { font-size: 17px; font-weight: 700; color: #1e293b; padding: 14px 20px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; }
.pv-body { flex: 1; padding: 12px 20px; min-height: 0; }
.mb { margin-bottom: 16px; }

.section { background: #fff; border: 1px solid #e8ecf1; border-radius: 10px; overflow: hidden; }
.section-header { padding: 10px 14px; font-size: 13px; font-weight: 600; color: #166534; background: linear-gradient(135deg, #f0fdf4, #dcfce7); }

/* 项目集网格 */
.items-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 8px; padding: 10px; }
.item-card { background: #fafbfc; border: 1px solid #e8ecf1; border-radius: 6px; padding: 8px 10px; }
.item-state { font-size: 12px; font-weight: 700; color: #6366f1; margin-bottom: 4px; }
.item-list { font-family: 'Fira Code', monospace; font-size: 10px; color: #475569; line-height: 1.6; }
.item-line { padding-left: 4px; }

/* 分析表 */
.table-hint { font-size: 11px; color: #94a3b8; padding: 6px 14px; }
.table-wrap { overflow-x: auto; padding: 0 14px 10px; }
.lr-table { border-collapse: collapse; font-size: 10px; }
.lr-table th, .lr-table td { border: 1px solid #e2e8f0; padding: 3px 7px; text-align: center; white-space: nowrap; min-width: 50px; }
.lr-table th { background: #f8fafc; font-weight: 600; color: #475569; font-size: 10px; }
.td-state { background: #f1f5f9; font-weight: 600; color: #6366f1; }
.td-shift { background: #dbeafe; color: #1e40af; font-weight: 600; }
.td-reduce { background: #dcfce7; color: #166534; font-weight: 600; }
.td-goto { background: #fefce8; color: #854d0e; }
.td-acc { background: #fce7f3; color: #9d174d; font-weight: 700; }
.th-col { font-family: 'Fira Code', monospace; font-size: 9px; }
</style>
