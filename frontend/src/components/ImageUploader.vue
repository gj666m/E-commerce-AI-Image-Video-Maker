<template>
  <div class="image-uploader">
    <el-upload
      :auto-upload="false"
      :show-file-list="false"
      :on-change="handleChange"
      accept=".jpg,.jpeg,.png,.webp"
      drag
    >
      <div v-if="previewUrl" class="preview-area">
        <img :src="previewUrl" alt="预览" />
        <div class="preview-overlay">点击或拖拽更换图片</div>
      </div>
      <div v-else class="upload-placeholder">
        <el-icon :size="48"><UploadFilled /></el-icon>
        <p>拖拽图片到此处，或点击上传</p>
        <p class="tip">支持 JPG/PNG/WEBP，最大 20MB</p>
      </div>
    </el-upload>
    <el-button
      v-if="previewUrl"
      type="danger"
      text
      size="small"
      class="clear-btn"
      @click="handleClear"
    >
      清除图片
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'

const props = defineProps<{
  modelValue?: File | null
}>()

const emit = defineEmits<{
  'update:modelValue': [file: File | null]
}>()

const previewUrl = ref<string | null>(null)

watch(
  () => props.modelValue,
  (file) => {
    if (file) {
      previewUrl.value = URL.createObjectURL(file)
    } else {
      previewUrl.value = null
    }
  },
)

function handleChange(uploadFile: UploadFile) {
  const file = uploadFile.raw
  if (!file) return

  // 格式校验
  const validTypes = ['image/jpeg', 'image/png', 'image/webp']
  if (!validTypes.includes(file.type)) {
    ElMessage.error('仅支持 JPG/PNG/WEBP 格式')
    return
  }

  // 大小校验
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 20MB')
    return
  }

  emit('update:modelValue', file)
}

function handleClear() {
  emit('update:modelValue', null)
  previewUrl.value = null
}
</script>

<style scoped>
.image-uploader {
  position: relative;
}

.image-uploader :deep(.el-upload) {
  width: 100%;
}

.image-uploader :deep(.el-upload-dragger) {
  width: 100%;
  padding: 20px;
}

.preview-area {
  position: relative;
  max-height: 300px;
}

.preview-area img {
  max-width: 100%;
  max-height: 280px;
  object-fit: contain;
  border-radius: 4px;
}

.preview-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  text-align: center;
  font-size: 13px;
  border-radius: 0 0 4px 4px;
}

.upload-placeholder {
  text-align: center;
  color: #909399;
  padding: 20px 0;
}

.upload-placeholder .tip {
  font-size: 12px;
  color: #c0c4cc;
}

.clear-btn {
  margin-top: 4px;
}
</style>
