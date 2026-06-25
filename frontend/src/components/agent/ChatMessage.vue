<template>
  <div class="chat-message" :class="msg.role">
    <div class="avatar" :class="msg.role">
      <el-icon v-if="msg.role === 'user'"><User /></el-icon>
      <span v-else class="brand-mark">AI</span>
    </div>
    <div class="bubble">
      <!-- 文本内容（markdown 渲染） -->
      <div v-if="msg.content" class="content markdown-body" v-html="renderedContent"></div>

      <!-- 工具步骤 -->
      <div v-for="step in msg.toolSteps" :key="step.id" class="tool-step">
        <div class="tool-head" @click="toggle(step.id)">
          <el-icon class="tool-icon" :class="step.status">
            <Loading v-if="step.status === 'running'" />
            <CircleCheckFilled v-else-if="step.status === 'done'" />
            <CircleCloseFilled v-else />
          </el-icon>
          <span class="tool-name">{{ toolLabel(step.tool) }}</span>
          <span v-if="step.status === 'running'" class="tool-status">{{ runningHint(step) }}</span>
          <el-icon class="toggle"><ArrowDown :class="{ open: openSet.has(step.id) }" /></el-icon>
        </div>
        <div v-if="openSet.has(step.id)" class="tool-body">
          <div v-if="Object.keys(step.args).length" class="tool-args">
            <span class="lbl">参数：</span>
            <code>{{ formatArgs(step.args) }}</code>
          </div>
          <div v-if="step.result" class="tool-result">
            <span class="lbl">结果：</span>
            <span class="result-text">{{ step.result }}</span>
          </div>
        </div>
      </div>

      <!-- 生成图 -->
      <div v-if="msg.images.length" class="images">
        <div v-for="img in msg.images" :key="img.image_id" class="img-card">
          <img :src="img.data_url" :alt="img.prompt_used" loading="lazy" />
          <div class="img-meta">
            <span class="model-tag">{{ img.model_used }}</span>
            <span class="cost">{{ img.cost.toFixed(4) }} {{ img.currency }}/张</span>
          </div>
          <div class="img-actions">
            <el-button size="small" :icon="Download" @click="download(img)" title="下载">下载</el-button>
          </div>
        </div>
      </div>

      <!-- 质检状态 -->
      <div v-if="msg.qcStatus" class="qc-status" :class="msg.qcStatus.state">
        <template v-if="msg.qcStatus.state === 'checking'">
          <el-icon class="qc-spin"><Loading /></el-icon>
          <span>视觉质检中…（第 {{ msg.qcStatus.retry + 1 }} 次）</span>
        </template>
        <template v-else-if="msg.qcStatus.state === 'passed'">
          <el-icon class="qc-pass"><CircleCheckFilled /></el-icon>
          <span>质检通过 · {{ msg.qcStatus.score }} 分</span>
        </template>
        <template v-else-if="msg.qcStatus.state === 'retry'">
          <el-icon class="qc-retry"><WarningFilled /></el-icon>
          <span>质检未通过 · {{ msg.qcStatus.score }} 分（第 {{ msg.qcStatus.retry }} 次重试中）</span>
          <div v-if="msg.qcStatus.issues?.length" class="qc-issues">
            <span v-for="(iss, i) in msg.qcStatus.issues" :key="i" class="qc-issue">· {{ iss }}</span>
          </div>
          <div v-if="msg.qcStatus.suggestions" class="qc-sugg">修正：{{ msg.qcStatus.suggestions }}</div>
        </template>
        <template v-else-if="msg.qcStatus.state === 'error'">
          <el-icon class="qc-retry"><WarningFilled /></el-icon>
          <span>质检服务异常（已跳过）：{{ msg.qcStatus.message }}</span>
        </template>
      </div>

      <!-- loading 占位（有 token 但内容为空时不显示） -->
      <div v-if="msg.pending && !msg.content && !msg.toolSteps.length && !msg.images.length" class="thinking">
        <el-icon class="thinking-dot"><Loading /></el-icon>
        <span>思考中…</span>
      </div>

      <!-- 错误 -->
      <div v-if="msg.error" class="error">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ msg.error }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import {
  User, Loading, CircleCheckFilled, CircleCloseFilled,
  ArrowDown, Download, WarningFilled,
} from '@element-plus/icons-vue'
import type { ChatMessage, ToolStep } from '../../types/agent'
import { renderMarkdown } from '../../utils/markdown'

