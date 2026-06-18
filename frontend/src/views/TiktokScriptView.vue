<template>
  <div class="tiktok-script-view">
    <!-- 标题区 -->
    <div class="page-header">
      <h1 class="page-title">TikTok 脚本提取</h1>
      <p class="page-desc">
        粘贴 TikTok 链接，AI 自动下载视频并转写成 SRT 字幕格式。支持 TikTok / Instagram / YouTube / 抖音，
        每条字幕含时间戳，可直接用作视频字幕或分析脚本结构
      </p>
    </div>

    <el-row :gutter="20" class="main-content">
      <!-- 左侧：输入区 -->
      <el-col :span="10">
        <el-card>
          <el-form label-position="top">
            <!-- 链接输入 -->
            <el-form-item label="TikTok 链接" required>
              <el-input
                v-model="rawInput"
                type="textarea"
                :rows="12"
                placeholder="粘贴 TikTok 链接，支持一条或多条&#10;每行一个，或用空格、逗号分隔"
                :disabled="processing"
              />
              <div class="link-count">
                <el-icon><Link /></el-icon>
                <span>已识别 <strong>{{ links.length }}</strong> 条链接</span>
              </div>
            </el-form-item>

            <!-- 提取按钮 -->
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="processing"
                :disabled="links.length === 0"
                @click="handleExtract"
                style="width: 100%"
              >
                {{ processing ? progressText : '提取' }}
              </el-button>
            </el-form-item>

            <!-- 中断按钮（处理中显示） -->
            <el-form-item v-if="processing">
              <el-button
                size="default"
                :icon="Close"
                @click="handleCancel"
                style="width: 100%"
              >
                中断（已提取的结果会保留）
              </el-button>
            </el-form-item>

            <!-- 说明 -->
            <div class="tips">
              <p><el-icon><InfoFilled /></el-icon> 说明</p>
              <ul>
                <li>串行处理（一条条来），稳定不触发风控</li>
                <li>每条约 30-90 秒（下载 + Gemini 视频转写）</li>
                <li>TikTok 服务器可能风控，失败的链接会标红可重试</li>
                <li>提取结果不存储，刷新页面会丢失，请及时复制</li>
              </ul>
            </div>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：结果区 -->
      <el-col :span="14">
        <el-card v-if="results.length === 0 && !processing">
          <el-empty description="粘贴链接后点击「提取」" />
        </el-card>

        <div v-else class="results-list">
          <!-- 总进度条 -->
          <el-card v-if="processing || doneCount > 0" class="progress-card">
            <div class="progress-info">
              <span>进度：{{ doneCount }} / {{ links.length }}</span>
              <span v-if="failCount > 0" class="fail-count">失败 {{ failCount }}</span>
              <el-button
                v-if="!processing && failCount > 0"
                size="small"
                type="primary"
                :icon="RefreshRight"
                @click="handleRetryFailed"
              >
                重试失败的（{{ failCount }} 条）
              </el-button>
              <el-button
                v-if="!processing && successCount > 0"
                size="small"
                :icon="CopyDocument"
                @click="copyAll"
              >
                复制全部
              </el-button>
              <el-button
                v-if="!processing && results.length > 0"
                size="small"
                text
                @click="handleClear"
              >
                清空结果
              </el-button>
            </div>
            <el-progress
              :percentage="progressPercent"
              :status="progressStatus"
              :show-text="false"
              :stroke-width="6"
            />
          </el-card>

          <!-- 结果卡片列表 -->
          <div
            v-for="(item, idx) in results"
            :key="idx"
            class="result-item"
          >
            <el-card>
              <template #header>
                <div class="item-header">
                  <div class="item-url">
                    <el-icon><Link /></el-icon>
                    <a :href="item.url" target="_blank" rel="noopener" :title="item.url">
                      {{ shortenUrl(item.url) }}
                    </a>
                  </div>
                  <div class="item-status">
                    <el-tag v-if="item.status === 'pending'" size="small" type="info">等待中</el-tag>
                    <el-tag v-else-if="item.status === 'processing'" size="small" type="warning">
                      <el-icon class="spin"><Loading /></el-icon>
                      转写中
                    </el-tag>
                    <el-tag v-else-if="item.status === 'success'" size="small" type="success">
                      成功（{{ item.script?.length || 0 }} 字）
                    </el-tag>
                    <el-tag v-else size="small" type="danger">失败</el-tag>
                  </div>
                </div>
              </template>

              <!-- 成功 -->
              <div v-if="item.status === 'success' && item.script" class="script-content">
                <pre>{{ item.script }}</pre>
                <div class="item-actions">
                  <el-button size="small" :icon="CopyDocument" @click="copyOne(item)">
                    复制
                  </el-button>
                </div>
              </div>

              <!-- 失败 -->
              <div v-else-if="item.status === 'failed'" class="error-content">
                <el-alert :title="item.error || '提取失败'" type="error" :closable="false" show-icon />
                <div class="item-actions">
                  <el-button
                    size="small"
                    type="primary"
                    :icon="RefreshRight"
                    :disabled="processing"
                    @click="handleRetryOne(idx)"
                  >
                    重试
                  </el-button>
                </div>
              </div>

              <!-- 处理中 -->
              <div v-else-if="item.status === 'processing'" class="processing-content">
                <el-icon :size="20" class="spin"><Loading /></el-icon>
                <span>下载视频 + Gemini 转写中（约 30-90 秒）...</span>
              </div>

              <!-- 等待 -->
              <div v-else class="pending-content">
                <span>排队等待中...</span>
              </div>
            </el-card>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Link,
  Close,
  Loading,
  CopyDocument,
  RefreshRight,
  InfoFilled,
} from '@element-plus/icons-vue'
import {
  extractTiktokScript,
  getErrorMessage,
  type TiktokScriptResult,
} from '../api'

