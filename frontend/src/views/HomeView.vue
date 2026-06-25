<template>
  <div class="leetcode-workspace">
    
    <div class="pane-column problem-pane" :style="{ width: problemWidth + 'px' }">
      <div class="pane-header">
        <div class="header-left">
          <el-icon class="pane-icon" color="#007aff"><Document /></el-icon>
          <span class="pane-title">题目描述</span>
        </div>
        <el-button-group class="header-actions">
          <el-button size="small" class="lc-btn" @click="openGenerateDialog">
            指定生成
          </el-button>
          <el-button size="small" class="lc-btn" @click="handleRandomProblem" :loading="isGenerating">
            随机题目
          </el-button>
          <el-button size="small" class="lc-btn" @click="enableMarkdownInput">
            <el-icon><Edit /></el-icon> 写入
          </el-button>
        </el-button-group>
      </div>

      <div class="pane-body" v-loading="isGenerating" element-loading-text="大模型生成题目中，请稍候...">
        <div v-if="!isWritingMode" class="markdown-body" v-html="renderedMarkdown"></div>
        <div v-else class="markdown-editor-wrapper">
          <el-input v-model="markdownInput" type="textarea" :rows="20" class="lc-markdown-input" />
          <el-button type="primary" size="small" class="execute-btn" @click="executeMarkdown">执行并解析题目</el-button>
        </div>
      </div>
    </div>

    <div class="resizer-bar" @mousedown="startDragLeft"></div>

    <div class="pane-column code-pane">
      <div class="pane-header">
        <div class="header-left">
          <span class="pane-title">C Minus 代码输入区</span>
        </div>
        
        <div class="header-actions-right">
          <el-button-group class="font-control-group">
            <el-button size="small" title="缩小代码" @click="changeFontSize('decrease')">
              <el-icon><ZoomOut /></el-icon>
            </el-button>
            <el-button size="small" title="放大代码" @click="changeFontSize('increase')">
              <el-icon><ZoomIn /></el-icon>
            </el-button>
          </el-button-group>

          <el-button type="success" size="small" class="run-compile-btn" :loading="compileLoading" @click="handleCompile">
            <el-icon><VideoPlay /></el-icon> 运行编译
          </el-button>
        </div>
      </div>
      
      <div class="pane-body editor-pane-body">
        <vue-monaco-editor
          v-model:value="sourceCode"
          language="c"
          theme="vs"
          :options="editorOptions"
          class="lc-monaco-wrapper"
        />
      </div>
    </div>

    <div v-if="isCompiled" class="resizer-bar" @mousedown="startDragRight"></div>

    <div v-if="isCompiled" class="pane-column result-pane" :style="{ width: resultWidth + 'px' }">
      <div class="pane-header">
        <div class="header-left">
          <span class="pane-title">编译分析与控制台</span>
        </div>
        <el-button link class="close-pane-btn" @click="isCompiled = false">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <div class="pane-body">
        <CompilerResultPanel
          :tokens="tokensList"
          :ll-result="llResult"
          :lr-result="lrResult"
          :problem-markdown="markdownInput"
          :source-code="sourceCode"
          @close="isCompiled = false"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="配置题目生成要求" width="420px" class="lc-dialog">
      <el-form label-width="70px" size="small">
        <el-form-item label="难度等级">
          <el-select v-model="taskParams.difficulty" placeholder="选择难度等级" style="width: 100%">
            <el-option label="暂无评定 (Unrated)" value="Unrated" />
            <el-option label="入门 (白)" value="入门" />
            <el-option label="普及- (橙)" value="普及-" />
            <el-option label="普及/提高- (黄)" value="普及/提高-" />
            <el-option label="提高+/省选- (蓝)" value="提高+/省选-" />
            <el-option label="省选+/NOI- (紫)" value="省选+/NOI-" />
            <el-option label="NOI/NOI+/CTSC (黑)" value="NOI/NOI+/CTSC" />
          </el-select>
        </el-form-item>
        <el-form-item label="限定条件">
          <el-input v-model="taskParams.requirements" type="textarea" :rows="3" placeholder="要求描述..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button size="small" @click="dialogVisible = false">取消</el-button>
          <el-button size="small" type="primary" @click="submitGenerateTask" :loading="isGenerating">确认生成</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { Document, Edit, Cpu, VideoPlay, PieChart, Close, ZoomIn, ZoomOut } from '@element-plus/icons-vue'
