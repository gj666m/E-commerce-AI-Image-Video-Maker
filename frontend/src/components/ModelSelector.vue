<template>
  <div class="model-selector">
    <el-select
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      placeholder="选择模型"
      style="width: 100%"
    >
      <el-option
        v-for="model in models"
        :key="model.name"
        :label="model.display_name"
        :value="model.name"
        :disabled="!model.available"
      >
        <div class="option-content">
          <span class="option-name">{{ model.display_name }}</span>
          <span class="option-tags">
            <el-tag
              v-for="cap in model.capabilities"
              :key="cap"
              size="small"
              type="info"
            >
              {{ capLabel(cap) }}
            </el-tag>
          </span>
        </div>
        <div class="option-desc">{{ model.description }}</div>
      </el-option>
    </el-select>
  </div>
</template>

<script setup lang="ts">
import type { ModelInfo } from '../types'

defineProps<{
  models: ModelInfo[]
  modelValue: string
}>()

defineEmits<{
  'update:modelValue': [value: string]
}>()

function capLabel(cap: string): string {
  const map: Record<string, string> = {
    text_to_image: '文生图',
    image_to_image: '图生图',
    text_to_video: '文生视频',
    image_to_video: '图生视频',
  }
  return map[cap] || cap
}
</script>

<style scoped>
.option-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.option-name {
  font-weight: 500;
}

.option-tags {
  display: flex;
  gap: 4px;
}

.option-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}
</style>
