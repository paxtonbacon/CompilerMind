// store.js — 跨页面共享状态（供 LLMAnalysisView 聊天框读取 HomeView 数据等）
import { reactive } from 'vue'

export const sharedState = reactive({
  problemMarkdown: '',
  sourceCode: '',
  answerCode: '',
  llResult: null,
  lrResult: null,
  astCompareResult: null,
  reportResult: null,
})