const props = defineProps<{ msg: ChatMessage }>()

const renderedContent = computed(() => renderMarkdown(props.msg.content || ''))

const openSet = ref<Set<string>>(new Set())

// 本消息存在 running 工具步骤时，每秒 tick 一次刷新"已等待 Xs"
const now = ref(Date.now())
let timer: ReturnType<typeof setInterval> | null = null
const hasRunning = computed(() => props.msg.toolSteps.some((s) => s.status === 'running'))
watch(hasRunning, (v) => { v ? startTimer() : stopTimer() }, { immediate: true })
onUnmounted(() => stopTimer())
function startTimer() {
  if (timer) return
  timer = setInterval(() => { now.value = Date.now() }, 1000)
}
function stopTimer() {
  if (timer) { clearInterval(timer); timer = null }
}

function toggle(id: string) {
  if (openSet.value.has(id)) openSet.value.delete(id)
  else openSet.value.add(id)
  openSet.value = new Set(openSet.value)
}

const TOOL_LABELS: Record<string, string> = {
  generate_quick_image: '生成图片',
  list_available_models: '查询可用模型',
}

function toolLabel(tool: string) {
  return TOOL_LABELS[tool] || tool
}

function runningHint(step: ToolStep): string {
  const elapsed = step.started_at ? Math.max(0, Math.floor((now.value - step.started_at) / 1000)) : 0
  if (step.tool === 'generate_quick_image') {
    return `正在生成图片… 通常 30-60s（已等待 ${elapsed}s）`
  }
  if (step.tool === 'list_available_models') {
    return `正在查询可用模型…（已等待 ${elapsed}s）`
  }
  return `执行中…（已等待 ${elapsed}s）`
}

function formatArgs(args: Record<string, unknown>): string {
  const parts: string[] = []
  if (args.description) parts.push(`描述: ${args.description}`)
  if (args.aspect_ratio) parts.push(`比例: ${args.aspect_ratio}`)
  if (args.model_name) parts.push(`模型: ${args.model_name}`)
  if (args.reference_image_ids && (args.reference_image_ids as string[]).length) parts.push(`参考图: ${(args.reference_image_ids as string[]).length} 张`)
  return parts.join('；') || JSON.stringify(args)
}

