<template>
  <div class="layout">
    <!-- 顶栏 -->
    <header class="header">
      <div class="header-left">
        <div class="logo" @click="$router.push('/')">
          <span class="logo-text">AI-ZW</span>
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
          <span class="username">{{ username }}</span>
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
          <el-menu-item index="/quick-image">
            <el-icon><MagicStick /></el-icon>
            <template #title>快速生图</template>
          </el-menu-item>
          <el-menu-item index="/outfit">
            <el-icon><ShoppingBag /></el-icon>
            <template #title>一键穿搭</template>
          </el-menu-item>
          <el-menu-item index="/analysis">
            <el-icon><View /></el-icon>
            <template #title>AI 商品分析</template>
          </el-menu-item>
          <el-menu-item index="/model-gen">
            <el-icon><Avatar /></el-icon>
            <template #title>AI 生成模特</template>
          </el-menu-item>
          <el-menu-item index="/video">
            <el-icon><VideoCameraFilled /></el-icon>
            <template #title>视频生成</template>
          </el-menu-item>
          <el-menu-item index="/seed-grass">
            <el-icon><Picture /></el-icon>
            <template #title>种草图</template>
          </el-menu-item>
          <el-menu-item index="/product-image">
            <el-icon><Present /></el-icon>
            <template #title>商品主图/A+</template>
          </el-menu-item>
          <!-- 管理员专属 -->
          <el-menu-item v-if="isAdmin" index="/admin/users">
            <el-icon><User /></el-icon>
            <template #title>用户管理</template>
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
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  HomeFilled,
  ShoppingBag,
  View,
  Avatar,
  VideoCameraFilled,
  Picture,
  Present,
  MagicStick,
  Expand,
  Fold,
  Moon,
  Sunny,
  UserFilled,
  User,
  ArrowDown,
  SwitchButton,
} from '@element-plus/icons-vue'
import { useTheme } from '../composables/useTheme'
import { useAuth } from '../composables/useAuth'

const route = useRoute()
const { isDark, toggleTheme } = useTheme()
const { username, isAdmin, logout } = useAuth()

const sidebarCollapsed = ref(false)
const currentRoute = computed(() => route.path)

function handleLogout() {
  logout()
}
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

/* 内容区 */
.content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: var(--content-bg);
  transition: background-color 0.3s;
}
</style>
