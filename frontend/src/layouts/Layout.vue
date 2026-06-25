<template>
  <div class="app-layout">
    <el-container class="layout-container">
      
      <el-header class="layout-header">
        <div class="header-left">
          <img 
            src="../assets/icon_menu.png" 
            alt="Toggle Menu" 
            class="toggle-btn"
            @click="isCollapsed = !isCollapsed"
          />
          <span class="logo-text">CompilerMind</span>
        </div>
        
        <div class="header-right">
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="el-dropdown-link">
              <el-icon class="more-icon"><MoreFilled /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="changePassword">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-container class="main-container">
        <el-aside :width="isCollapsed ? '64px' : '200px'" class="layout-aside">
          <el-menu
            :default-active="activeMenu"
            :collapse="isCollapsed"
            :collapse-transition="false"
            class="side-menu"
            router
            :teleported="false"
            popper-class="my-hidden-popper"
          >
            <el-menu-item index="/home">
               <el-icon :size="35" color="#409EFF"><HomeFilled /></el-icon>
              <template #title>主页</template>
            </el-menu-item>
            <el-menu-item index="/grammar">
              <el-icon :size="35" color="#409EFF"><List /></el-icon>
              <template #title>文法</template>
            </el-menu-item>
            <el-menu-item index="/lexer">
              <el-icon :size="35" color="#409EFF"><Opportunity /></el-icon>
              <template #title>词法</template>
            </el-menu-item>
            <el-menu-item index="/ll-parser">
              <el-icon :size="35" color="#409EFF"><Management /></el-icon>
              <template #title>LL语法</template>
            </el-menu-item>
            <el-menu-item index="/lr-parser">
              <el-icon :size="35" color="#409EFF"><Briefcase /></el-icon>
              <template #title>LR语法</template>
            </el-menu-item>
            <el-menu-item index="/semantic">
              <el-icon :size="35" color="#409EFF"><Stamp /></el-icon>
              <template #title>语义</template>
            </el-menu-item>
            <el-menu-item index="/llm-analysis">
              <el-icon :size="35" color="#409EFF"><Platform /></el-icon>
              <template #title>LLM分析</template>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <el-main class="layout-main">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </el-main>
      </el-container>

    </el-container>

    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码及用户信息"
      width="500px"
      destroy-on-close
      center
    >
      <el-form :model="pwdForm" label-width="100px" label-position="right">
        <el-form-item label="原始密码">
          <el-input v-model="pwdForm.oldPassword" type="password" show-password placeholder="请输入原始密码" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.newPassword" type="password" show-password placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="pwdForm.confirmPassword" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
        <el-form-item label="新用户名">
          <el-input v-model="pwdForm.newUsername" placeholder="请输入新用户名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="passwordDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitPasswordChange">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
// 导入 Element Plus 常用图标
import { 
  HomeFilled, Document, Operation, TrendCharts, 
  Share, Cpu, ChatLineRound, MoreFilled, 
  Opportunity,
  Management,
  Briefcase,
  Stamp,
  Platform
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 状态：左侧栏是否折叠（默认 true，只显示图标）
const isCollapsed = ref(true)

// 状态：修改密码弹窗可见性
const passwordDialogVisible = ref(false)

// 当前高亮的菜单项（根据当前路由动态决定）
const activeMenu = computed(() => route.path)

// 修改密码表单数据
const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
  newUsername: ''
})

// 处理下拉菜单点击事件
const handleCommand = (command) => {
  if (command === 'changePassword') {
    passwordDialogVisible.value = true
  } else if (command === 'logout') {
    localStorage.removeItem('cm_auth')
    router.push('/login')
  }
}

// 提交密码修改（之后对接 FastAPI 后端）
const submitPasswordChange = async () => {
  if (!pwdForm.oldPassword) { ElMessage.warning('请输入原始密码'); return }
  if (!pwdForm.newPassword) { ElMessage.warning('请输入新密码'); return }
  if (pwdForm.newPassword !== pwdForm.confirmPassword) { ElMessage.warning('两次新密码不一致'); return }
  try {
    await axios.post('/api/change_password', {
      old_password: pwdForm.oldPassword,
      new_password: pwdForm.newPassword,
      new_username: pwdForm.newUsername,
    })
    ElMessage.success('密码修改成功，请重新登录')
    localStorage.removeItem('cm_auth')
    passwordDialogVisible.value = false
    router.push('/login')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  }
}
</script>

<style scoped>
.app-layout {
  height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
}

.layout-container {
  height: 100%;
}

/* 顶部栏样式 */
.layout-header {
  background-color: #ffffff;
  color: #323232;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.toggle-btn {
  cursor: pointer;
  width: 24px;
  height: 24px;
  transition: transform 0.3s;
}
.toggle-btn:hover {
  transform: scale(1.1);
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
  letter-spacing: 1px;
}

.more-icon {
  color: #323232;
  font-size: 20px;
  cursor: pointer;
  transform: rotate(90deg); /* 旋转90度让三个点变成竖着的 */
  padding: 5px;
}

/* 侧边栏与主区域布局 */
.main-container {
  height: calc(100vh - 60px);
}

.layout-aside {
  background-color: #ffffff;
  border-right: 1px solid #e6e6e6;
  transition: width 0.3s ease-in-out; /* 让收缩有平滑动画 */
  overflow-x: hidden;
}

.side-menu {
  border-right: none;
  height: 100%;
  background-color: "#545c64"
  text-color="#fff"
  active-text-color="#ffd04b"
  radius="2"
}

.el-menu-item {
  transition: background-color 0.3s;
  padding-left: 0%;
  padding-right: 0%;
}

.el-menu-tooltip__trigger el-tooltip__trigger el-tooltip__trigger {
  padding: 0;
}

/* 主内容区样式 */
.layout-main {
  background-color: #fafafa;
  padding: 20px;
  overflow-y: auto;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>

<style>
/* 终极绝招：直接让这个黑色气泡隐藏（移走立刻消失或彻底不显） */
.el-popper.is-dark.el-menu-popper {
  display: none !important;
}
</style>

<style>
/* 1. 如果你想彻底关闭、让它完全不显示 */
.my-hidden-popper,
.el-menu-popper--collapse,
.el-tooltip__popper {
  display: none !important;
  opacity: 0 !important;
  visibility: hidden !important;
}

/* 2. 如果你想保留它，但去除延迟（鼠标移走立刻消失） */
.el-tooltip__popper {
  transition: none !important;
  transition-delay: 0s !important;
  animation: none !important;
}
</style>