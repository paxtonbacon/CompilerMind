import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../layouts/Layout.vue'

function isAuthenticated() {
  try {
    const auth = JSON.parse(localStorage.getItem('cm_auth') || '{}')
    return !!auth.time
  } catch { return false }
}

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/',
    component: Layout,
    redirect: '/home',
    children: [
      { path: 'home', name: 'Home', component: () => import('../views/HomeView.vue') },
      { path: 'grammar', name: 'Grammar', component: () => import('../views/GrammarView.vue') },
      { path: 'lexer', name: 'Lexer', component: () => import('../views/LexerView.vue') },
      { path: 'll-parser', name: 'LLParser', component: () => import('../views/LLParserView.vue') },
      { path: 'lr-parser', name: 'LRParser', component: () => import('../views/LRParserView.vue') },
      { path: 'semantic', name: 'Semantic', component: () => import('../views/SemanticView.vue') },
      { path: 'llm-analysis', name: 'LLMAnalysis', component: () => import('../views/LLMAnalysisView.vue') },
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, from, next) => {
  if (to.name === 'Login') return next()
  if (!isAuthenticated()) return next('/login')
  next()
})

export default router