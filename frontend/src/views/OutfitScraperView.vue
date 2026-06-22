<template>
  <div class="outfit-scraper-view">
    <div class="page-header">
      <h1 class="page-title">穿搭素材抓取</h1>
      <p class="page-desc">
        粘贴 TikTok / Instagram / YouTube / 抖音 视频链接，自动下载并抽取穿搭关键帧。
        可一键送入视频生成作为参考图，免手动截图
      </p>
    </div>

    <el-row :gutter="20" class="main-content">
      <!-- 左侧：输入区 -->
      <el-col :span="10">
        <el-card>
          <el-form label-position="top">
            <el-tabs v-model="mode" class="input-tabs">
              <!-- 链接模式 -->
              <el-tab-pane label="链接模式" name="link">
                <el-form-item label="视频链接" required>
                  <el-input
                    v-model="rawInput"
                    type="textarea"
                    :rows="10"
                    placeholder="粘贴视频链接，支持一条或多条&#10;每行一个，或用空格、逗号分隔"
                    :disabled="processing"
                  />
                  <div class="link-count">
                    <el-icon><Link /></el-icon>
                    <span>已识别 <strong>{{ links.length }}</strong> 条链接</span>
                  </div>
                </el-form-item>
              </el-tab-pane>

              <!-- 上传模式 -->
              <el-tab-pane label="上传模式" name="upload">
                <el-upload
                  drag
                  multiple
                  :auto-upload="false"
                  accept="video/*"
                  :file-list="uploadFileList"
                  :on-change="handleFileChange"
                  :on-remove="handleFileRemove"
                  :disabled="processing"
                >
                  <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                  <div class="el-upload__text">
                    拖拽视频到此处，或<em>点击选择</em>
                  </div>
                  <template #tip>
                    <div class="upload-tip">
                      支持 mp4/mov/webm 等，单个 ≤30MB，可多选。
                      <br />TikTok 链接被风控时，手动下载后用此模式更稳。
                    </div>
                  </template>
                </el-upload>
                <div class="link-count" v-if="uploadFileList.length > 0">
                  <el-icon><UploadFilled /></el-icon>
                  <span>已选 <strong>{{ uploadFileList.length }}</strong> 个视频</span>
                </div>
              </el-tab-pane>
            </el-tabs>

            <el-form-item label="每条返回帧数">
              <el-slider v-model="maxFrames" :min="3" :max="12" :step="1" show-input :disabled="processing" />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="processing"
                :disabled="canStart === false"
                @click="handleStart"
                style="width: 100%"
              >
                {{ processing ? progressText : (mode === 'link' ? '抓取' : '开始抽帧') }}
              </el-button>
            </el-form-item>

            <el-form-item v-if="processing">
              <el-button size="default" :icon="Close" @click="handleCancel" style="width: 100%">
                中断（已抓取的结果会保留）
              </el-button>
            </el-form-item>

            <div class="tips">
              <p><el-icon><InfoFilled /></el-icon> 说明</p>
              <ul>
                <li v-if="mode === 'link'">串行处理，每条约 10-30 秒（下载 + ffmpeg 抽帧）</li>
                <li v-else>串行处理，每个视频约 5-15 秒（仅 ffmpeg 抽帧，无下载）</li>
                <li v-if="mode === 'link'">TikTok 服务器可能风控，失败时可切换「上传模式」手动上传</li>
                <li>ffmpeg 自动按场景变化挑关键帧（跳过相似帧）</li>
                <li>点击关键帧可放大，勾选后一键送入视频生成</li>
              </ul>
            </div>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：结果区 -->
      <el-col :span="14">
        <el-card v-if="results.length === 0 && !processing">
          <el-empty description="粘贴链接后点击「抓取」" />
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
                v-if="!processing && selectedFramesCount > 0"
                size="small"
                type="success"
                :icon="VideoCamera"
                @click="sendToVideo"
              >
                送入视频生成（{{ selectedFramesCount }} 张）
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
          <div v-for="(item, idx) in results" :key="idx" class="result-item">
            <el-card>
              <template #header>
                <div class="item-header">
                  <div class="item-url">
                    <el-icon>
                      <UploadFilled v-if="!item.url.startsWith('http')" />
                      <Link v-else />
                    </el-icon>
                    <a v-if="item.url.startsWith('http')" :href="item.url" target="_blank" rel="noopener" :title="item.url">
                      {{ shortenUrl(item.url) }}
                    </a>
                    <span v-else :title="item.url">{{ item.url }}</span>
                  </div>
                  <div class="item-status">
                    <el-tag v-if="item.status === 'pending'" size="small" type="info">等待中</el-tag>
                    <el-tag v-else-if="item.status === 'processing'" size="small" type="warning">
                      <el-icon class="spin"><Loading /></el-icon>
                      抽帧中
                    </el-tag>
                    <el-tag v-else-if="item.status === 'success'" size="small" type="success">
                      成功（{{ item.frames?.length || 0 }} 帧）
                    </el-tag>
                    <el-tag v-else size="small" type="danger">失败</el-tag>
                  </div>
                </div>
              </template>

              <!-- 成功 -->
              <div v-if="item.status === 'success' && item.frames?.length" class="frames-grid">
                <div
                  v-for="(frame, fIdx) in item.frames"
                  :key="fIdx"
                  class="frame-item"
                  :class="{ selected: isSelected(idx, fIdx) }"
                  @click="toggleFrame(idx, fIdx)"
                >
                  <el-image
                    :src="frame"
                    fit="cover"
                    :preview-src-list="item.frames"
                    :initial-index="fIdx"
                    :preview-teleported="true"
                    class="frame-img"
                    @click.stop
                  />
                  <div class="frame-check" v-if="isSelected(idx, fIdx)">
                    <el-icon><Check /></el-icon>
                  </div>
                  <div class="frame-actions">
                    <el-button size="small" text :icon="Download" @click.stop="downloadFrame(frame, `${idx}_${fIdx}.jpg`)" />
                  </div>
                </div>
              </div>

              <!-- 失败 -->
              <div v-else-if="item.status === 'failed'" class="error-content">
                <el-alert :title="item.error || '抓取失败'" type="error" :closable="false" show-icon />
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
                <span>{{ mode === 'link' ? '下载视频 + ffmpeg 抽帧中（约 10-30 秒）...' : 'ffmpeg 抽帧中（约 5-15 秒）...' }}</span>
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
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import {
  Link, Close, Loading, RefreshRight, InfoFilled,
  Download, Check, VideoCamera, UploadFilled,
} from '@element-plus/icons-vue'
import {
  scrapeOutfit, scrapeOutfitUpload, getErrorMessage, type OutfitScrapeResult,
} from '../api'

