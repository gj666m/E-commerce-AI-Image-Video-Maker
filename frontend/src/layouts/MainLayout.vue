<template>
  <div class="layout">
    <!-- 顶栏 -->
    <header class="header">
      <div class="header-left">
        <div class="logo" @click="$router.push('/')">
          <span class="logo-text">AI-ZW</span>
        </div>
      </div>
      <div class="header-center">
        <!-- API易 余额展示（全员可见） -->
        <div v-if="balance.available" class="balance-box" :class="balanceClass">
          <el-icon><Wallet /></el-icon>
          <span class="balance-label">API易余额</span>
          <span class="balance-amount">${{ balance.quota_usd?.toFixed(2) }}</span>
        </div>
        <div v-else-if="balance.message" class="balance-box balance-error" :title="balance.message">
          <el-icon><Wallet /></el-icon>
          <span>余额查询失败</span>
        </div>
      </div>
      <div class="header-right">
        <el-switch
          v-model="isDark"
          :active-action-icon="Moon"
          :inactive-action-icon="Sunny"
          @change="toggleTheme"
          style="--el-switch-on-color: #2c2c3e"
        />
        <div class="user-info">
          <el-icon><UserFilled /></el-icon>
          <span class="username">{{ displayName }}</span>
          <el-tag v-if="isAdmin" type="danger" size="small" class="role-tag">管理员</el-tag>
        </div>
        <el-dropdown trigger="click">
          <el-button text circle>
            <el-icon><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="isAdmin" @click="$router.push('/admin/users')">
                <el-icon><User /></el-icon>用户管理
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="main">
      <!-- 侧边栏 -->
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <el-menu
          :default-active="currentRoute"
          :default-openeds="defaultOpenGroups"
          :collapse="sidebarCollapsed"
          :collapse-transition="true"
          background-color="var(--sidebar-bg)"
          text-color="var(--sidebar-text)"
          active-text-color="var(--sidebar-active-text)"
          router
        >
          <el-menu-item index="/">
            <el-icon><HomeFilled /></el-icon>
            <template #title>首页</template>
          </el-menu-item>
          <!-- AI 助手置顶（入口级，不归类） -->
          <el-menu-item index="/agent">
            <el-icon><ChatDotSquare /></el-icon>
            <template #title>AI 对话助手</template>
          </el-menu-item>
          <!-- Prompt 工坊置顶（入口级，AI 帮你写专业 prompt） -->
          <el-menu-item index="/prompt-workshop">
            <el-icon><MagicStick /></el-icon>
            <template #title>Prompt 工坊</template>
          </el-menu-item>

          <!-- 分组：图片 -->
          <el-sub-menu index="grp-image">
            <template #title>
              <el-icon><Picture /></el-icon>
              <span>图片</span>
            </template>
            <el-menu-item v-for="it in groups.image" :key="it.path" :index="it.path">
              <el-icon><component :is="it.icon" /></el-icon>
              <template #title>{{ it.title }}</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 分组：视频 -->
          <el-sub-menu index="grp-video">
            <template #title>
              <el-icon><VideoCameraFilled /></el-icon>
              <span>视频</span>
            </template>
            <el-menu-item v-for="it in groups.video" :key="it.path" :index="it.path">
              <el-icon><component :is="it.icon" /></el-icon>
              <template #title>{{ it.title }}</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 分组：产品/市场调研 -->
          <el-sub-menu index="grp-research">
            <template #title>
              <el-icon><TrendCharts /></el-icon>
              <span>产品/市场调研</span>
            </template>
            <el-menu-item v-for="it in groups.research" :key="it.path" :index="it.path">
              <el-icon><component :is="it.icon" /></el-icon>
              <template #title>{{ it.title }}</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 分组：历史记录 -->
          <el-sub-menu index="grp-history">
            <template #title>
              <el-icon><Clock /></el-icon>
              <span>历史记录</span>
            </template>
            <el-menu-item v-for="it in groups.history" :key="it.path" :index="it.path">
              <el-icon><component :is="it.icon" /></el-icon>
              <template #title>{{ it.title }}</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 分组：素材资产库 -->
          <el-sub-menu index="grp-asset">
            <template #title>
              <el-icon><Files /></el-icon>
              <span>素材资产库</span>
            </template>
            <el-menu-item v-for="it in groups.asset" :key="it.path" :index="it.path">
              <el-icon><component :is="it.icon" /></el-icon>
              <template #title>{{ it.title }}</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 分组：素材应用及数据跟踪（即将上线） -->
          <el-sub-menu index="grp-tracking" disabled>
            <template #title>
              <el-icon><DataAnalysis /></el-icon>
              <span>素材应用及数据跟踪</span>
              <el-tag size="small" type="info" class="soon-tag">即将上线</el-tag>
            </template>
          </el-sub-menu>

          <!-- 管理员专属 -->
          <el-menu-item v-if="isAdmin" index="/admin/users">
            <el-icon><User /></el-icon>
            <template #title>用户管理</template>
          </el-menu-item>
          <el-menu-item index="/user-guide">
            <el-icon><QuestionFilled /></el-icon>
            <template #title>使用手册</template>
          </el-menu-item>
        </el-menu>

        <!-- 折叠按钮 -->
        <div class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
          <el-icon :size="16">
            <component :is="sidebarCollapsed ? Expand : Fold" />
          </el-icon>
        </div>
      </aside>

      <!-- 内容区 -->
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, reactive } from 'vue'
import { useRoute } from 'vue-router'
import {
  HomeFilled,
  ShoppingBag,
  View,
  Avatar,
  VideoCameraFilled,
  VideoCamera,
  Picture,
  Present,
  MagicStick,
  TrendCharts,
  DocumentCopy,
  Clock,
  Expand,
  Fold,
  Moon,
  Sunny,
  UserFilled,
  User,
  ArrowDown,
  SwitchButton,
  Wallet,
  Film,
  PictureFilled,
  ChatDotSquare,
  QuestionFilled,
  Files,
  DataAnalysis,
} from '@element-plus/icons-vue'
import { markRaw } from 'vue'
import { useTheme } from '../composables/useTheme'
import { useAuth } from '../composables/useAuth'
import { getBalance, type BalanceResponse } from '../api'

