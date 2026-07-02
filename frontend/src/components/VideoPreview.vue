<template>
  <div class="video-preview" v-if="videoUrl">
    <h4>生成结果</h4>
    <div class="video-container">
      <video
        :src="fileUrl(videoUrl)"
        controls
        loop
        class="video-player"
      />
    </div>
    <div class="actions">
      <el-button type="primary" @click="download">
        下载视频
      </el-button>
    </div>
    <div class="meta-info">
      <el-tag size="small">模型: {{ modelUsed }}</el-tag>
      <el-tag size="small" type="info">费用: {{ currency }}{{ cost.toFixed(4) }}</el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { fileUrl } from '../utils/fileUrl'

const props = defineProps<{
  videoUrl: string
  modelUsed: string
  cost: number
  currency?: string
}>()

function download() {
  const link = document.createElement('a')
  link.href = fileUrl(props.videoUrl)
  // 从 URL 提取文件名
  const filename = props.videoUrl.split('/').pop() || 'video.mp4'
  link.download = filename
  link.click()
}
</script>

<style scoped>
.video-preview {
  margin-top: 20px;
}

.video-preview h4 {
  margin-bottom: 12px;
  color: #303133;
}

.video-container {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
  background: #000;
}

.video-player {
  width: 100%;
  max-height: 400px;
  display: block;
}

.actions {
  margin-top: 12px;
}

.meta-info {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
</style>