type ItemStatus = 'pending' | 'processing' | 'success' | 'failed'

interface ResultItem extends OutfitScrapeResult {
  status: ItemStatus
}

const router = useRouter()
const mode = ref<'link' | 'upload'>('link')
const rawInput = ref('')
const uploadFileList = ref<UploadFile[]>([])
const processing = ref(false)
const results = ref<ResultItem[]>([])
const maxFrames = ref(8)
const selectedFrames = ref<Set<string>>(new Set()) // key = "itemIdx_frameIdx"
let abortController: AbortController | null = null

const URL_REGEX = /https?:\/\/[^\s,，]+/g

const links = computed(() => {
  const text = rawInput.value.trim()
  if (!text) return []
  const matches = text.match(URL_REGEX)
  return matches ? Array.from(new Set(matches)) : []
})

const doneCount = computed(() =>
  results.value.filter((r) => r.status === 'success' || r.status === 'failed').length
)
const successCount = computed(() => results.value.filter((r) => r.status === 'success').length)
const failCount = computed(() => results.value.filter((r) => r.status === 'failed').length)
const progressPercent = computed(() =>
  results.value.length === 0 ? 0 : Math.round((doneCount.value / results.value.length) * 100)
)
const progressStatus = computed(() => {
  if (processing.value) return undefined
  if (failCount.value > 0 && successCount.value === 0) return 'exception'
  if (failCount.value > 0) return 'warning'
  return 'success'
})
const progressText = computed(() =>
  processing.value
    ? `处理中（${doneCount.value + 1} / ${results.value.length}）`
    : (mode.value === 'link' ? '抓取' : '开始抽帧')
)

const selectedFramesCount = computed(() => selectedFrames.value.size)

const canStart = computed(() => {
  if (processing.value) return false
  return mode.value === 'link' ? links.value.length > 0 : uploadFileList.value.length > 0
})

// === 文件上传管理 ===
function handleFileChange(file: UploadFile) {
  if (file.raw && !file.raw.type.startsWith('video/')) {
    ElMessage.warning(`${file.name} 不是视频文件，已跳过`)
    return
  }
  if (file.raw && file.raw.size > 30 * 1024 * 1024) {
    ElMessage.warning(`${file.name} 超过 30MB，已跳过`)
    return
  }
  uploadFileList.value.push(file)
}

function handleFileRemove(file: UploadFile) {
  const idx = uploadFileList.value.findIndex((f) => f.uid === file.uid)
  if (idx >= 0) uploadFileList.value.splice(idx, 1)
}

// === 主流程（统一入口，根据 mode 分发） ===
async function handleStart() {
  if (canStart.value === false) return
  selectedFrames.value.clear()

  if (mode.value === 'link') {
    results.value = links.value.map((url) => ({
      success: false, url, frames: [], error: null, status: 'pending',
    }))
  } else {
    results.value = uploadFileList.value.map((f) => ({
      success: false, url: f.name, frames: [], error: null, status: 'pending',
    }))
  }

  processing.value = true
  abortController = new AbortController()

  for (let i = 0; i < results.value.length; i++) {
    if (abortController.signal.aborted) break
    await processOne(i)
  }

  processing.value = false
  abortController = null

  const okN = successCount.value
  const failN = failCount.value
  if (failN === 0) ElMessage.success(`全部完成，共 ${okN} 条`)
  else if (okN === 0) ElMessage.error(`全部失败（${failN} 条）`)
  else ElMessage.warning(`完成：成功 ${okN} 条，失败 ${failN} 条`)
}

