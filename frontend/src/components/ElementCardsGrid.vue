<!-- 要素卡片网格：8 字段 v-model 双列布局（续15 工坊结构化模式） -->
<template>
  <div class="element-cards-grid">
    <div class="card-header">
      <span class="header-title">结构化要素</span>
      <span class="header-hint">改字段后下方 prompt 实时本地拼装</span>
    </div>
    <el-row :gutter="10">
      <el-col v-for="f in fields" :key="f.key" :xs="24" :sm="12">
        <div class="field-card" :class="{ disabled }">
          <span class="field-tag" :style="{ background: tagColor(f.key) }">{{ f.label }}</span>
          <el-input
            :model-value="modelValue[f.key]"
            type="textarea"
            :rows="2"
            :placeholder="placeholder(f.key)"
            :disabled="disabled"
            resize="none"
            @update:model-value="onUpdate(f.key, $event)"
          />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import type { PromptElements } from '../types'
import { ELEMENT_FIELDS } from '../utils/promptAssembly'

const props = defineProps<{
  modelValue: PromptElements
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: PromptElements): void
}>()

const fields = ELEMENT_FIELDS

const TAG_COLORS: Record<string, string> = {
  subject: '#409eff',
  clothing: '#ec6b87',
  scene: '#67c23a',
  lighting: '#e6a23c',
  lens: '#909399',
  rhythm: '#9c27b0',
  composition: '#00bcd4',
  style_keywords: '#795548',
}

function tagColor(key: string): string {
  return TAG_COLORS[key] || '#909399'
}

const PLACEHOLDERS: Record<string, string> = {
  subject: '人物主体或商品核心特征',
  clothing: '款式 / 面料 / 颜色',
  scene: '具体场景环境',
  lighting: '光线方向 / 色温 / 硬度',
  lens: '镜头焦段 / 景别 / 光圈',
  rhythm: '节奏氛围',
  composition: '构图 / 机位 / 姿势',
  style_keywords: '风格关键词（逗号分隔）',
}

function placeholder(key: string): string {
  return PLACEHOLDERS[key] || ''
}

function onUpdate(key: keyof PromptElements, value: string) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}
</script>

<style scoped>
.element-cards-grid {
  width: 100%;
}
.card-header {
  display: flex; align-items: baseline; gap: 10px;
  margin-bottom: 8px;
}
.header-title {
  font-weight: 600; font-size: 14px; color: #303133;
}
.header-hint {
  font-size: 12px; color: #909399;
}
.field-card {
  margin-bottom: 8px;
  display: flex; align-items: flex-start;
  gap: 6px;
}
.field-card.disabled { opacity: 0.6; }
.field-tag {
  flex-shrink: 0;
  display: inline-block;
  margin-top: 6px;
  padding: 2px 8px;
  border-radius: 10px;
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  width: 36px;
  text-align: center;
}
.field-card :deep(.el-textarea__inner) {
  font-size: 13px;
  line-height: 1.5;
  padding: 6px 10px;
}
</style>
