<template>
  <div class="llm-page">
    <div class="chat-container">
      <div class="chat-header">
        <span>CompilerMind AI 助教</span>
        <el-button size="small" text style="color:#94a3b8" @click="clearChat">清空记录</el-button>
      </div>
      <el-scrollbar ref="chatScroll" class="chat-body">
        <div v-for="(msg,i) in messages" :key="i" :class="['msg', msg.role==='user'?'msg-user':'msg-ai']">
          <div class="msg-bubble" v-html="msg.role==='ai'?renderMd(msg.content):msg.content"></div>
          <div class="msg-time">{{ msg.time }}</div>
        </div>
        <div v-if="chatLoading" class="msg msg-ai"><div class="msg-bubble typing">思考中...</div></div>
      </el-scrollbar>
      <div class="chat-input-row">
        <el-input v-model="input" placeholder="输入问题..." @keyup.enter="send" class="ci"/>
        <el-button type="primary" :loading="chatLoading" @click="send" style="margin-left:8px">发送</el-button>
      </div>
      <div class="context-bar">
        <el-tag size="small" type="info" style="cursor:pointer" @click="attachContext">📎 附带当前题目上下文</el-tag>
        <span v-if="hasContext" style="font-size:11px;color:#16a34a;margin-left:8px">已附加上下文</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { sharedState } from '../store.js'

const CHAT_STORAGE_KEY = 'compilermind_chat_history'

const loadMessages = () => {
  try { return JSON.parse(localStorage.getItem(CHAT_STORAGE_KEY) || '[]') }
  catch { return [] }
}
const saveMessages = (msgs) => {
  // 只存储最近 50 条
  const slim = msgs.slice(-50).map(({role,content,time}) => ({role,content,time}))
  localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(slim))
}

const input=ref(''),chatLoading=ref(false),hasContext=ref(false),chatScroll=ref(null)
const messages=ref(loadMessages())

// 自动保存
watch(messages, (v) => saveMessages(v), { deep: true })

const scrollDown=async()=>{await nextTick();chatScroll.value?.setScrollTop(99999)}

onMounted(()=>{
  if (!messages.value.length) {
    messages.value.push({role:'ai',content:'你好！我是 CompilerMind AI 助教，可以解答编译原理相关问题。点击下方 📎 可以附带当前题目和代码上下文。',time:new Date().toLocaleTimeString()})
  }
  scrollDown()
})

const renderMd=(t)=>marked.parse(t)

const attachContext=()=>{
  if(!sharedState.problemMarkdown&&!sharedState.sourceCode){ElMessage.warning('HomeView 中暂无题目/代码数据');return}
  hasContext.value=true
  const ctx=`【当前题目】${sharedState.problemMarkdown||'(无)'}\n【学生代码】\n${sharedState.sourceCode||'(无)'}\n【答案代码】\n${sharedState.answerCode||'(无)'}`
  messages.value.push({role:'system',content:'[已附加上下文]',time:new Date().toLocaleTimeString()})
  window.__chatContext=ctx
  ElMessage.success('上下文已附加')
}

const send=async()=>{
  const text=input.value.trim();if(!text)return
  messages.value.push({role:'user',content:text,time:new Date().toLocaleTimeString()})
  input.value='';await scrollDown()
  chatLoading.value=true
  try{
    const ctx=window.__chatContext||''
    const res=await axios.post('/api/chat',{message:text,context:ctx})
    messages.value.push({role:'ai',content:res.data.reply,time:new Date().toLocaleTimeString()})
  }catch{ElMessage.error('AI 回复失败')}
  finally{chatLoading.value=false;await scrollDown()}
}

const clearChat=()=>{
  messages.value=[]
  saveMessages([])
  ElMessage.success('聊天记录已清空')
}
</script>

<style scoped>
.llm-page{height:100%;display:flex;background:#fff;border-radius:8px;overflow:hidden}
.chat-container{flex:1;display:flex;flex-direction:column;min-height:0}
.chat-header{background:linear-gradient(135deg,#1e293b,#334155);color:#f8fafc;padding:10px 16px;font-size:15px;font-weight:600;flex-shrink:0;display:flex;justify-content:space-between;align-items:center}
.chat-body{flex:1;padding:12px;background:#f8fafc}
.msg{margin-bottom:12px;max-width:33%;width:fit-content}
.msg-user{margin-left:auto}.msg-ai{margin-right:auto}
.msg-bubble{padding:8px 12px;border-radius:12px;font-size:13px;line-height:1.6;text-align:left;word-break:break-word}
.msg-user .msg-bubble{background:#3b82f6;color:#fff;border-bottom-right-radius:4px}
.msg-ai .msg-bubble{background:#fff;border:1px solid #e2e8f0;border-bottom-left-radius:4px}
.msg-bubble.typing{color:#94a3b8;font-style:italic}
.msg-time{font-size:10px;color:#94a3b8;margin-top:2px;padding:0 4px}
.chat-input-row{display:flex;padding:8px 12px;border-top:1px solid #e2e8f0;background:#fff}
.ci{flex:1}
.context-bar{padding:4px 12px 8px;background:#fff}
.msg-ai :deep(h3){font-size:14px;margin:4px 0}
.msg-ai :deep(p){margin:4px 0}
.msg-ai :deep(code){background:#f1f5f9;padding:1px 4px;border-radius:3px;font-size:11px}
</style>
