<template>
  <div class="chat-input">
    <!-- 已上传参考图预览 -->
    <div v-if="refs.length" class="refs-row">
      <div v-for="r in refs" :key="r.image_id" class="ref-chip">
        <el-icon><Picture /></el-icon>
        <span class="ref-name" :title="r.filename">{{ r.filename }}</span>
        <el-icon class="ref-remove" @click="$emit('remove-ref', r.image_id)"><Close /></el-icon>
      </div>
    </div>

    <div class="input-row">
      <el-upload
        :show-file-list="false"
        :multiple="true"
        :auto-upload="true"
        :http-request="handleUpload"
        accept="image/*"
        :disabled="uploading || loading"
      >
        <el-button :icon="Picture" circle :loading="uploading" :disabled="loading" title="上传参考图（可选）" />
      </el-upload>

      <el-input
        v-model="text"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 5 }"
        placeholder="描述你想生成的图片，或问任何电商视觉创作问题…（Enter 发送，Shift+Enter 换行）"
        resize="none"
        :disabled="loading"
        @keydown.enter.exact.prevent="onSend"
      />

      <el-button
        v-if="!loading"
        type="primary"
        :icon="Promotion"
        :disabled="!text.trim()"
        @click="onSend"
      >发送</el-button>
      <el-button v-else type="danger" :icon="VideoPause" @click="$emit('stop')">停止</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Picture, Close, Promotion, VideoPause } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { UploadedRef } from '../../types/agent'
import type { UploadRequestOptions } from 'element-plus'

const props = defineProps<{
  refs: UploadedRef[]
  loading: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
  stop: []
  upload: [files: File[]]
  'remove-ref': [imageId: string]
}>()

const text = ref('')
const uploading = ref(false)

function onSend() {
  const t = text.value.trim()
  if (!t || props.loading) return
  emit('send', t)
  text.value = ''
}

async function handleUpload(opt: UploadRequestOptions) {
  const files: File[] = []
  // element-plus http-request 单文件回调；多选时会逐个回调
  if (opt.file) files.push(opt.file)
  if (!files.length) return
  uploading.value = true
  try {
    emit('upload', files)
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.chat-input {
  border-top: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
  padding: 12px 16px;
}
.refs-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.ref-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 12px;
  max-width: 160px;
}
.ref-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ref-remove {
  cursor: pointer;
  color: var(--el-color-danger);
  flex-shrink: 0;
}
.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.input-row :deep(.el-textarea__inner) {
  min-width: 0;
}
</style>
