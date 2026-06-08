<template>
  <div class="home">
    <div class="home-header">
      <h2>欢迎使用 AI-ZW</h2>
      <p>选择一个功能模块开始</p>
    </div>

    <div class="nav-grid">
      <div
        v-for="item in navItems"
        :key="item.path"
        class="nav-card"
        @click="$router.push(item.path)"
      >
        <div class="nav-card-icon" :style="{ background: item.color }">
          <el-icon :size="28" color="#fff"><component :is="item.icon" /></el-icon>
        </div>
        <div class="nav-card-body">
          <h4>{{ item.title }}</h4>
          <p>{{ item.desc }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { VideoCameraFilled, Avatar, ShoppingBag, View, Picture, Present } from '@element-plus/icons-vue'
import { markRaw } from 'vue'

const navItems = [
  {
    path: '/outfit',
    icon: markRaw(ShoppingBag),
    title: '一键穿搭展示',
    desc: '上传商品图，AI 生成模特穿搭展示',
    color: 'linear-gradient(135deg, #409eff, #79bbff)',
  },
  {
    path: '/analysis',
    icon: markRaw(View),
    title: 'AI 商品分析',
    desc: '上传商品图，AI 智能分析卖点与关键词',
    color: 'linear-gradient(135deg, #67c23a, #95d475)',
  },
  {
    path: '/model-gen',
    icon: markRaw(Avatar),
    title: 'AI 生成模特',
    desc: '指定参数生成模特图，保存到模特库',
    color: 'linear-gradient(135deg, #e6a23c, #eebe77)',
  },
  {
    path: '/video',
    icon: markRaw(VideoCameraFilled),
    title: '视频生成',
    desc: '上传参考图，生成商品展示视频',
    color: 'linear-gradient(135deg, #f56c6c, #fab6b6)',
  },
  {
    path: '/seed-grass',
    icon: markRaw(Picture),
    title: '种草图生成',
    desc: '博主人设 + 场景，生成博主生活照',
    color: 'linear-gradient(135deg, #b37feb, #d3adf7)',
  },
  {
    path: '/product-image',
    icon: markRaw(Present),
    title: '商品主图 / A+ 图',
    desc: '白底主图 + A+ 内容图，支持 AI 策划',
    color: 'linear-gradient(135deg, #36cfc9, #87e8de)',
  },
]
</script>

<style scoped>
.home {
  max-width: 900px;
}

.home-header {
  margin-bottom: 32px;
}

.home-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.home-header p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.nav-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}

.nav-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 22px 20px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.nav-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.1);
  border-color: #409eff;
}

html.dark .nav-card:hover {
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
}

.nav-card-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-card-body h4 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.nav-card-body p {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

@media (max-width: 768px) {
  .nav-grid {
    grid-template-columns: 1fr;
  }
}
</style>
