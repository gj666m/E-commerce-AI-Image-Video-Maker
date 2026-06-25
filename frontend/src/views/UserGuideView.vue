<template>
  <div class="guide-view">
    <!-- Hero -->
    <div class="guide-hero">
      <div class="hero-icon gradient-purple">
        <el-icon :size="32"><Reading /></el-icon>
      </div>
      <div class="hero-text">
        <h1 class="hero-title">使用手册</h1>
        <p class="hero-sub">
          帮助运营快速上手各模块，附 6 条 Creatok 验证过的视频提示词示例。点击左侧目录跳转，或从各功能页右上角「？」图标直达。
        </p>
      </div>
    </div>

    <!-- 豆包专家版引导（全局顶部，黄色横幅） -->
    <el-alert type="warning" :closable="false" show-icon class="doubao-banner">
      <template #title>
        <span class="banner-title">💡 这些示例怎么来的？</span>
        <span class="banner-body">
          通过「豆包网页专家版」描述自己的需求让豆包补全生成——每日有免费额度。
          自己写卡壳时也可以用工具内右侧的「AI 优化 / 智能扩写」按钮补强。
        </span>
        <el-link type="warning" :href="doubaoUrl" target="_blank" rel="noopener" class="banner-link">
          前往豆包专家版 →
        </el-link>
      </template>
    </el-alert>

    <div class="guide-body">
      <!-- 左侧目录 sticky -->
      <aside class="guide-toc">
        <div class="toc-block">
          <div class="toc-header">模块使用说明</div>
          <a
            v-for="m in moduleGuides"
            :key="m.anchor"
            class="toc-link"
            :class="{ active: activeAnchor === m.anchor }"
            :href="`#${m.anchor}`"
            @click.prevent="scrollToAnchor(m.anchor)"
          >
            <el-icon class="toc-icon"><component :is="iconMap[m.icon]" /></el-icon>
            <span>{{ m.title }}</span>
          </a>
        </div>
        <div class="toc-block">
          <div class="toc-header">视频提示词示例</div>
          <a
            v-for="ex in videoExamples"
            :key="ex.id"
            class="toc-link"
            :class="{ active: activeAnchor === ex.id }"
            :href="`#${ex.id}`"
            @click.prevent="scrollToAnchor(ex.id)"
          >
            <span class="toc-dot">•</span>
            <span class="toc-ex-title">{{ ex.title.replace(/^示例 \d+：/, '') }}</span>
          </a>
        </div>
      </aside>

      <!-- 右侧内容 -->
      <main class="guide-content">
        <!-- 6 个模块说明 -->
        <section
          v-for="m in moduleGuides"
          :id="m.anchor"
          :key="m.anchor"
          class="guide-section module-section"
        >
          <div class="module-header">
            <span class="section-icon" :class="m.gradient">
              <el-icon :size="22"><component :is="iconMap[m.icon]" /></el-icon>
            </span>
            <div>
              <h2 class="module-title">{{ m.title }}</h2>
              <p class="module-intro">{{ m.intro }}</p>
            </div>
          </div>
          <div v-for="(s, idx) in m.sections" :key="idx" class="module-subsection">
            <h3 class="subsection-title">{{ s.subtitle }}</h3>
            <ul class="subsection-tips">
              <li v-for="(tip, i) in s.tips" :key="i">{{ tip }}</li>
            </ul>
          </div>
        </section>

        <!-- 视频提示词示例 -->
        <section id="video-examples" class="guide-section examples-section">
          <div class="module-header">
            <span class="section-icon gradient-red">
              <el-icon :size="22"><VideoCamera /></el-icon>
            </span>
            <div>
              <h2 class="module-title">Creatok 验证过的视频提示词示例</h2>
              <p class="module-intro">
                以下 6 条来自 Creatok 平台实测效果好的提示词，可复制但不必完全照搬——核心是学习其结构（时长/比例/分镜时间轴/穿搭细节/场景描述/技术参数）。
                含 <code class="inline-code">@图片N</code> 标记的示例：需上传对应参考图，用工具内的 @ 引用语法精准分工。
              </p>
            </div>
          </div>

          <div class="examples-grid">
            <GuideExampleCard
              v-for="ex in videoExamples"
              :id="ex.id"
              :key="ex.id"
              :example="ex"
            />
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import {
  Reading,
  VideoCamera,
  MagicStick,
  VideoCameraFilled,
  Film,
  Picture,
  Present,
  ChatDotSquare,
} from '@element-plus/icons-vue'
import { moduleGuides, videoExamples, doubaoUrl } from '../data/guideContent'
import GuideExampleCard from '../components/GuideExampleCard.vue'

const route = useRoute()
const activeAnchor = ref<string>('')

// 图标映射：模块 icon 字段 → 实际组件
// （用动态 component :is，需要从 icons-vue 注册）
const iconMap: Record<string, any> = {
  MagicStick,
  VideoCameraFilled,
  Film,
  Picture,
  Present,
  ChatDotSquare,
}