import VueMonacoEditor from '@guolao/vue-monaco-editor'

import CompilerResultPanel from '../components/CompilerResultPanel.vue'
import { tokenize, llParse, lrParse, generateProblem, generateRandomProblem } from '../api.js'
import { sharedState } from '../store.js'

// --- 状态控制 ---
const isCompiled = ref(false)         
const compileLoading = ref(false)     
const isWritingMode = ref(false)      
const dialogVisible = ref(false)    
const fontSize = ref(18)  

const sourceCode = ref('')            
const tokensList = ref([])
const llResult = ref(null)            // LL(1) 解析结果
const lrResult = ref(null)            // LR(1) 解析结果
const markdownInput = ref(`### 题目生成区域

> 请点击上面按钮生成题目，或切换到写入模式手动输入题目描述。

> 这是一个题目生成与编译原理学习的在线平台，欢迎使用！`)

const taskParams = reactive({ difficulty: '', requirements: '' })
const problemWidth = ref(380)  
const resultWidth = ref(400) 
const isGenerating = ref(false)

// 同步题目内容到共享状态（供 LLMAnalysisView 聊天框读取）
watch(markdownInput, (v) => { sharedState.problemMarkdown = v }, { immediate: true })


// 3. 🟥 编写放大缩小方法
const changeFontSize = (type) => {
  if (type === 'increase' && fontSize.value < 32) {
    fontSize.value += 1
  } else if (type === 'decrease' && fontSize.value > 12) {
    fontSize.value -= 1
  }
}

// 4. 🟥 将原本的静态对象改为 computed 计算属性，实现动态响应
const editorOptions = computed(() => ({
  fontSize: fontSize.value, // 🟩 绑定动态字号
  fontFamily: "'Fira Code', Consolas, Monaco, monospace",
  theme: 'vs',              
  lineNumbers: 'on',        
  minimap: { enabled: false }, 
  automaticLayout: true,    
  wordWrap: 'on',           
  tabSize: 4,               
  scrollBeyondLastLine: false, 
  renderLineHighlight: 'all',  
  contextmenu: false,
}))

// 1. 指定生成请求
const submitGenerateTask = async () => {
  if (!taskParams.difficulty) {
    ElMessage.warning('请选择难度等级')
    return
  }
  
  isGenerating.value = true
  try {
    const res = await generateProblem({
      difficulty: taskParams.difficulty,
      requirements: taskParams.requirements || '无特殊要求'
    })
    
    // 假设后端返回的数据结构为 { data: { markdown: "..." } }
    markdownInput.value = res.data.markdown
    isWritingMode.value = false
    dialogVisible.value = false
    ElMessage.success('大模型生成完毕！')
  } catch (error) {
    console.error(error)
    ElMessage.error('题目生成失败，请检查后端或大模型接口状态')
  } finally {
    isGenerating.value = false
  }
}

// 2. 随机生成请求
const handleRandomProblem = async () => {
  isGenerating.value = true
  try {
    const res = await generateRandomProblem()
    markdownInput.value = res.data.markdown
    isWritingMode.value = false
    ElMessage.success('随机生成题目成功！')
  } catch (error) {
    ElMessage.error('生成随机题目失败')
  } finally {
    isGenerating.value = false
  }
}


