<template>
  <div class="compiler-result-panel">
    
    <el-tabs v-model="activeMainTab" class="main-tabs" stretch>
      
      <el-tab-pane label="编译结果" name="result">
        <div class="tab-content-wrapper">
          
          <div class="sub-view-selector-bar">
            <span class="selector-label">查看细节：</span>
            <el-select v-model="activeSubView" size="small" style="width: 180px" class="lc-select">
              <el-option label="词法分析表" value="tokens" />
              <el-option label="最左推导步骤" value="derivation" />
              <el-option label="最左归约可视化" value="reduction" />
              <el-option label="AST 语法树" value="ast-compare" />
              <el-option label="作用域符号表" value="symbols" />
              <el-option label="语义分析" value="semantic" />
              <el-option label="P-Code 中间代码" value="ir-code" />
            </el-select>
          </div>

          <el-scrollbar class="sub-content-scroll">
            
            <div v-if="activeSubView === 'tokens'" class="pane-sub-core">
              <el-table :data="tokens" size="small" stripe border class="lc-table">
                <el-table-column prop="type" label="Token 类型" width="120" />
                <el-table-column prop="value" label="字面值 (Lexeme)" />
                <el-table-column prop="line" label="行" width="50" align="center" />
                <el-table-column prop="column" label="列" width="50" align="center" />
              </el-table>
            </div>

            <div v-if="activeSubView === 'derivation'" class="pane-sub-core">
              <div class="info-tip">Grammar: C-Minus 上下文无关文法推导轨迹（LL(1) 最左推导）</div>
              <div v-if="llErrors.length" class="error-tip">
                ⚠️ 语法错误：{{ llErrors.join('; ') }}
              </div>
              <el-timeline v-if="derivationSteps.length" class="lc-timeline">
                <el-timeline-item
                  v-for="(step, idx) in derivationSteps"
                  :key="idx"
                  :timestamp="'Step ' + step.seq"
                  :type="idx === 0 ? 'primary' : 'info'"
                >
                  <div class="code-font font-bold">{{ step.expr }}</div>
                </el-timeline-item>
              </el-timeline>
              <div v-else class="empty-hint">暂无推导数据</div>
            </div>

            <div v-if="activeSubView === 'reduction'" class="pane-sub-core">
              <div class="info-tip">LR 分析栈实时归约动作状态监控（SLR(1) 最左归约）</div>
              <div v-if="lrErrors.length" class="error-tip">
                ⚠️ 语法错误：{{ lrErrors.join('; ') }}
              </div>
              <div v-if="reductionSteps.length" class="reduction-step-card" v-for="(item, index) in reductionSteps" :key="index">
                <div class="card-row">
                  <span class="lbl">分析栈:</span> <span class="code-font stack-val">{{ item.stack }}</span>
                </div>
                <div class="card-row">
                  <span class="lbl">剩余输入:</span> <span class="code-font input-val">{{ item.input }}</span>
                </div>
                <div class="card-row action-row">
                  <el-tag size="small" :type="item.action.includes('r') ? 'success' : item.action === 'acc' ? '' : 'warning'">
                    {{ item.action === 'acc' ? '✅ 接受 (Accept)' : item.action.startsWith('s') ? '移进 (Shift ' + item.action.slice(1) + ')' : item.action.startsWith('r') ? '归约 (Reduce ' + item.action.slice(1) + ')' : item.action }}
                  </el-tag>
                </div>
              </div>
              <div v-else class="empty-hint">暂无归约数据</div>
            </div>

            <div v-if="activeSubView === 'semantic'" class="pane-sub-core">
              <div class="info-tip">语义分析：变量重定义检测 & 未声明引用检测</div>
              
              <div v-if="semanticErrors.length" class="error-tip">
                <strong>⚠️ 语义错误 ({{ semanticErrors.length }})：</strong>
                <ul style="margin: 4px 0 0 16px; padding: 0;">
                  <li v-for="(e, i) in semanticErrors" :key="i">{{ e }}</li>
                </ul>
              </div>
              <div v-else class="success-tip">
                ✅ 语义分析通过，未检测到变量重定义或未声明引用错误
              </div>

              <div style="margin-top: 16px;">
                <h4 style="font-size:13px; color:#1e293b; margin-bottom:8px;">符号表概览</h4>
                <el-table v-if="symbolTable.length" :data="symbolTable" size="small" stripe border class="lc-table">
                  <el-table-column prop="name" label="名称" width="100" />
                  <el-table-column prop="type" label="类型" width="70" />
                  <el-table-column prop="kind" label="类别" width="80" />
                  <el-table-column prop="scope" label="作用域" />
                </el-table>
                <div v-else class="empty-hint">暂无符号表数据</div>
              </div>
            </div>

            <div v-if="activeSubView === 'ast-compare'" class="pane-sub-core">
              <div class="ast-compare-box">
                <div class="ast-title pass-title">LL(1) 递归下降 AST</div>
                <pre class="ast-pre code-font text-green">{{ llTextTree }}</pre>

                <div v-if="llConflicts.length" class="conflict-info">
                  <strong>⚠️ LL 预测表冲突：</strong>
                  <ul>
                    <li v-for="(c, i) in llConflicts.slice(0, 5)" :key="i">{{ c }}</li>
                  </ul>
                </div>
                
                <div class="ast-title" style="background: #eff6ff; color: #1e40af; margin-top: 16px;">SLR(1) 最左归约 AST</div>
                <pre class="ast-pre code-font" style="color: #93c5fd !important;">{{ lrTextTree }}</pre>
              </div>
            </div>

            <div v-if="activeSubView === 'symbols'" class="pane-sub-core">
              <div class="info-tip">作用域符号表（由语义分析器构建）</div>
              <el-table v-if="symbolTable.length" :data="symbolTable" size="small" stripe border class="lc-table">
                <el-table-column prop="name" label="变量名" />
                <el-table-column prop="type" label="数据类型" width="80" />
                <el-table-column prop="kind" label="类别" width="80" />
                <el-table-column prop="scope" label="作用域 (Scope)" />
              </el-table>
              <div v-else class="empty-hint">暂无符号表数据</div>
            </div>

            <div v-if="activeSubView === 'ir-code'" class="pane-sub-core">
              <div class="info-tip">P-Code 三地址中间代码</div>
              <div v-if="pcode.length" class="ir-wrapper">
                <div class="ir-line" v-for="(code, i) in pcode" :key="i">
                  <span class="ir-num">{{ i }}</span>
                  <span class="ir-text code-font">{{ code }}</span>
                </div>
              </div>
              <div v-else class="empty-hint">暂无中间代码</div>
            </div>

          </el-scrollbar>
        </div>
      </el-tab-pane>

      <el-tab-pane label="题目解析" name="analysis">
        <div class="tab-content-wrapper">
          
          <div class="sub-view-selector-bar">
            <span class="selector-label">分析维度：</span>
            <el-select v-model="activeAnalysisSubView" size="small" style="width: 200px" class="lc-select">
              <el-option label="题目答案代码" value="answer-code" />
              <el-option label="AST 对比评分" value="ast-score" />
              <el-option label="大模型标准输出报告" value="llm-report" />
            </el-select>
          </div>

          <el-scrollbar class="sub-content-scroll">

            <!-- ── 子视图 1：题目答案代码 ── -->
            <div v-if="activeAnalysisSubView === 'answer-code'" class="pane-sub-core">
              <!-- 控制栏 -->
              <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
                <el-switch
                  v-model="useGrammarConstraint"
                  active-text="文法约束"
                  inactive-text="无约束"
                  size="small"
                />
                <el-button
                  type="primary"
                  size="small"
                  :loading="answerLoading"
                  @click="handleGenerateAnswer"
                  :disabled="!problemMarkdown"
                >
                  生成答案
                </el-button>
                <span v-if="answerResult" style="font-size:12px; color:#64748b;">
                  {{ answerResult.use_constraint ? '✅ 文法约束模式' : '⚡ 无约束模式' }}
                  {{ answerResult.is_valid ? '— 校验通过' : answerResult.is_valid === false ? '— ⚠️ 存在越界' : '' }}
                </span>
              </div>


              <!-- LLM 生成的答案 -->
              <div v-if="answerResult">
                <h4 style="font-size:13px; color:#1e293b; margin-bottom:4px;">
                  🎯 大模型参考答案
                  <span v-if="answerResult.use_constraint && answerResult.retry_history?.length > 1"
                        style="color:#d97706; font-weight:400;">
                    (已重试 {{ answerResult.retry_history.length - 1 }} 次)
                  </span>
                  <span v-if="answerResult.use_constraint && answerResult.is_valid"
                        style="color:#16a34a; font-weight:400;">
                    ✅ 校验通过
                  </span>
                </h4>
                <pre class="ast-pre code-font text-green" style="max-height:260px;">{{ answerResult.answer_code }}</pre>

                <!-- 重试历史 -->
                <div v-if="answerResult.retry_history?.length > 1" style="margin-top:8px;">
                  <h4 style="font-size:12px; color:#64748b; margin-bottom:4px;">🔄 文法纠错重试过程</h4>
                  <div v-for="(h, i) in answerResult.retry_history" :key="i" style="margin-bottom:6px;">
                    <div :class="h.is_valid ? 'retry-card-pass' : 'retry-card-fail'">
                      <div class="retry-header">
                        <span class="retry-badge">第 {{ h.attempt }} 次</span>
                        <span :style="{color: h.is_valid ? '#16a34a' : '#dc2626', fontSize:'11px'}">
                          {{ h.is_valid ? '✅ 通过' : `❌ ${h.errors.length} 个错误` }}
                        </span>
                      </div>
                      <div v-if="h.errors.length" class="retry-errors">
                        <div v-for="(e, j) in h.errors.slice(0, 3)" :key="j" class="retry-err-line">{{ e }}</div>
                        <div v-if="h.errors.length > 3" style="color:#94a3b8; font-size:10px;">
                          ... 还有 {{ h.errors.length - 3 }} 条错误
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 校验日志 -->
                <div v-if="answerResult.validation_log.length" style="margin-top:8px;">
                  <h4 style="font-size:12px; color:#64748b; margin-bottom:4px;">📋 最终文法校验日志</h4>
                  <div class="validation-log-box">
                    <div v-for="(log, i) in answerResult.validation_log" :key="i" class="log-line">
                      {{ log }}
                    </div>
                  </div>
                </div>

                <!-- 修正建议 -->
                <div v-if="answerResult.corrections.length" style="margin-top:8px;">
                  <h4 style="font-size:12px; color:#d97706; margin-bottom:4px;">🔧 修正建议</h4>
                  <div v-for="(c, i) in answerResult.corrections" :key="i" class="correction-card">
                    <div><strong>问题 Token:</strong> <code>{{ c.token }}</code></div>
                    <div><strong>说明:</strong> {{ c.issue }}</div>
                    <div><strong>建议:</strong> {{ c.suggestion }}</div>
                  </div>
                </div>
              </div>

              <!-- 错误汇总 -->
              <div style="margin-top:12px;">
                <h4 style="font-size:13px; color:#1e293b; margin-bottom:4px;">⚠️ 语法 / 语义错误汇总</h4>
                <div v-if="allErrors.length" class="error-tip">
                  <ul style="margin:4px 0 0 16px; padding:0;">
                    <li v-for="(e, i) in allErrors" :key="i">{{ e }}</li>
                  </ul>
                </div>
                <div v-else class="success-tip">✅ 未检测到语法或语义错误</div>
              </div>
            </div>

            <!-- ── 子视图 2：AST 对比评分 ── -->
            <div v-if="activeAnalysisSubView === 'ast-score'" class="pane-sub-core">
              
              <!-- 控制按钮 -->
              <div style="margin-bottom:12px;">
                <el-button
                  type="primary"
                  size="small"
                  :loading="astCompareLoading"
                  @click="handleASTCompare"
                  :disabled="!sourceCode || !answerResult?.answer_code"
                >
                  执行 AST 对比
                </el-button>
                <span v-if="!answerResult?.answer_code" style="font-size:11px; color:#94a3b8; margin-left:8px;">
                  请先生成参考答案
                </span>
              </div>

              <!-- 评分结果 -->
              <div v-if="astCompareResult">
                <div class="score-header" style="margin-bottom: 12px;">
                  <span class="score-lbl">AST 结构匹配度：</span>
                  <span class="score-val" :class="astCompareResult.similarity >= 80 ? 'text-green' : astCompareResult.similarity >= 50 ? '' : 'text-red'">
                    {{ astCompareResult.similarity }}%
                  </span>
                </div>
                <el-progress
                  :percentage="astCompareResult.similarity"
                  :status="astCompareResult.similarity >= 80 ? 'success' : astCompareResult.similarity >= 50 ? '' : 'exception'"
                  :stroke-width="10"
                />

                <div style="display:flex; gap:8px; margin-top:8px; font-size:11px; color:#64748b;">
                  <span>编辑距离: {{ astCompareResult.edit_distance }}</span>
                  <span>学生差异节点: {{ astCompareResult.student_diff_count }}</span>
                  <span>参考差异节点: {{ astCompareResult.reference_diff_count }}</span>
                </div>

                <!-- 双 AST 并排对比 -->
                <div style="display:flex; gap:12px; margin-top:16px;">
                  <div style="flex:1;">
                    <div class="ast-title" style="margin-top:0; background:#fef2f2; color:#991b1b;">
                      👨‍🎓 学生 SLR(1) AST
                    </div>
                    <pre class="ast-pre code-font" style="max-height:320px; font-size:10px; line-height:1.4;"
                         v-html="renderHighlightedTree(astCompareResult.student_tree)"></pre>
                  </div>
                  <div style="flex:1;">
                    <div class="ast-title" style="margin-top:0; background:#f0fdf4; color:#166534;">
                      📚 参考 SLR(1) AST
                    </div>
                    <pre class="ast-pre code-font" style="max-height:320px; font-size:10px; line-height:1.4;"
                         v-html="renderHighlightedTree(astCompareResult.reference_tree)"></pre>
                  </div>
                </div>
              </div>

              <!-- 无结果时的默认展示 -->
              <div v-else>
                <div class="score-header" style="margin-bottom: 12px;">
                  <span class="score-lbl">AST 结构匹配度：</span>
                  <span class="score-val" style="color:#94a3b8;">--</span>
                </div>
                <el-progress :percentage="0" :stroke-width="10" />
                <div style="display:flex; gap:12px; margin-top:16px;">
                  <div style="flex:1;">
                    <div class="ast-title pass-title" style="margin-top:0;">学生 AST</div>
                    <pre class="ast-pre code-font" style="max-height:260px; font-size:10px;">{{ lrTextTree || '(暂无)' }}</pre>
                  </div>
                  <div style="flex:1;">
                    <div class="ast-title" style="margin-top:0; background:#eff6ff; color:#1e40af;">参考 AST</div>
                    <pre class="ast-pre code-font" style="max-height:260px; font-size:10px; color:#93c5fd !important;">(请先生成参考答案)</pre>
                  </div>
                </div>
              </div>
            </div>

            <!-- ── 子视图 3：大模型输出报告 ── -->
            <div v-if="activeAnalysisSubView === 'llm-report'" class="pane-sub-core">
             
              <div style="margin-bottom:12px;">
                <el-button
                  type="primary"
                  size="small"
                  :loading="reportLoading"
                  @click="handleGenerateReport"
                >
                  生成诊断报告
                </el-button>
              </div>

              <div v-if="reportResult?.parsed" class="report-container">
                <!-- 总分卡片 -->
                <div class="report-score-card">
                  <div class="score-big">{{ reportResult.parsed.score }}</div>
                  <div class="score-label">综合评分 / 100</div>
                  <el-tag size="small" :type="reportResult.parsed.level === 'easy' ? 'success' : reportResult.parsed.level === 'hard' ? 'danger' : 'warning'">
                    {{ reportResult.parsed.level.toUpperCase() }}
                  </el-tag>
                </div>

                <!-- 评语 -->
                <div class="report-comment">
                  <h4>💬 总体评价</h4>
                  <p>{{ reportResult.parsed.comment_text || '(暂无)' }}</p>
                  <h4>💡 改进建议</h4>
                  <p>{{ reportResult.parsed.suggestion || '(暂无)' }}</p>
                </div>

                <!-- 错误列表 -->
                <div v-if="reportResult.parsed.errors?.length" class="report-errors">
                  <h4>⚠️ 错误详情</h4>
                  <el-table :data="reportResult.parsed.errors" size="small" stripe border class="lc-table">
                    <el-table-column prop="line" label="行号" width="60" align="center" />
                    <el-table-column prop="type" label="类型" width="80">
                      <template #default="{ row }">
                        <el-tag size="small" :type="row.type === 'runtime' ? 'danger' : row.type === 'logic' ? 'warning' : 'info'">
                          {{ row.type }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="msg" label="错误信息" />
                  </el-table>
                </div>

                <!-- 原始输出折叠 -->
                <el-collapse style="margin-top:12px;">
                  <el-collapse-item title="📄 查看原始 FEEDBACK 输出">
                    <pre class="ast-pre code-font" style="max-height:200px; font-size:10px;">{{ reportResult.raw_report }}</pre>
                  </el-collapse-item>
                </el-collapse>
              </div>

              <div v-else class="empty-hint" style="text-align:left;">
                <p>点击上方按钮，大模型将综合以下信息生成诊断报告：</p>
                <ul style="font-size:12px; color:#64748b; padding-left:16px;">
                  <li>题目描述</li>
                  <li>学生提交代码</li>
                  <li>语法/语义错误 ({{ allErrors.length }} 条)</li>
                  <li>AST 相似度 ({{ astCompareResult?.similarity || '--' }}%)</li>
                </ul>
              </div>
            </div>

          </el-scrollbar>
        </div>
      </el-tab-pane>

      <el-tab-pane label="AI 指导与个性建议" name="guidance">
        <div class="tab-content-wrapper">

          <div class="sub-view-selector-bar">
            <span class="selector-label">操作：</span>
            <el-button
              type="primary"
              size="small"
              :loading="guidanceLoading"
              @click="handleGenerateGuidance"
            >
              生成个性化指导
            </el-button>
          </div>

          <el-scrollbar class="sub-content-scroll">
            <div class="pane-sub-core">

              <!-- 当前指导 -->
              <div v-if="guidanceMarkdown" class="guidance-result">
                <div class="markdown-preview" style="max-height:none;"
                     v-html="renderedGuidance"></div>
              </div>
              <div v-else class="empty-hint">
                <p>点击按钮，AI 生成个性指导：</p>
                <div style="display:flex; gap:16px; margin-top:12px; justify-content:center;">
                  <div class="dimension-card">
                    <span style="font-size:20px;"></span>
                    <span>代码水平</span>
                  </div>
                  <div class="dimension-card">
                    <span style="font-size:20px;"></span>
                    <span>代码风格</span>
                  </div>
                  <div class="dimension-card">
                    <span style="font-size:20px;"></span>
                    <span>数学思维</span>
                  </div>
                  <div class="dimension-card">
                    <span style="font-size:20px;"></span>
                    <span>综合建议</span>
                  </div>
                </div>
              </div>

              <!-- 历史记录 -->
              <div v-if="guidanceHistory.length" style="margin-top:20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                  <h4 style="font-size:13px; color:#1e293b; margin:0;">
                    历史评价 ({{ guidanceHistory.length }} 条)
                  </h4>
                  <el-button size="small" type="danger" text @click="clearHistory">
                    清空历史
                  </el-button>
                </div>
                <el-collapse>
                  <el-collapse-item
                    v-for="(item, idx) in [...guidanceHistory].reverse()"
                    :key="item.id"
                    :title="`${item.time} — ${item.title}`"
                  >
                    <div class="history-summary">{{ item.summary }}...</div>
                    <el-button size="small" type="primary" text
                               @click.stop="guidanceMarkdown = item.full">
                      查看完整评价
                    </el-button>
                  </el-collapse-item>
                </el-collapse>
              </div>

            </div>
          </el-scrollbar>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'
import { generateAnswer, compareAST, generateReport, generateGuidance } from '../api.js'

// 接收来自 HomeView 的真实编译分析数据
const props = defineProps({
  tokens: {
    type: Array,
    default: () => []
  },
  llResult: {
    type: Object,
    default: null
  },
  lrResult: {
    type: Object,
    default: null
  },
  problemMarkdown: {
    type: String,
    default: ''
  },
  sourceCode: {
    type: String,
    default: ''
  }
})

// 默认大模块定位在 "result"
const activeMainTab = ref('result')
// 编译结果二级子功能定位
const activeSubView = ref('tokens')
// 题目解析二级子功能定位
const activeAnalysisSubView = ref('answer-code')

// ── 派生数据（从 props 中提取，响应式） ──

// LL(1) 最左推导步骤 → 用于 derivation 视图
const derivationSteps = computed(() => {
  if (!props.llResult?.derivation_steps) return []
  return props.llResult.derivation_steps.map((step, idx) => ({
    seq: idx + 1,
    expr: step
  }))
})

// LR(1) 最左归约步骤 → 用于 reduction 视图
const reductionSteps = computed(() => {
  if (!props.lrResult?.parsing_steps) return []
  return props.lrResult.parsing_steps.map(item => ({
    stack: item.state_stack || '',
    input: item.remaining_input || '',
    action: item.action || ''
  }))
})

// LL AST 文本树
const llTextTree = computed(() => {
  return props.llResult?.text_tree || '暂无 LL AST 数据'
})

// LR AST 文本树
const lrTextTree = computed(() => {
  return props.lrResult?.text_tree || '暂无 LR AST 数据'
})

// 语法错误提示
const llErrors = computed(() => props.llResult?.syntax_errors || [])
const lrErrors = computed(() => props.lrResult?.syntax_errors || [])

// LL 冲突信息
const llConflicts = computed(() => props.llResult?.conflicts || [])

// ── 语义分析 ──
const symbolTable = computed(() => props.llResult?.symbol_table || [])
const semanticErrors = computed(() => props.llResult?.semantic_errors || [])

// ── P-Code ──
const pcode = computed(() => props.llResult?.pcode || [])

// ── 题目解析相关 ──
const useGrammarConstraint = ref(true)        // 默认开启文法约束
const answerLoading = ref(false)
const answerResult = ref(null)

const handleGenerateAnswer = async () => {
  if (!props.problemMarkdown) {
    ElMessage.warning('请先生成或输入题目描述')
    return
  }
  answerLoading.value = true
  try {
    const res = await generateAnswer({
      problem_markdown: props.problemMarkdown,
      use_grammar_constraint: useGrammarConstraint.value
    })
    answerResult.value = res.data
    ElMessage.success('答案生成完成')
    // 自动触发 AST 对比
    if (props.sourceCode && res.data.answer_code) {
      handleASTCompare()
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('答案生成失败，请检查 LLM API 配置')
  } finally {
    answerLoading.value = false
  }
}

// AST 对比
const astCompareLoading = ref(false)
const astCompareResult = ref(null)

const handleASTCompare = async () => {
  if (!props.sourceCode || !answerResult.value?.answer_code) {
    ElMessage.warning('需要用户代码和参考答案才能对比')
    return
  }
  astCompareLoading.value = true
  try {
    const res = await compareAST(props.sourceCode, answerResult.value.answer_code)
    astCompareResult.value = res.data
  } catch (e) {
    console.error(e)
    ElMessage.error('AST 对比失败')
  } finally {
    astCompareLoading.value = false
  }
}

// 大模型报告
const reportLoading = ref(false)
const reportResult = ref(null)

const handleGenerateReport = async () => {
  reportLoading.value = true
  try {
    const res = await generateReport({
      student_code: props.sourceCode,
      problem_markdown: props.problemMarkdown,
      syntax_errors: props.llResult?.syntax_errors || [],
      semantic_errors: props.llResult?.semantic_errors || [],
      ast_similarity: astCompareResult.value?.similarity || astScore.value,
      ast_edit_ops: astCompareResult.value?.edit_operations || []
    })
    reportResult.value = res.data
    ElMessage.success('诊断报告生成完成')
  } catch (e) {
    console.error(e)
    ElMessage.error('报告生成失败')
  } finally {
    reportLoading.value = false
  }
}

// ── AI 指导与个性建议 ──
const STORAGE_KEY = 'compilermind_guidance_history'

const loadHistory = () => {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch { return [] }
}
const saveHistory = (data) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

const guidanceLoading = ref(false)
const guidanceMarkdown = ref('')
const guidanceHistory = ref(loadHistory())

const extractProblemTitle = () => {
  // 从 markdown 中提取 ## 标题
  const m = props.problemMarkdown?.match(/^##\s*(.+)/m)
  return m ? m[1].trim() : '(未命名题目)'
}

const handleGenerateGuidance = async () => {
  guidanceLoading.value = true
  try {
    const historySummaries = guidanceHistory.value.map(h => h.summary)
    const res = await generateGuidance({
      student_code: props.sourceCode,
      problem_markdown: props.problemMarkdown,
      syntax_errors: props.llResult?.syntax_errors || [],
      semantic_errors: props.llResult?.semantic_errors || [],
      ast_similarity: astCompareResult.value?.similarity || astScore.value,
      history_summaries: historySummaries
    })
    guidanceMarkdown.value = res.data.markdown

    // 存入 localStorage 历史
    const summary = res.data.markdown.replace(/[#*`\n]/g, ' ').substring(0, 100)
    guidanceHistory.value.push({
      id: Date.now(),
      time: new Date().toLocaleString(),
      title: extractProblemTitle(),
      summary,
      full: res.data.markdown
    })
    // 最多保留 20 条
    if (guidanceHistory.value.length > 20) {
      guidanceHistory.value = guidanceHistory.value.slice(-20)
    }
    saveHistory(guidanceHistory.value)
    ElMessage.success('个性化指导生成完成')
  } catch (e) {
    console.error(e)
    ElMessage.error('指导生成失败')
  } finally {
    guidanceLoading.value = false
  }
}

const clearHistory = () => {
  guidanceHistory.value = []
  saveHistory([])
  ElMessage.success('历史记录已清除')
}

const renderedProblemMarkdown = computed(() => {
  if (!props.problemMarkdown) return '<p style="color:#94a3b8;">暂无题目描述，请在左侧生成或写入题目</p>'
  return marked.parse(props.problemMarkdown)
})

// 渲染指导 markdown
const renderedGuidance = computed(() => {
  if (!guidanceMarkdown.value) return ''
  return marked.parse(guidanceMarkdown.value)
})

// 汇总所有错误
const allErrors = computed(() => {
  const syntax = props.llResult?.syntax_errors || []
  const semantic = props.llResult?.semantic_errors || []
  return [...syntax, ...semantic]
})

// AST 匹配度评分（简化：基于错误数量和冲突数量）
const astScore = computed(() => {
  if (astCompareResult.value) return astCompareResult.value.similarity
  const errors = allErrors.value.length
  const conflicts = (props.llResult?.conflicts?.length || 0)
  if (!props.llResult && !props.lrResult) return 0
  // 无错误 → 100%，每个错误/冲突扣分
  const penalty = errors * 15 + conflicts * 5
  return Math.max(0, 100 - penalty)
})

// 高亮渲染：将 ❌ 标记的行标红
const renderHighlightedTree = (treeText) => {
  if (!treeText) return '(暂无数据)'
  return treeText.split('\n').map(line => {
    if (line.includes('❌')) {
      return `<span style="color:#ef4444; font-weight:bold;">${line}</span>`
    }
    return line
  }).join('\n')
}
</script>

<style scoped>
/* ==================== 核心：第三栏独立容器外壳 ==================== */
.compiler-result-panel {
  display: flex;
  flex-direction: column;
  height: 100%;          /* 继承父级高度，充满右侧网格 */
  background-color: #ffffff;
  overflow: hidden;      /* ⚠️ 极其重要：防止整个组件溢出，强行把溢出交由内部滚动条处理 */
}

/* ==================== 第一层：Element Tabs 布局锁定 ==================== */
.main-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;         /* 💡 现代CSS秘诀：允许Flex子项收缩到小于内容的高度，触发独立滚动 */
}

/* 强行让 Element 标签页的内容区填满剩余的所有垂直空间 */
.main-tabs :deep(.el-tabs__content) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;         /* 再次向下传递缩容权限 */
}

/* 强行让包裹内容的 Pane 容器充满 */
.main-tabs :deep(.el-tab-pane) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* ==================== 第二层：内容区域与滚动条管理 ==================== */
/* 编译结果标签页下的整体外壳 */
.tab-content-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* 核心二级子功能切换控制栏（保持固定高度，不参与滚动） */
.sub-view-selector-bar {
  flex-shrink: 0;        /* 严禁被压缩 */
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background-color: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
}

.selector-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

/* ==================== 第三层：绝对滚动的微调 ==================== */
/* 核心滚动组件：扔掉之前脆弱的 calc(100vh - Xpx)，改用自适应 flex */
.sub-content-scroll,
.main-content-scroll {
  flex: 1;               /* 贪婪扩展，吃掉所有剩下的空间 */
  min-height: 0;         /* 强制截断，激活内部滚动 */
}

/* 内部填充垫片 */
.pane-sub-core {
  padding: 12px;
}

/* ==================== 极客视觉样式（保持不变） ==================== */
.code-font {
  font-family: "Fira Code", Consolas, Monaco, monospace;
}

.info-tip {
  font-size: 11px;
  color: #94a3b8;
  background-color: #f8fafc;
  padding: 6px;
  border-radius: 4px;
  margin-bottom: 12px;
  border-left: 2px solid #94a3b8;
}

.reduction-step-card {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 8px;
  background-color: #ffffff;
  font-size: 12px;
}
.card-row { margin-bottom: 4px; color: #334155; }
.card-row .lbl { color: #64748b; font-weight: 500; display: inline-block; width: 65px; }
.action-row { text-align: right; margin-bottom: 0; }

.ast-compare-box { font-size: 12px; }
.ast-title { font-weight: 600; padding: 4px 8px; border-radius: 4px; margin-top: 10px; }
.pass-title { background-color: #f0fdf4; color: #166534; }
.error-title { background-color: #fef2f2; color: #991b1b; }
.ast-pre { background-color: #1e293b; color: #f8fafc; padding: 10px; border-radius: 6px; margin: 6px 0; overflow-x: auto; font-size: 11px; line-height: 1.5; text-align: left; white-space: pre; }
.text-green { color: #4ade80 !important; }
.text-red { color: #f87171 !important; }
.error-analysis { margin-top: 8px; color: #b45309; background-color: #fffbeb; padding: 8px; border-radius: 4px; border: 1px solid #fef3c7; }

.ir-wrapper { background-color: #1e293b; border-radius: 6px; padding: 10px; }
.ir-line { display: flex; font-size: 12px; line-height: 1.8; }
.ir-num { width: 30px; color: #64748b; user-select: none; text-align: right; margin-right: 12px; }
.ir-text { color: #38bdf8; }

.analysis-box, .guidance-box { padding: 16px; font-size: 13px; line-height: 1.6; color: #334155; }
.analysis-box h4, .guidance-box h5 { font-size: 14px; margin-top: 16px; margin-bottom: 8px; color: #1e293b; font-weight: 600; }
.analysis-box blockquote { background: #f1f5f9; border-left: 3px solid #cbd5e1; padding: 8px; margin: 10px 0; font-family: monospace; }
.score-header { display: flex; justify-content: space-between; font-weight: 600; margin-bottom: 6px; }
.ai-report-card { background: #fafafa; border: 1px dashed #d9d9d9; padding: 12px; border-radius: 6px; margin-top: 16px; }
.ai-report-card ul { padding-left: 16px; margin: 0; }
.ai-report-card li { margin-bottom: 8px; }

/* 新增：数据为空/错误提示 */
.error-tip {
  font-size: 12px;
  color: #991b1b;
  background: #fef2f2;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 12px;
  border-left: 3px solid #ef4444;
}
.success-tip {
  font-size: 13px;
  color: #166534;
  background: #f0fdf4;
  padding: 10px 12px;
  border-radius: 4px;
  border-left: 3px solid #22c55e;
}
.empty-hint {
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
  padding: 24px;
}
.conflict-info {
  margin-top: 12px;
  padding: 10px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  font-size: 12px;
  color: #92400e;
}
.conflict-info ul {
  margin: 4px 0 0 16px;
  padding: 0;
}

/* 题目解析：markdown 预览 */
.markdown-preview {
  background: #fafbfc;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.7;
  color: #334155;
  max-height: 200px;
  overflow-y: auto;
}
.markdown-preview :deep(h3) { font-size: 15px; color: #1e293b; margin: 0 0 8px; }
.markdown-preview :deep(p) { margin: 4px 0; }
.markdown-preview :deep(code) { background: #f1f5f9; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
.markdown-preview :deep(blockquote) { border-left: 3px solid #94a3b8; padding-left: 10px; color: #64748b; margin: 8px 0; }

/* 校验日志 */
.validation-log-box {
  background: #1e293b;
  border-radius: 4px;
  padding: 8px;
  max-height: 150px;
  overflow-y: auto;
}
.log-line {
  font-family: "Fira Code", monospace;
  font-size: 10px;
  color: #94a3b8;
  line-height: 1.6;
}
.correction-card {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 4px;
  padding: 6px 8px;
  margin-bottom: 4px;
  font-size: 11px;
  color: #92400e;
}
.correction-card code {
  background: #fef3c7;
  padding: 0 3px;
  border-radius: 2px;
}

/* 重试历史卡片 */
.retry-card-pass {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 4px;
  padding: 6px 8px;
}
.retry-card-fail {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 4px;
  padding: 6px 8px;
}
.retry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.retry-badge {
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  background: #e2e8f0;
  padding: 1px 6px;
  border-radius: 3px;
}
.retry-errors {
  margin-top: 4px;
}
.retry-err-line {
  font-family: "Fira Code", monospace;
  font-size: 10px;
  color: #991b1b;
  line-height: 1.5;
  padding-left: 4px;
  border-left: 2px solid #fca5a5;
  margin-bottom: 2px;
}

/* 报告卡片 */
.report-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.report-score-card {
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  color: #f8fafc;
}
.score-big {
  font-size: 36px;
  font-weight: 700;
  color: #38bdf8;
  line-height: 1;
}
.score-label {
  font-size: 12px;
  color: #94a3b8;
}
.report-comment {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px;
  text-align: left;
}
.report-comment h4 {
  font-size: 12px;
  color: #1e293b;
  margin: 0 0 4px;
}
.report-comment p {
  font-size: 13px;
  color: #475569;
  margin: 0 0 10px;
  line-height: 1.5;
}
.report-errors {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 12px;
}
.report-errors h4 {
  font-size: 12px;
  color: #991b1b;
  margin: 0 0 8px;
}

/* AI 指导 */
.guidance-result {
  background: #fafbfc;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 16px;
  text-align: left;
}
.dimension-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 16px;
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 12px;
  color: #475569;
}
.history-summary {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  margin-bottom: 8px;
}

/* 优化 Element Plus Tab 样式使其更精致 */
:deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: #f1f5f9;
}
:deep(.el-tabs__active-bar) {
  background-color: #3b82f6;
}
</style>