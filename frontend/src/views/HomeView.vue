<template>
  <div class="home">
    <!-- Hero 区 -->
    <div class="home-header">
      <h2>欢迎使用 AI-ZW</h2>
      <p>选择一个功能模块开始，或直接和 AI 对话助手说出你的需求</p>
    </div>

    <!-- AI 对话助手突出大卡片（置顶，入口级） -->
    <div class="agent-banner" @click="$router.push('/agent')">
      <div class="agent-banner-icon">
        <el-icon :size="32" color="#fff"><ChatDotSquare /></el-icon>
      </div>
      <div class="agent-banner-body">
        <div class="agent-banner-title">
          <span>AI 对话助手</span>
          <el-tag size="small" type="success" effect="dark" round>推荐</el-tag>
        </div>
        <p>不知道选哪个工具？直接告诉 AI 你的需求，它会自动调用生图 / 视频生成 / 商品分析等能力帮你完成</p>
      </div>
      <el-icon class="agent-banner-arrow"><ArrowRight /></el-icon>
    </div>

    <!-- 分区卡片网格 -->
    <section
      v-for="section in sections"
      :key="section.key"
      class="section"
    >
      <div class="section-header">
        <div class="section-title">
          <el-icon :size="18" :color="section.color"><component :is="section.icon" /></el-icon>
          <h3>{{ section.title }}</h3>
          <el-tag v-if="section.soon" size="small" type="info" round>即将上线</el-tag>
        </div>
        <p v-if="section.desc" class="section-desc">{{ section.desc }}</p>
      </div>

      <div v-if="section.items.length" class="section-grid" :class="{ single: section.items.length === 1 }">
        <div
          v-for="item in section.items"
          :key="item.path"
          class="nav-card"
          @click="$router.push(item.path)"
        >
          <div class="nav-card-icon" :style="{ background: item.color }">
            <el-icon :size="24" color="#fff"><component :is="item.icon" /></el-icon>
          </div>
          <div class="nav-card-body">
            <h4>{{ item.title }}</h4>
            <p>{{ item.desc }}</p>
          </div>
        </div>
      </div>

      <!-- 即将上线占位 -->
      <div v-else class="coming-soon">
        <el-icon :size="20"><InfoFilled /></el-icon>
        <span>该板块正在规划中，敬请期待</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  ChatDotSquare,
  ArrowRight,
  Picture,
  VideoCameraFilled,
  TrendCharts,
  Clock,
  Files,
  DataAnalysis,
  InfoFilled,
  MagicStick,
  ShoppingBag,
  Avatar,
  Present,
  Film,
  View,
  DocumentCopy,
  PictureFilled,
} from '@element-plus/icons-vue'
import { markRaw } from 'vue'

interface NavItem {
  path: string
  title: string
  desc: string
  icon: ReturnType<typeof markRaw>
  color: string
}

interface Section {
  key: string
  title: string
  desc?: string
  icon: ReturnType<typeof markRaw>
  color: string
  soon?: boolean
  items: NavItem[]
}