function download(img: { data_url: string; model_used: string }) {
  const a = document.createElement('a')
  a.href = img.data_url
  a.download = `agent_${img.model_used}_${Date.now()}.jpg`
  a.click()
}
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
}
.chat-message.user {
  flex-direction: row-reverse;
}
.avatar {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.avatar.user {
  background: linear-gradient(135deg, #67c23a, #4e9f2e);
}
.avatar.assistant {
  background: linear-gradient(135deg, #6c5ce7, #8e7bff);
}
.avatar .brand-mark {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.bubble {
  max-width: 78%;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 14px;
  padding: 10px 14px;
  word-break: break-word;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}
.chat-message.user .bubble {
  background: linear-gradient(135deg, #ecf5ff, #e0efff);
  border-color: #c6e2ff;
}
.chat-message.assistant .bubble {
  background: var(--el-bg-color);
}
.content {
  line-height: 1.65;
  font-size: 14px;
}
.tool-step {
  margin: 8px 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-bg-color);
}
.tool-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  cursor: pointer;
  font-size: 13px;
  user-select: none;
}
.tool-icon.running { color: var(--el-color-primary); animation: spin 1s linear infinite; }
.tool-icon.done { color: var(--el-color-success); }
.tool-icon.error { color: var(--el-color-danger); }
.tool-name { font-weight: 500; }
.tool-status { color: var(--el-text-color-secondary); font-size: 12px; }
.toggle { margin-left: auto; transition: transform 0.2s; }
.toggle .open, .toggle :deep(.open) { transform: rotate(180deg); }
.tool-body {
  padding: 8px 10px;
  border-top: 1px solid var(--el-border-color-lighter);
  font-size: 12px;
  color: var(--el-text-color-regular);
}
.tool-args, .tool-result { margin: 2px 0; }
.lbl { color: var(--el-text-color-secondary); margin-right: 4px; }
.tool-args code { background: var(--el-fill-color-light); padding: 1px 4px; border-radius: 3px; }
.result-text { word-break: break-word; }
.images {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}
.img-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-bg-color);
  width: 220px;
}
.img-card img {
  width: 100%;
  display: block;
  cursor: zoom-in;
}
.img-meta {
  display: flex;
  justify-content: space-between;
  padding: 6px 8px;
  font-size: 12px;
}
.model-tag {
  background: var(--el-color-primary-light-8);
  color: var(--el-color-primary);
  padding: 1px 6px;
  border-radius: 8px;
}
.cost { color: var(--el-text-color-secondary); }
.img-actions { padding: 0 8px 8px; }
.thinking {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.thinking-dot { animation: spin 1s linear infinite; }
.error {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--el-color-danger);
  font-size: 13px;
  margin-top: 6px;
}
.qc-status {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px;
  border: 1px solid var(--el-border-color-lighter);
}
.qc-status.checking { background: var(--el-color-primary-light-9); color: var(--el-color-primary); }
.qc-status.passed { background: var(--el-color-success-light-9); color: var(--el-color-success); }
.qc-status.retry { background: var(--el-color-warning-light-9); color: var(--el-color-warning); flex-direction: column; align-items: flex-start; }
.qc-status.error { background: var(--el-fill-color-light); color: var(--el-text-color-secondary); }
.qc-spin { animation: spin 1s linear infinite; }
.qc-issues { display: flex; flex-direction: column; gap: 2px; width: 100%; }
.qc-issue { color: var(--el-color-danger); }
.qc-sugg { color: var(--el-text-color-regular); }
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* markdown 渲染排版（v-html 内容需用 :deep 穿透 scoped） */
.content.markdown-body :deep(p) {
  margin: 6px 0;
}
.content.markdown-body :deep(p:first-child) { margin-top: 0; }
.content.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.content.markdown-body :deep(h1),
.content.markdown-body :deep(h2),
.content.markdown-body :deep(h3),
.content.markdown-body :deep(h4) {
  margin: 12px 0 6px;
  font-weight: 600;
  line-height: 1.4;
}
.content.markdown-body :deep(h1) { font-size: 18px; }
.content.markdown-body :deep(h2) { font-size: 16px; }
.content.markdown-body :deep(h3) { font-size: 15px; }
.content.markdown-body :deep(h4) { font-size: 14px; }
.content.markdown-body :deep(ul),
.content.markdown-body :deep(ol) {
  margin: 6px 0;
  padding-left: 22px;
}
.content.markdown-body :deep(li) { margin: 2px 0; }
.content.markdown-body :deep(strong) { font-weight: 600; }
.content.markdown-body :deep(em) { font-style: italic; }
.content.markdown-body :deep(blockquote) {
  margin: 6px 0;
  padding: 4px 12px;
  border-left: 3px solid var(--el-color-primary-light-5);
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  border-radius: 0 6px 6px 0;
}
.content.markdown-body :deep(a) {
  color: var(--el-color-primary);
  text-decoration: none;
}
.content.markdown-body :deep(a:hover) { text-decoration: underline; }
.content.markdown-body :deep(.code-block) {
  margin: 6px 0;
  padding: 10px 12px;
  background: #1e1e2e;
  color: #cdd6f4;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 12.5px;
  line-height: 1.5;
  font-family: 'JetBrains Mono', 'Fira Code', Menlo, Consolas, monospace;
}
.content.markdown-body :deep(code:not(.hljs)) {
  background: var(--el-fill-color-dark);
  color: var(--el-color-danger);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'JetBrains Mono', Menlo, Consolas, monospace;
}
.content.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 6px 0;
  font-size: 13px;
}
.content.markdown-body :deep(th),
.content.markdown-body :deep(td) {
  border: 1px solid var(--el-border-color);
  padding: 4px 8px;
}
.content.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--el-border-color-lighter);
  margin: 10px 0;
}
</style>