// 拖拽左边界控制条（调节第一栏宽度）
const startDragLeft = (downEvent) => {
  downEvent.preventDefault()
  const startX = downEvent.clientX
  const startWidth = problemWidth.value

  const onMouseMove = (moveEvent) => {
    // 鼠标当前位置减去按下的位置，得到偏移量
    const deltaX = moveEvent.clientX - startX
    const newWidth = startWidth + deltaX
    
    // 设置安全边界：限制题目栏最小 260px，最大 700px，防止被捏死或撑爆
    if (newWidth >= 260 && newWidth <= 700) {
      problemWidth.value = newWidth
    }
  }

  const onMouseUp = () => {
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// 拖拽右边界控制条（调节第三栏宽度）
const startDragRight = (downEvent) => {
  downEvent.preventDefault()
  const startX = downEvent.clientX
  const startWidth = resultWidth.value

  const onMouseMove = (moveEvent) => {
    // 注意：往左拖动时鼠标 clientX 减小，但右侧栏宽度应该增加，所以用减法
    const deltaX = moveEvent.clientX - startX
    const newWidth = startWidth - deltaX
    
    // 设置安全边界：限制结果面板最小 280px，最大 750px
    if (newWidth >= 280 && newWidth <= 750) {
      resultWidth.value = newWidth
    }
  }

  const onMouseUp = () => {
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// --- 其余核心计算属性与业务方法 ---

const renderedMarkdown = computed(() => marked.parse(markdownInput.value))

const openGenerateDialog = () => { dialogVisible.value = true }
const enableMarkdownInput = () => { isWritingMode.value = true }
const executeMarkdown = () => { isWritingMode.value = false }

const handleCompile = async () => {
  if (!sourceCode.value.trim()) {
    ElMessage.warning('代码区为空，请输入代码后再执行编译')
    return
  }
  compileLoading.value = true
  let hasAnyResult = false

  try {
    // 词法分析：必须成功
    const tokRes = await tokenize(sourceCode.value)
    tokensList.value = tokRes.data.tokens
    hasAnyResult = true
    sharedState.sourceCode = sourceCode.value
  } catch (e) {
    console.error('词法分析失败', e)
    tokensList.value = []
  }

  try {
    // LL(1) 解析
    const llRes = await llParse(sourceCode.value)
    llResult.value = llRes.data
    sharedState.llResult = llRes.data
    hasAnyResult = true
  } catch (e) {
    console.error('LL 解析失败', e)
    llResult.value = null
  }

  try {
    // LR(1) 解析
    const lrRes = await lrParse(sourceCode.value)
    lrResult.value = lrRes.data
    sharedState.lrResult = lrRes.data
    hasAnyResult = true
  } catch (e) {
    console.error('LR 解析失败', e)
    lrResult.value = null
  }

  if (hasAnyResult) {
    isCompiled.value = true
    const hasErrors = (llResult.value?.syntax_errors?.length || 0) +
                      (lrResult.value?.syntax_errors?.length || 0) +
                      (llResult.value?.semantic_errors?.length || 0)
    if (hasErrors > 0) {
      ElMessage.warning(`编译完成，检测到 ${hasErrors} 个错误/警告，请查看详情`)
    } else {
      ElMessage.success('编译完成，未检测到错误')
    }
  } else {
    ElMessage.error('全部后端服务连接失败，请检查服务状态')
  }

  compileLoading.value = false
}
</script>

<style scoped>
/* ==================== 核心布局调整 ==================== */
.leetcode-workspace {
  display: flex;
  height: 100%;
  background-color: #fafafa;
  box-sizing: border-box;
  gap: 0; /* 🟥 移除了原有的固定 gap，改由拖拽条充当间距 */
}

/* 🟥 极客级无缝拖拽控制条样式 */
.resizer-bar {
  width: 8px; /* 宽度适中，既方便鼠标捕捉，又符合力扣间距 */
  cursor: col-resize; /* 鼠标悬停时变成左右双箭头 */
  background-color: #fafafa; /* 默认与背景同色 */
  position: relative;
  user-select: none;
  z-index: 5;
}

/* 鼠标 hover 到边界线上时，浮现出高质感的高亮蓝线 */
.resizer-bar::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 3px;
  width: 2px;
  background-color: transparent;
  transition: background-color 0.15s ease;
}

.resizer-bar:hover::after,
.resizer-bar:active::after {
  background-color: #007aff; /* 力扣/主流 IDE 激活态标志性蓝色 */
}

/* ==================== 容器分栏样式 ==================== */
.pane-column {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e5e5e5;
  overflow: hidden;
  box-sizing: border-box;
}

.problem-pane {
  flex-shrink: 0; /* 🟥 防止被 flex 机制强行压扁，宽度严格遵守 JS 变量 */
}

.code-pane {
  flex: 1; /* 🟩 核心：代码域无限自适应，吃掉剩余全部空间 */
  min-width: 250px;
}

.result-pane {
  flex-shrink: 0; /* 🟥 防止被压扁 */
  background-color: #ffffff;
}

/* ==================== 细节 UI 控制（保持不变） ==================== */
.pane-header {
  height: 42px;
  padding: 0 12px;
  background-color: #ffffff;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-left { display: flex; align-items: center; gap: 6px; }
.pane-title { font-weight: 600; color: #262626; font-size: 13px; }
.pane-body { flex: 1; padding: 14px; overflow-y: auto; font-size: 13px; color: #3c3c3c; }

/* ==================== 自定义滚动条（浅色·悬停显示） ==================== */
.pane-body::-webkit-scrollbar { width: 5px; }
.pane-body::-webkit-scrollbar-track { background: transparent; }
.pane-body::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 6px;
  transition: background 0.3s ease;
}
.pane-body:hover::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.15); }
.pane-body::-webkit-scrollbar-thumb:hover { background: rgba(0, 0, 0, 0.28); }
/* Firefox 兼容 */
.pane-body { scrollbar-width: thin; scrollbar-color: transparent transparent; }
.pane-body:hover { scrollbar-color: rgba(0, 0, 0, 0.15) transparent; }
.markdown-body :deep(h3) { font-size: 14px !important; font-weight: 600; color: #1a1a1a; margin-top: 14px; border-left: 3px solid #007aff; padding-left: 6px; }
.editor-pane-body { padding: 0; }
.lc-modern-editor { display: flex; height: 100%; width: 100%; background-color: #f9fafb; font-family: monospace; }
.editor-line-numbers { width: 42px; background-color: #f3f4f6; border-right: 1px solid #e5e7eb; padding-top: 10px; display: flex; flex-direction: column; align-items: center; }
.line-number-cell { font-size: 12px; color: #9ca3af; height: 22px; line-height: 22px; }
.editor-textarea { flex: 1; border: none; resize: none; outline: none; padding: 10px 12px; background-color: #ffffff; font-size: 13px; line-height: 22px; color: #1f2937; }
.run-compile-btn { background-color: #2db55d !important; border-color: #2db55d !important; }
.close-pane-btn { font-size: 16px; color: #8c8c8c; }
/* ==================== 编辑器分栏样式重构 ==================== */
.editor-pane-body {
  padding: 0; 
  position: relative;
  height: 100%;
  width: 100%;
}

/* 🟥 让 Monaco 完美无缝地吃满力扣分栏卡片的外壳 */
.lc-monaco-wrapper {
  width: 100%;
  height: 100%;
  padding-top: 8px; /* 给顶部留出微小的呼吸感 */
  background-color: #ffffff;
}

/* ==================== Markdown 渲染美化 ==================== */
.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  color: #24292f;
  line-height: 1.7;
  font-size: 14px;
  word-wrap: break-word;
}

/* 二级标题：底部带细分割线，显得正式 */
.markdown-body :deep(h2) {
  font-size: 18px;
  font-weight: 600;
  padding-bottom: 6px;
  border-bottom: 1px solid #eaecef;
  margin-top: 16px;
  margin-bottom: 12px;
  color: #1f2328;
}

/* 三级标题：带有小蓝条装饰，清晰划分模块 */
.markdown-body :deep(h3) {
  font-size: 15px;
  font-weight: 600;
  margin-top: 18px;
  margin-bottom: 10px;
  padding-left: 8px;
  border-left: 4px solid #ffffff;
  color: #24292f;
  text-align: left;
}

/* 引用块：非常适合用来做“难度：xxxx”的展示 */
.markdown-body :deep(blockquote) {
  margin: 12px 0;
  padding: 8px 16px;
  color: #57606a;
  background-color: #f6f8fa; /* 极浅灰背景 */
  border-left: 4px solid #d0d7de;
  border-radius: 4px;
}
.markdown-body :deep(blockquote p) {
  margin: 0;
  font-weight: 500;
}

/* 正文段落与列表 */
.markdown-body :deep(p) { margin-bottom: 12px; text-align: left;}
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 20px; margin-bottom: 12px; text-align: left;}
.markdown-body :deep(li) { margin-bottom: 4px; text-align: left;}

/* 强调文字 */
.markdown-body :deep(strong) { font-weight: 600; color: #24292f; text-align: left;}

/* ==================== 现代输入框美化 ==================== */
.markdown-editor-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

/* 穿透修改 Element Plus 输入框的内部结构 */
.lc-markdown-input :deep(.el-textarea__inner) {
  background-color: #f9fafb; /* 极简的浅灰背景 */
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  font-family: "Fira Code", Consolas, Monaco, monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.02);
  transition: all 0.25s ease;
  resize: none; /* 禁用原生拖拽，高度由外层控制 */
}

/* 聚焦时的呼吸灯边缘效果 */
.lc-markdown-input :deep(.el-textarea__inner):focus {
  background-color: #ffffff;
  border-color: #0674ab;
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.15);
  outline: none;
}
</style>