function scrollToAnchor(anchor: string) {
  const el = document.getElementById(anchor)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeAnchor.value = anchor
    // 同步 URL hash
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, '', `#${anchor}`)
    }
  }
}

let scrollContainer: HTMLElement | null = null

function onScroll() {
  if (!scrollContainer) return
  // 找到离顶部最近的 section
  const allAnchors = [
    ...moduleGuides.map((m) => m.anchor),
    ...videoExamples.map((e) => e.id),
  ]
  let current = ''
  for (const anchor of allAnchors) {
    const el = document.getElementById(anchor)
    if (el) {
      // scrollContainer 是 .content（main 元素），getBoundingClientRect 相对 viewport
      const rect = el.getBoundingClientRect()
      // 减去 100px 作为「顶部到达」阈值（sticky header + 一些缓冲）
      if (rect.top < 120) {
        current = anchor
      } else {
        break
      }
    }
  }
  if (current) activeAnchor.value = current
}

onMounted(async () => {
  await nextTick()
  // 查找滚动容器：MainLayout 的 .content
  scrollContainer = document.querySelector('.layout > .main > .content')
  if (scrollContainer) {
    scrollContainer.addEventListener('scroll', onScroll, { passive: true })
  }
  // 初始高亮
  if (moduleGuides.length > 0) {
    activeAnchor.value = moduleGuides[0].anchor
  }
  // 若 URL 带 hash，滚动到对应位置
  if (route.hash) {
    const anchor = route.hash.slice(1)
    await nextTick()
    setTimeout(() => {
      scrollToAnchor(anchor)
    }, 100)
  }
})

onBeforeUnmount(() => {
  if (scrollContainer) {
    scrollContainer.removeEventListener('scroll', onScroll)
    scrollContainer = null
  }
})

// 暴露 iconMap 给 template 使用（component :is 字符串 → 组件）
// 注意：template 已用 component :is，需要在 setup 返回时让它可见
// 但 Vue 3 <script setup> 默认不暴露局部变量给 template 的 component :is 字符串解析
// 解决：把 iconMap 注册到组件实例
void iconMap // 引用避免未使用告警
</script>

<style scoped>
.guide-view {
  max-width: 1400px;
  margin: 0 auto;
}

/* Hero */
.guide-hero {
  display: flex;
  gap: 16px;
  align-items: center;
  padding: 16px 4px 20px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 20px;
}

.hero-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.hero-title {
  margin: 0 0 6px;
  font-size: 26px;
  font-weight: 700;
  background: linear-gradient(135deg, #6c5ce7, #8e7bff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-sub {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

/* 豆包横幅 */
.doubao-banner {
  margin-bottom: 24px;
}

.doubao-banner :deep(.el-alert__content) {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.banner-title {
  font-weight: 600;
  font-size: 14px;
}

.banner-body {
  font-weight: 400;
  font-size: 13px;
  line-height: 1.6;
}

.banner-link {
  margin-top: 4px;
  font-size: 13px;
}

/* 双栏布局 */
.guide-body {
  display: flex;
  gap: 28px;
  align-items: flex-start;
}

.guide-toc {
  width: 220px;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  max-height: calc(100vh - 20px);
  overflow-y: auto;
  padding: 8px 0;
}

.toc-block {
  margin-bottom: 20px;
}

.toc-header {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 4px 8px;
  margin-bottom: 4px;
}

.toc-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  text-decoration: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border-left: 2px solid transparent;
}

.toc-link:hover {
  background: var(--el-fill-color-light);
  color: var(--el-color-primary);
}

.toc-link.active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border-left-color: var(--el-color-primary);
  font-weight: 500;
}

.toc-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.toc-dot {
  color: var(--el-text-color-secondary);
  font-size: 14px;
  flex-shrink: 0;
  padding-left: 4px;
}

.toc-ex-title {
  font-size: 12px;
  line-height: 1.4;
}

/* 右侧内容 */
.guide-content {
  flex: 1;
  min-width: 0;
}

.guide-section {
  padding: 20px 0 28px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  scroll-margin-top: 20px;
}

.module-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.module-title {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.module-intro {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
}

.module-subsection {
  margin: 16px 0 8px;
  padding-left: 50px;
}

.subsection-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.subsection-tips {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.8;
}

.subsection-tips li {
  margin-bottom: 4px;
}

.inline-code {
  background: var(--el-fill-color-dark);
  color: var(--el-color-primary);
  padding: 1px 6px;
  border-radius: 4px;
  font-family: 'Menlo', 'Monaco', monospace;
  font-size: 12px;
}

.examples-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.examples-grid > * {
  scroll-margin-top: 20px;
}

/* 响应式 */
@media (max-width: 900px) {
  .guide-body {
    flex-direction: column;
  }
  .guide-toc {
    position: static;
    max-height: none;
    width: 100%;
  }
  .examples-grid {
    grid-template-columns: 1fr;
  }
}
</style>