const route = useRoute()
const { isDark, toggleTheme } = useTheme()
const { displayName, isAdmin, logout, refreshMe } = useAuth()

const sidebarCollapsed = ref(false)
const currentRoute = computed(() => route.path)

// 侧边栏分组定义（按需求方拍板的 6 板块归类）
const groups = {
  image: [
    { path: '/quick-image', title: '快速生图', icon: markRaw(MagicStick) },
    { path: '/outfit', title: '一键穿搭', icon: markRaw(ShoppingBag) },
    { path: '/model-gen', title: 'AI 生成模特', icon: markRaw(Avatar) },
    { path: '/seed-grass', title: '种草图', icon: markRaw(Picture) },
    { path: '/product-image', title: '商品主图 / A+', icon: markRaw(Present) },
  ],
  video: [
    { path: '/video', title: '视频生成', icon: markRaw(VideoCameraFilled) },
    { path: '/video-shots', title: '分镜视频', icon: markRaw(Film) },
  ],
  research: [
    { path: '/analysis', title: 'AI 商品分析', icon: markRaw(View) },
    { path: '/video-prompt', title: '提示词反推', icon: markRaw(MagicStick) },
    { path: '/replicate', title: '爆品复刻', icon: markRaw(TrendCharts) },
    { path: '/tiktok-script', title: 'TikTok 脚本提取', icon: markRaw(DocumentCopy) },
    { path: '/outfit-scrape', title: '穿搭素材抓取', icon: markRaw(PictureFilled) },
  ],
  history: [
    { path: '/history', title: '生成历史', icon: markRaw(Clock) },
    { path: '/video-history', title: '视频历史', icon: markRaw(VideoCamera) },
    { path: '/prompt-library', title: 'Prompt 复用库', icon: markRaw(Files) },
  ],
  asset: [
    { path: '/asset-library', title: '素材资产库', icon: markRaw(Files) },
  ],
}