type ItemStatus = 'pending' | 'processing' | 'success' | 'failed'

interface ResultItem extends TiktokScriptResult {
  status: ItemStatus
}

const rawInput = ref('')
const processing = ref(false)
const results = ref<ResultItem[]>([])
const currentIndex = ref(0)
let abortController: AbortController | null = null

// === 链接解析 ===
const URL_REGEX = /https?:\/\/[^\s,，]+/g

const links = computed(() => {
  const text = rawInput.value.trim()
  if (!text) return []
  const matches = text.match(URL_REGEX)
  return matches ? Array.from(new Set(matches)) : [] // 去重
})

// === 进度 ===
const doneCount = computed(() =>
  results.value.filter((r) => r.status === 'success' || r.status === 'failed').length
)
const successCount = computed(() =>
  results.value.filter((r) => r.status === 'success').length
)
const failCount = computed(() =>
  results.value.filter((r) => r.status === 'failed').length
)
const progressPercent = computed(() =>
  results.value.length === 0
    ? 0
    : Math.round((doneCount.value / results.value.length) * 100)
)
const progressStatus = computed(() => {
  if (processing.value) return undefined
  if (failCount.value > 0 && successCount.value === 0) return 'exception'
  if (failCount.value > 0) return 'warning'
  return 'success'
})
const progressText = computed(() => {
  if (processing.value) {
    return `提取中（${doneCount.value + 1} / ${links.value.length}）`
  }
  return '提取'
})

// === 主流程 ===
async function handleExtract() {
  if (links.value.length === 0 || processing.value) return

  // 初始化结果列表
  results.value = links.value.map((url) => ({
    success: false,
    url,
    script: null,
    error: null,
    status: 'pending',
  }))

  processing.value = true
  abortController = new AbortController()

  for (let i = 0; i < results.value.length; i++) {
    if (abortController.signal.aborted) break
    currentIndex.value = i
    await processOne(i)
  }

  processing.value = false
  abortController = null

  const okN = successCount.value
  const failN = failCount.value
  if (failN === 0) {
    ElMessage.success(`全部完成，共 ${okN} 条`)
  } else if (okN === 0) {
    ElMessage.error(`全部失败（${failN} 条），可点「重试」再试`)
  } else {
    ElMessage.warning(`完成：成功 ${okN} 条，失败 ${failN} 条`)
  }
}

