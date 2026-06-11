<template>
  <div class="result-preview" v-if="images.length > 0">
    <h4>生成结果</h4>
    <div class="image-grid">
      <div v-for="(img, index) in images" :key="index" class="image-item">
        <el-image
          :src="'data:image/png;base64,' + img"
          fit="contain"
          :preview-src-list="images.map(i => 'data:image/png;base64,' + i)"
          :initial-index="index"
        />
        <div class="actions">
          <el-button type="primary" size="small" @click="download(img, index)">
            下载
          </el-button>
          <el-button size="small" @click="goVideo(img, index)">
            生成视频
          </el-button>
        </div>
      </div>
    </div>
    <div class="meta-info">
      <el-tag size="small">模型: {{ modelUsed }}</el-tag>
      <el-tag size="small" type="info">费用: {{ currency }}{{ cost.toFixed(4) }}</el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

defineProps<{
  images: string[]
  modelUsed: string
  cost: number
  currency?: string
}>()

const router = useRouter()

function download(base64Data: string, index: number) {
  const link = document.createElement('a')
  link.href = 'data:image/png;base64,' + base64Data
  link.download = `generated_${index + 1}.png`
  link.click()
}

function goVideo(base64Data: string, _index: number) {
  // 将 base64 图片存入 sessionStorage，跳转到视频页自动加载
  sessionStorage.setItem('video_ref_image', base64Data)
  router.push('/video')
}
</script>

<style scoped>
.result-preview {
  margin-top: 20px;
}

.result-preview h4 {
  margin-bottom: 12px;
  color: #303133;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.image-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.image-item .el-image {
  width: 100%;
  height: 300px;
}

.actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  justify-content: center;
}

.meta-info {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
</style>
