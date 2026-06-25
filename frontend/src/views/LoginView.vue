<template>
  <div class="login-page">
    <div class="login-card">
      <h1>CompilerMind</h1>
      <p class="sub">编译原理课程设计系统</p>
      <el-form :model="form" label-width="0" @submit.prevent="doLogin">
        <el-form-item><el-input v-model="form.username" placeholder="用户名" size="large" /></el-form-item>
        <el-form-item><el-input v-model="form.password" type="password" show-password placeholder="密码" size="large" @keyup.enter="doLogin" /></el-form-item>
        <el-form-item><el-button type="primary" size="large" :loading="loading" @click="doLogin" style="width:100%">登 录</el-button></el-form-item>
      </el-form>
      <p v-if="error" class="err">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

const doLogin = async () => {
  if (!form.value.username || !form.value.password) return
  loading.value = true
  error.value = ''
  try {
    const res = await axios.post('/api/login', form.value)
    localStorage.setItem('cm_auth', JSON.stringify({ time: Date.now(), user: res.data.username }))
    router.replace('/home')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { height: 100vh; display: flex; align-items: center; justify-content: center; background: #fefcf5; }
.login-card { background: #fff; padding: 40px 36px; border-radius: 8px; width: 360px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
h1 { font-size: 24px; color: #1e293b; margin: 0 0 4px; text-align: center; }
.sub { font-size: 13px; color: #94a3b8; text-align: center; margin: 0 0 28px; }
.err { font-size: 12px; color: #dc2626; text-align: center; margin-top: 8px; }
</style>