// 根据当前路由自动展开所在分组
const defaultOpenGroups = computed(() => {
  const path = route.path
  const result: string[] = []
  for (const [key, items] of Object.entries(groups)) {
    if (items.some((it) => it.path === path)) {
      result.push(`grp-${key}`)
    }
  }
  return result
})

// API易 余额展示（全员可见，5 分钟自动刷新）
const balance = reactive<BalanceResponse>({
  success: false,
  available: false,
})
let balanceTimer: ReturnType<typeof setInterval> | null = null

const balanceClass = computed(() => {
  const v = balance.quota_usd ?? 0
  if (v >= 10) return 'balance-ok'
  if (v >= 1) return 'balance-warn'
  return 'balance-low'
})

async function loadBalance(opts?: { fresh?: boolean }) {
  try {
    const res = await getBalance(opts)
    Object.assign(balance, res)
  } catch (e) {
    // 静默失败，不打扰用户（header 隐藏即可）
    balance.available = false
    balance.message = '加载失败'
  }
}

// 提供全局事件总线：其他页面（如视频完成）可触发立即刷新
function refreshBalanceFresh() {
  loadBalance({ fresh: true })
}

function handleLogout() {
  logout()
}

onMounted(() => {
  loadBalance()
  balanceTimer = setInterval(loadBalance, 15 * 1000) // 15 秒（与后端缓存对齐）
  // 监听全局事件（如视频完成强制刷新余额）
  window.addEventListener('balance:refresh', refreshBalanceFresh as EventListener)
  // 拉取最新用户信息（display_name 等）
  refreshMe()
})

onBeforeUnmount(() => {
  if (balanceTimer) clearInterval(balanceTimer)
  window.removeEventListener('balance:refresh', refreshBalanceFresh as EventListener)
})
</script>

<style scoped>
.layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶栏 */
.header {
  height: var(--header-height);
  background: var(--header-bg);
  border-bottom: 1px solid var(--header-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
  z-index: 10;
  transition: background-color 0.3s, border-color 0.3s;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #409eff, #79bbff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 1px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}

.balance-box {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 13px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-regular);
  border: 1px solid transparent;
  transition: all 0.3s;
}

.balance-label {
  color: var(--el-text-color-secondary);
}

.balance-amount {
  font-weight: 600;
}

.balance-ok {
  background: var(--el-color-success-light-9);
  border-color: var(--el-color-success-light-5);
  color: var(--el-color-success);
}

.balance-warn {
  background: var(--el-color-warning-light-9);
  border-color: var(--el-color-warning-light-5);
  color: var(--el-color-warning);
}

.balance-low {
  background: var(--el-color-danger-light-9);
  border-color: var(--el-color-danger-light-5);
  color: var(--el-color-danger);
}

.balance-error {
  color: var(--el-text-color-placeholder);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.username {
  font-weight: 500;
}

.role-tag {
  margin-left: 2px;
}

/* 主体区域 */
.main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 侧边栏 */
.sidebar {
  width: var(--sidebar-width);
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width var(--sidebar-transition);
  overflow: hidden;
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}

.sidebar .el-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
}

.sidebar-toggle {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--sidebar-text);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  transition: background-color 0.2s;
  flex-shrink: 0;
}

.sidebar-toggle:hover {
  background: var(--sidebar-hover-bg);
  color: var(--sidebar-active-text);
}

/* "即将上线" 占位分组样式 */
.soon-tag {
  margin-left: 6px;
  opacity: 0.7;
}

.sidebar .el-sub-menu.is-disabled .el-sub-menu__title {
  opacity: 0.55;
  cursor: not-allowed;
}

/* 内容区 */
.content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: var(--content-bg);
  transition: background-color 0.3s;
}
</style>
