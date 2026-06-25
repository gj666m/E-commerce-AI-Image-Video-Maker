<template>
  <div class="chat-input">
    <!-- 已上传参考图预览 -->
    <div v-if="refs.length" class="refs-row">
      <div v-for="r in refs" :key="r.image_id" class="ref-chip">
        <img v-if="r.thumb_url" :src="r.thumb_url" class="ref-thumb" :alt="r.filename" />
        <el-icon v-else><Picture /></el-icon>
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

      <!-- 比例下拉（表单式快捷控件） -->
      <el-select
        v-model="aspectRatio"
        size="default"
        class="ratio-select"
        :disabled="loading"
        title="画面比例"
      >
        <el-option v-for="r in ASPECT_RATIOS" :key="r.value" :label="r.label" :value="r.value" />
      </el-select>

      <!-- 模型下拉（表单式快捷控件） -->
      <el-select
        v-model="modelName"
        size="default"
        class="model-select"
        :disabled="loading"
        :placeholder="modelsLoading ? '加载模型…' : '自动路由'"
        title="生图模型（留空=自动）"
      >
        <el-option label="自动路由" :value="''" />
        <el-option
          v-for="m in availableModels"
          :key="m.name"
          :label="`${m.display_name} (${m.name})`"
          :value="m.name"
        />
      </el-select>

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
import { ref, onMounted } from 'vue'
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

interface ModelOption {
  name: string
  display_name: string
  available: boolean
}

const ASPECT_RATIOS = [
  { value: '1:1', label: '1:1 方' },
  { value: '3:4', label: '3:4 竖' },
  { value: '4:3', label: '4:3 横' },
  { value: '4:5', label: '4:5 竖' },
  { value: '9:16', label: '9:16 短视频' },
  { value: '16:9', label: '16:9 横' },
  { value: '61:25', label: '61:25 A+ Banner' },
]

const text = ref('')
const uploading = ref(false)
const aspectRatio = ref('1:1')
const modelName = ref('')
const availableModels = ref<ModelOption[]>([])
const modelsLoading = ref(false)

async function loadModels() {
  modelsLoading.value = true
  try {
    const token = localStorage.getItem('ai-zw-token')
    const resp = await fetch('/api/models', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!resp.ok) return
    const data = await resp.json()
    availableModels.value = (data.models || [])
      .filter((m: any) => m.name !== 'mock' && m.available)
      .map((m: any) => ({ name: m.name, display_name: m.display_name, available: !!m.available }))
  } catch {
    /* 静默失败，下拉显示"自动路由" */
  } finally {
    modelsLoading.value = false
  }
}

function onSend() {
  const raw = text.value.trim()
  if (!raw || props.loading) return
  // 把用户选择以中性前缀注入 prompt（不强制覆盖 Claude 判断，仅作提示）
  const parts: string[] = []
  if (aspectRatio.value && aspectRatio.value !== '1:1') {
    parts.push(`[画面比例: ${aspectRatio.value}]`)
  }
  if (modelName.value) {
    parts.push(`[指定模型: ${modelName.value}]`)
  }
  const composed = parts.length ? `${parts.join(' ')} ${raw}` : raw
  emit('send', composed)
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

onMounted(loadModels)
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
  max-width: 200px;
}
.ref-thumb {
  width: 28px;
  height: 28px;
  object-fit: cover;
  border-radius: 8px;
  flex-shrink: 0;
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
.ratio-select {
  width: 110px;
  flex-shrink: 0;
}
.model-select {
  width: 170px;
  flex-shrink: 0;
}
</style>