async function processOne(idx: number) {
  const item = results.value[idx]
  if (item.status === 'success') return // 已成功不重试

  item.status = 'processing'
  item.error = null

  try {
    const res = await extractTiktokScript(item.url, abortController?.signal)
    item.success = res.success
    item.script = res.script
    item.error = res.error
    item.video_size = res.video_size
    item.status = res.success ? 'success' : 'failed'
  } catch (e) {
    // AbortError 不算失败（用户主动中断）
    if (abortController?.signal.aborted) {
      item.status = 'pending'
      return
    }
    item.success = false
    item.error = getErrorMessage(e, '提取失败')
    item.status = 'failed'
  }
}

function handleCancel() {
  if (abortController) {
    abortController.abort()
    ElMessage.info('已中断，已提取的结果保留')
  }
}

// === 单条重试 ===
async function handleRetryOne(idx: number) {
  if (processing.value) return
  // 单独的 abortController
  const singleAbort = new AbortController()
  processing.value = true
  abortController = singleAbort

  await processOne(idx)

  processing.value = false
  abortController = null

  const item = results.value[idx]
  if (item.status === 'success') {
    ElMessage.success('重试成功')
  } else {
    ElMessage.error('重试失败：' + (item.error || '未知错误'))
  }
}

// === 批量重试失败的 ===
async function handleRetryFailed() {
  if (processing.value) return
  const failedIndexes = results.value
    .map((r, i) => (r.status === 'failed' ? i : -1))
    .filter((i) => i >= 0)

  if (failedIndexes.length === 0) return

  processing.value = true
  abortController = new AbortController()

  for (const idx of failedIndexes) {
    if (abortController.signal.aborted) break
    await processOne(idx)
  }

  processing.value = false
  abortController = null
}

// === 工具 ===
function shortenUrl(url: string): string {
  if (url.length <= 60) return url
  return url.slice(0, 30) + '...' + url.slice(-25)
}

async function copyOne(item: ResultItem) {
  if (!item.script) return
  try {
    await navigator.clipboard.writeText(item.script)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选择文本')
  }
}

async function copyAll() {
  const successItems = results.value.filter((r) => r.status === 'success' && r.script)
  if (successItems.length === 0) return

  const text = successItems
    .map((item, i) => {
      return `# 视频 ${i + 1}\n链接：${item.url}\n\n${item.script}`
    })
    .join('\n\n' + '='.repeat(60) + '\n\n')

  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`已复制 ${successItems.length} 条字幕到剪贴板`)
  } catch {
    ElMessage.error('复制失败')
  }
}

function handleClear() {
  results.value = []
}
</script>

<style scoped>
.tiktok-script-view {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 8px 0;
  background: linear-gradient(135deg, var(--el-color-primary), var(--el-color-primary-light-3));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.page-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 0;
  line-height: 1.6;
}

.main-content {
  align-items: stretch;
}

.link-count {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.link-count strong {
  color: var(--el-color-primary);
  font-weight: 700;
}

.tips {
  margin-top: 16px;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  border-left: 3px solid var(--el-color-info);
}

.tips p {
  margin: 0 0 8px 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.tips ul {
  margin: 0;
  padding-left: 20px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.8;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.progress-card {
  flex-shrink: 0;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  flex-wrap: wrap;
}

.fail-count {
  color: var(--el-color-danger);
  font-weight: 600;
}

.result-item {
  width: 100%;
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.item-url {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
  font-size: 13px;
}

.item-url a {
  color: var(--el-color-primary);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-url a:hover {
  text-decoration: underline;
}

.item-status {
  flex-shrink: 0;
}

.script-content pre {
  background: var(--el-fill-color-darker, #f5f7fa);
  border-radius: 6px;
  padding: 12px;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 400px;
  overflow-y: auto;
  margin: 0 0 10px 0;
  color: var(--el-text-color-regular);
}

.error-content,
.processing-content,
.pending-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.processing-content,
.pending-content {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  padding: 16px 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.item-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.spin {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
