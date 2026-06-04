<template>
  <div class="home">
    <el-card>
      <template #header>
        <h2>AI 电商图像视频生成工具</h2>
      </template>

      <el-descriptions title="系统状态" :column="1" border>
        <el-descriptions-item label="状态">
          <el-tag :type="status === 'ok' ? 'success' : 'danger'">
            {{ status === 'ok' ? '正常运行' : '异常' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="模式">
          <el-tag :type="mockMode ? 'warning' : 'primary'">
            {{ mockMode ? 'Mock 模式（未配置 API Key）' : '生产模式' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <h3>功能入口</h3>
      <div class="nav-grid">
        <el-card shadow="hover" class="nav-card" @click="$router.push('/outfit')">
          <el-icon :size="32"><ShoppingBag /></el-icon>
          <h4>一键穿搭展示</h4>
          <p>上传商品图 → 模特穿搭展示图</p>
        </el-card>
        <el-card shadow="hover" class="nav-card" @click="$router.push('/analysis')">
          <el-icon :size="32"><View /></el-icon>
          <h4>AI 商品分析</h4>
          <p>上传商品图 → AI 智能分析卖点与关键词</p>
        </el-card>
        <el-card shadow="hover" class="nav-card" @click="$router.push('/model-gen')">
          <el-icon :size="32"><Avatar /></el-icon>
          <h4>AI 生成模特</h4>
          <p>指定参数 → AI 生成模特图 → 保存到模特库</p>
        </el-card>
        <el-card shadow="hover" class="nav-card" @click="$router.push('/video')">
          <el-icon :size="32"><VideoCameraFilled /></el-icon>
          <h4>视频生成</h4>
          <p>上传参考图 + 视频描述 → 生成商品视频</p>
        </el-card>
        <el-card shadow="hover" class="nav-card" @click="$router.push('/seed-grass')">
          <el-icon :size="32"><Picture /></el-icon>
          <h4>种草图生成</h4>
          <p>博主人设 + 场景 → AI 生成博主生活照</p>
        </el-card>
        <el-card shadow="hover" class="nav-card" @click="$router.push('/product-image')">
          <el-icon :size="32"><Present /></el-icon>
          <h4>商品主图 / A+ 图</h4>
          <p>白底主图 + A+ 内容图，支持 AI 策划</p>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { VideoCameraFilled, Avatar, ShoppingBag, View, Picture, Present } from '@element-plus/icons-vue'
import { healthCheck } from '../api'

const status = ref('loading')
const mockMode = ref(false)

onMounted(async () => {
  try {
    const data = await healthCheck()
    status.value = data.status
    mockMode.value = data.mock_mode
  } catch {
    status.value = 'error'
  }
})
</script>

<style scoped>
.home {
  max-width: 800px;
  margin: 40px auto;
  padding: 0 20px;
}

.nav-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.nav-card {
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s;
}

.nav-card:hover {
  transform: translateY(-2px);
}

.nav-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.nav-card h4 {
  margin: 8px 0 4px;
}

.nav-card p {
  font-size: 13px;
  color: #909399;
  margin: 0;
}
</style>
