<template>
  <div class="example-card">
    <!-- 标题栏 + 复制按钮 -->
    <div class="example-header">
      <h4 class="example-title">{{ example.title }}</h4>
      <el-button size="small" type="primary" plain @click="copyPrompt">
        <el-icon><CopyDocument /></el-icon>
        <span>{{ copied ? '已复制' : '复制 Prompt' }}</span>
      </el-button>
    </div>

    <!-- 标签 -->
    <div class="example-tags">
      <el-tag v-for="tag in example.tags" :key="tag" size="small" effect="plain" round>
        {{ tag }}
      </el-tag>
    </div>

    <!-- 适用场景 -->
    <div class="example-scenario">
      <el-icon class="scenario-icon"><InfoFilled /></el-icon>
      <span>{{ example.scenario }}</span>
    </div>

    <!-- @图片N 引用提示（仅含图引用时展示） -->
    <el-alert
      v-if="example.hasImageRef && example.imageRefHint"
      type="warning"
      :closable="false"
      show-icon
      class="ref-hint"
    >
      <template #title>
        <span class="ref-hint-label">使用前需上传参考图：</span>
        <span class="ref-hint-text">{{ example.imageRefHint }}</span>
      </template>
    </el-alert>

    <!-- Prompt 原文（可折叠） -->
    <div class="prompt-block">
      <div class="prompt-toggle" @click="expanded = !expanded">
        <el-icon class="toggle-icon" :class="{ rotated: expanded }"><ArrowRight /></el-icon>
        <span>Prompt 原文</span>
        <span class="prompt-meta">{{ expanded ? '点击收起' : '点击展开查看完整 Prompt' }}</span>
      </div>
      <div v-show="expanded" class="prompt-content">
        <pre>{{ example.rawPrompt }}</pre>
      </div>
    </div>

    <!-- 底部豆包引导 -->
    <div class="doubao-tip">
      <el-icon><MagicStick /></el-icon>
      <span>{{ doubaoTip }}</span>
      <el-link type="primary" :href="doubaoUrl" target="_blank" rel="noopener" class="doubao-link">
        前往豆包专家版 →
      </el-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, InfoFilled, ArrowRight, MagicStick } from '@element-plus/icons-vue'
import { doubaoTip, doubaoUrl, type PromptExample } from '../data/guideContent'

const props = defineProps<{ example: PromptExample }>()

const expanded = ref(false)
const copied = ref(false)

async function copyPrompt() {
  try {
    await navigator.clipboard.writeText(props.example.rawPrompt)
    copied.value = true
    ElMessage.success('Prompt 已复制到剪贴板')
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (e) {
    ElMessage.error('复制失败：浏览器不支持或权限被拒')
  }
}
</script>

<style scoped>
.example-card {
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  padding: 18px 20px;
  background: var(--el-bg-color);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.example-card:hover {
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.08);
  border-color: var(--el-color-primary-light-5);
}

.example-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.example-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.4;
  flex: 1;
}

.example-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.example-scenario {
  display: flex;
  gap: 6px;
  align-items: flex-start;
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
}

.scenario-icon {
  color: var(--el-color-info);
  margin-top: 2px;
  flex-shrink: 0;
}

.ref-hint {
  margin: 0;
}

.ref-hint-label {
  font-weight: 600;
}

.ref-hint-text {
  font-weight: 400;
}

.prompt-block {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
}

.prompt-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  background: var(--el-fill-color-light);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  transition: background 0.2s;
}

.prompt-toggle:hover {
  background: var(--el-fill-color);
}

.toggle-icon {
  transition: transform 0.2s;
  font-size: 12px;
}

.toggle-icon.rotated {
  transform: rotate(90deg);
}

.prompt-meta {
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: 400;
}

.prompt-content {
  padding: 12px 14px;
  max-height: 400px;
  overflow-y: auto;
}

.prompt-content pre {
  margin: 0;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  color: var(--el-text-color-regular);
  white-space: pre-wrap;
  word-break: break-word;
}

.doubao-tip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(255, 213, 79, 0.12), rgba(255, 167, 38, 0.08));
  border-radius: 8px;
  font-size: 12px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
}

.doubao-tip > span {
  flex: 1;
  min-width: 200px;
}

.doubao-link {
  margin-left: auto;
  font-size: 12px;
  flex-shrink: 0;
}
</style>