const sections: Section[] = [
  {
    key: 'image',
    title: '图片',
    desc: '出图类工具：从快速生图到垂直场景全覆盖',
    icon: markRaw(Picture),
    color: '#722ed1',
    items: [
      {
        path: '/quick-image',
        title: '快速生图',
        desc: '上传参考图（可选）+ 描述 + 选模型，一句话出图',
        icon: markRaw(MagicStick),
        color: 'linear-gradient(135deg, #722ed1, #b37feb)',
      },
      {
        path: '/outfit',
        title: '一键穿搭展示',
        desc: '上传商品图，AI 生成模特穿搭展示',
        icon: markRaw(ShoppingBag),
        color: 'linear-gradient(135deg, #409eff, #79bbff)',
      },
      {
        path: '/model-gen',
        title: 'AI 生成模特',
        desc: '指定参数生成模特图，保存到模特库',
        icon: markRaw(Avatar),
        color: 'linear-gradient(135deg, #e6a23c, #eebe77)',
      },
      {
        path: '/seed-grass',
        title: '种草图生成',
        desc: '博主人设 + 场景，生成博主生活照',
        icon: markRaw(Picture),
        color: 'linear-gradient(135deg, #b37feb, #d3adf7)',
      },
      {
        path: '/product-image',
        title: '商品主图 / A+ 图',
        desc: '白底主图 + A+ 内容图，支持 AI 策划',
        icon: markRaw(Present),
        color: 'linear-gradient(135deg, #36cfc9, #87e8de)',
      },
    ],
  },
  {
    key: 'video',
    title: '视频',
    desc: '视频生成：单镜直出与分镜叙事',
    icon: markRaw(VideoCameraFilled),
    color: '#f56c6c',
    items: [
      {
        path: '/video',
        title: '视频生成',
        desc: '上传参考图，生成商品展示视频（支持电商/自由创作）',
        icon: markRaw(VideoCameraFilled),
        color: 'linear-gradient(135deg, #f56c6c, #fab6b6)',
      },
      {
        path: '/video-shots',
        title: '分镜视频',
        desc: 'AI 按 Hook→Detail→Recall 规划分镜，生成 4-15s 叙事视频',
        icon: markRaw(Film),
        color: 'linear-gradient(135deg, #722ed1, #9254de)',
      },
    ],
  },
  {
    key: 'research',
    title: '产品 / 市场调研',
    desc: '分析竞品 / 提取素材 / 理解内容，辅助决策',
    icon: markRaw(TrendCharts),
    color: '#eb2f96',
    items: [
      {
        path: '/analysis',
        title: 'AI 商品分析',
        desc: '上传商品图，AI 智能分析卖点 / 关键词 / 适用场景',
        icon: markRaw(View),
        color: 'linear-gradient(135deg, #67c23a, #95d475)',
      },
      {
        path: '/video-prompt',
        title: '提示词反推',
        desc: '上传短视频，AI 反推 Sora / Seedance / HappyHorse 三种风格 prompt',
        icon: markRaw(MagicStick),
        color: 'linear-gradient(135deg, #13c2c2, #5cdbd3)',
      },
      {
        path: '/replicate',
        title: '爆品复刻',
        desc: '上传爆款视频 + 商品，AI 抽骨架 + 裂变 3 份新视频 prompt',
        icon: markRaw(TrendCharts),
        color: 'linear-gradient(135deg, #eb2f96, #ff85c0)',
      },
      {
        path: '/tiktok-script',
        title: 'TikTok 脚本提取',
        desc: '粘贴 TikTok 链接，AI 批量转写为 SRT 字幕',
        icon: markRaw(DocumentCopy),
        color: 'linear-gradient(135deg, #fa8c16, #ffc069)',
      },
      {
        path: '/outfit-scrape',
        title: '穿搭素材抓取',
        desc: '粘贴视频链接或上传视频，自动抽关键帧作为参考图',
        icon: markRaw(PictureFilled),
        color: 'linear-gradient(135deg, #08979c, #36cfc9)',
      },
    ],
  },
  {
    key: 'history',
    title: '历史记录',
    desc: '查看已生成的图片 / 视频素材',
    icon: markRaw(Clock),
    color: '#909399',
    items: [
      {
        path: '/history',
        title: '生成历史',
        desc: '所有图片生成记录（含过期元数据 90 天内保留）',
        icon: markRaw(Clock),
        color: 'linear-gradient(135deg, #909399, #c8c9cc)',
      },
      {
        path: '/video-history',
        title: '视频历史',
        desc: '所有视频生成记录 + 首帧预览',
        icon: markRaw(VideoCameraFilled),
        color: 'linear-gradient(135deg, #606266, #909399)',
      },
    ],
  },
  {
    key: 'asset',
    title: '素材资产库',
    desc: '标签维护 + 素材沉淀池，方便检索复用',
    icon: markRaw(Files),
    color: '#faad14',
    soon: true,
    items: [],
  },
  {
    key: 'tracking',
    title: '素材应用及数据跟踪',
    desc: '店铺 / 链接 / 状态 / 效果追踪，量化素材价值',
    icon: markRaw(DataAnalysis),
    color: '#52c41a',
    soon: true,
    items: [],
  },
]
</script>

<style scoped>
.home {
  max-width: 1100px;
}

.home-header {
  margin-bottom: 24px;
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

/* AI 助手置顶 banner */
.agent-banner {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 22px 24px;
  background: linear-gradient(135deg, #6c5ce7 0%, #8e7bff 100%);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  margin-bottom: 32px;
  color: #fff;
  position: relative;
  overflow: hidden;
}

.agent-banner:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(108, 92, 231, 0.35);
}

.agent-banner-icon {
  width: 60px;
  height: 60px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  backdrop-filter: blur(8px);
}

.agent-banner-body {
  flex: 1;
}

.agent-banner-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
}

.agent-banner-body p {
  font-size: 13px;
  opacity: 0.92;
  line-height: 1.5;
  margin: 0;
}

.agent-banner-arrow {
  font-size: 22px;
  opacity: 0.7;
  transition: transform 0.3s;
}

.agent-banner:hover .agent-banner-arrow {
  transform: translateX(4px);
  opacity: 1;
}

/* 分区 */
.section {
  margin-bottom: 32px;
}

.section-header {
  margin-bottom: 14px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-desc {
  margin: 4px 0 0 26px;
  font-size: 13px;
  color: var(--text-secondary);
}

.section-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.section-grid.single {
  grid-template-columns: 1fr;
}

.nav-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.nav-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border-color: #409eff;
}

html.dark .nav-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.nav-card-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-card-body h4 {
  margin: 0 0 2px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.nav-card-body p {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* 即将上线占位 */
.coming-soon {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 22px 16px;
  background: var(--el-fill-color-light);
  border: 1px dashed var(--border-color);
  border-radius: 12px;
  color: var(--text-secondary);
  font-size: 13px;
}

@media (max-width: 900px) {
  .section-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .section-grid {
    grid-template-columns: 1fr;
  }
}
</style>
