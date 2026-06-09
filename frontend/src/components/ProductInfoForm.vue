<template>
  <el-collapse v-model="expanded" class="product-info-form">
    <el-collapse-item name="info">
      <template #title>
        <span class="collapse-title">商品信息（可选）</span>
        <el-button
          :loading="analyzing"
          :disabled="!image"
          size="small"
          plain
          style="margin-left: 12px"
          @click.stop="handleAnalyze"
        >
          {{ analyzing ? 'AI 分析中...' : 'AI 智能分析' }}
        </el-button>
        <el-tooltip v-if="!image" content="请先上传商品图" placement="top">
          <el-icon style="margin-left: 4px; color: #909399"><InfoFilled /></el-icon>
        </el-tooltip>
      </template>

      <el-input
        :model-value="modelValue"
        @update:model-value="emit('update:modelValue', $event)"
        type="textarea"
        :rows="8"
        placeholder="可自由输入商品信息，或粘贴亚马逊五点描述 / listing 内容。&#10;也可以点击「AI 智能分析」自动识别商品图生成。"
      />
    </el-collapse-item>
  </el-collapse>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import { analyzeProduct } from '../api'

const props = defineProps<{
  image: File | null
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const expanded = ref<string[]>([])
const analyzing = ref(false)

async function handleAnalyze() {
  if (!props.image) return

  analyzing.value = true
  try {
    // 如果用户已经输入了内容，传给 AI 作为参考去优化补全
    const existingText = props.modelValue.trim()
    const resp = await analyzeProduct(
      props.image,
      existingText || undefined,
    )

    const a = resp.analysis
    // 按 LinkFox 框架格式化成可读文本
    const lines: string[] = []

    if (a.category || a.style) {
      lines.push(`【基础档案】`)
      lines.push(`款式品类：${a.category || ''}${a.style ? '，' + a.style : ''}`)
    }
    if (a.fabric || a.color || a.pattern) {
      lines.push(`面料：${a.fabric || '未识别'}，颜色：${a.color || '未识别'}，图案：${a.pattern || '纯色'}`)
    }
    if (a.details) {
      lines.push(`工艺细节：${a.details}`)
    }
    if (a.selling_points?.length) {
      lines.push(``)
      lines.push(`【核心卖点】`)
      a.selling_points.forEach((p, i) => lines.push(`${i + 1}. ${p}`))
    }
    if (a.suitable_scenes?.length) {
      lines.push(``)
      lines.push(`【适用场景】`)
      a.suitable_scenes.forEach(s => lines.push(`- ${s}`))
    }
    if (a.target_audience || a.season) {
      lines.push(``)
      if (a.target_audience) lines.push(`目标受众：${a.target_audience}`)
      if (a.season) lines.push(`适合季节：${a.season}`)
    }
    if (a.keywords?.length) {
      lines.push(``)
      lines.push(`关键词：${a.keywords.join('、')}`)
    }

    const result = lines.join('\n')
    emit('update:modelValue', result)

    // 展开面板让用户看到结果
    if (!expanded.value.includes('info')) {
      expanded.value = ['info']
    }
    ElMessage.success('AI 分析完成')
  } catch {
    ElMessage.error('AI 分析失败，请稍后重试')
  } finally {
    analyzing.value = false
  }
}
</script>

<style scoped>
.product-info-form {
  margin: 8px 0;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  overflow: hidden;
}

.collapse-title {
  font-weight: 500;
  color: var(--text-primary);
}
</style>