async function processOne(idx: number) {
  const item = results.value[idx]
  if (item.status === 'success') return
  item.status = 'processing'
  item.error = null

  try {
    const res = mode.value === 'link'
      ? await scrapeOutfit(item.url, maxFrames.value, abortController?.signal)
      : await scrapeOutfitUpload(uploadFileList.value[idx].raw as File, maxFrames.value, abortController?.signal)
    item.success = res.success
    item.frames = res.frames || []
    item.error = res.error
    item.video_size = res.video_size
    item.status = res.success ? 'success' : 'failed'
  } catch (e) {
    if (abortController?.signal.aborted) {
      item.status = 'pending'
      return
    }
    item.success = false
    item.error = getErrorMessage(e, mode.value === 'link' ? '抓取失败' : '抽帧失败')
    item.status = 'failed'
  }
}

function handleCancel() {
  if (abortController) {
    abortController.abort()
    ElMessage.info('已中断，已抓取的结果保留')
  }
}

async function handleRetryOne(idx: number) {
  if (processing.value) return
  const singleAbort = new AbortController()
  processing.value = true
  abortController = singleAbort
  await processOne(idx)
  processing.value = false
  abortController = null

  const item = results.value[idx]
  if (item.status === 'success') ElMessage.success('重试成功')
  else ElMessage.error('重试失败：' + (item.error || '未知错误'))
}

async function handleRetryFailed() {
  if (processing.value) return
  const failedIndexes = results.value.map((r, i) => (r.status === 'failed' ? i : -1)).filter((i) => i >= 0)
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

// === 帧选择 ===
function isSelected(itemIdx: number, frameIdx: number): boolean {
  return selectedFrames.value.has(`${itemIdx}_${frameIdx}`)
}

function toggleFrame(itemIdx: number, frameIdx: number) {
  const key = `${itemIdx}_${frameIdx}`
  if (selectedFrames.value.has(key)) selectedFrames.value.delete(key)
  else selectedFrames.value.add(key)
  // 触发响应式更新
  selectedFrames.value = new Set(selectedFrames.value)
}

function downloadFrame(dataUrl: string, filename: string) {
  const link = document.createElement('a')
  link.href = dataUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// === 送入视频生成 ===
async function sendToVideo() {
  if (selectedFrames.value.size === 0) return

  // 收集选中的帧（data URL）
  const frames: { dataUrl: string; file: File }[] = []
  for (const key of selectedFrames.value) {
    const [itemIdxStr, frameIdxStr] = key.split('_')
    const itemIdx = parseInt(itemIdxStr)
    const frameIdx = parseInt(frameIdxStr)
    const dataUrl = results.value[itemIdx]?.frames?.[frameIdx]
    if (!dataUrl) continue
    const file = await dataUrlToFile(dataUrl, `frame_${itemIdx}_${frameIdx}.jpg`)
    frames.push({ dataUrl, file })
  }

  if (frames.length === 0) {
    ElMessage.error('无法获取选中的帧')
    return
  }

  // 用 sessionStorage 传递给视频页（VideoGenView 读 'video_ref_images' key）
  const dataUrls = frames.map((f) => f.dataUrl)
  sessionStorage.setItem('video_ref_images', JSON.stringify(dataUrls))

  ElMessage.success(`已选 ${frames.length} 张，跳转视频生成页`)
  router.push('/video')
}

async function dataUrlToFile(dataUrl: string, filename: string): Promise<File> {
  const resp = await fetch(dataUrl)
  const blob = await resp.blob()
  return new File([blob], filename, { type: 'image/jpeg' })
}

// === 工具 ===
function shortenUrl(url: string): string {
  if (url.length <= 60) return url
  return url.slice(0, 30) + '...' + url.slice(-25)
}

function handleClear() {
  results.value = []
  selectedFrames.value.clear()
}
</script>

<style scoped>
.outfit-scraper-view {
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

.input-tabs {
  margin-bottom: 8px;
}

.upload-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
  padding-top: 4px;
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

.frames-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}

.frame-item {
  position: relative;
  border: 2px solid transparent;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
}

.frame-item:hover {
  border-color: var(--el-color-primary-light-5);
}

.frame-item.selected {
  border-color: var(--el-color-success);
  box-shadow: 0 0 0 2px var(--el-color-success-light-5);
}

.frame-img {
  width: 100%;
  aspect-ratio: 3/4;
  display: block;
}

.frame-check {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  background: var(--el-color-success);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
}

.frame-actions {
  position: absolute;
  bottom: 4px;
  right: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.frame-item:hover .frame-actions {
  opacity: 1;
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
