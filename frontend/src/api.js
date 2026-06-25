import axios from 'axios'

const api = axios.create({
    baseURL: '/api',
    headers: { 'Content-Type': 'application/json' }
})

// 全局 401 拦截：token 失效跳登录
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('cm_auth')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const tokenize = (code) => api.post('/tokenize', { code })
export const llParse = (code) => api.post('/ll_parse', { code })
export const lrParse = (code) => api.post('/lr_parse', { code })
export const parseCode = (code) => api.post('/parse', { code })
export const constrainedGenerate = (prompt) => api.post('/constrained_generate', null, { params: { prompt } })
export const diagnose = (code) => api.post('/diagnose', { code })
export const similarity = (studentCode, referenceCode) => api.post('/similarity', null, {
    params: { student: studentCode, reference: referenceCode }
})
// 新增：向后端请求指定生成的题目
export const generateProblem = (params) => api.post('/generate_problem', params)

// 新增：向后端请求随机生成的题目
export const generateRandomProblem = () => api.get('/generate_random_problem')

// 新增：向后端请求 LLM 生成题目答案
export const generateAnswer = (params) => api.post('/generate_answer', params)

// 新增：AST 树编辑距离对比
export const compareAST = (studentCode, referenceCode) => api.post('/compare_ast', {
  student_code: studentCode,
  reference_code: referenceCode
})

// 新增：大模型诊断报告
export const generateReport = (params) => api.post('/generate_report', params)

// 新增：个性化指导建议
export const generateGuidance = (params) => api.post('/generate_guidance', params)