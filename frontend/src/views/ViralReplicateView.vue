<template>
  <div class="replicate-view">
    <!-- 标题区 -->
    <div class="page-header">
      <h1 class="page-title">爆品复刻</h1>
      <p class="page-desc">
        上传爆款视频 + 你的商品，AI 自动抽取爆款叙事骨架（hook 类型 / 镜头数 / 节奏），
        再基于你的商品裂变出 3 份差异化视频 prompt（场景迁移 / 受众错位 / 风格变体），
        选中后一键调 Seedance 生成视频
      </p>
    </div>

    <el-row :gutter="20" class="main-content">
      <!-- 左侧：输入区 -->
      <el-col :span="10">
        <el-card>
          <el-form label-position="top">
            <!-- 1. 原视频素材 -->
            <el-form-item label="原爆款视频" required>
              <!-- 方式一：链接 -->
              <div class="link-input-row">
                <el-input
                  v-model="videoUrl"
                  placeholder="粘贴 TikTok / Instagram / YouTube 短视频链接"
                  clearable
                  :disabled="!!videoFile || importing"
                >
                  <template #append>
                    <el-button
                      :disabled="!videoUrl || !!videoFile"
                      :loading="importing"
                      @click="handleImportLink"
                    >
                      {{ importing ? '解析中' : '解析' }}
                    </el-button>
                  </template>
                </el-input>
              </div>
              <div class="link-hint">
                支持 TikTok / Instagram / YouTube / 抖音；服务器可能被平台风控，失败请改用上传
              </div>

              <!-- 分隔线 -->
              <div class="divider"><span>或</span></div>

              <!-- 方式二：文件上传 -->
              <el-upload
                v-if="!videoFile"
                :auto-upload="false"
                :show-file-list="false"
                :on-change="handleVideoChange"
                accept=".mp4,.mov,.webm,.mkv"
                drag
                class="upload-area"
                :disabled="!!videoUrl || importing"
              >
                <el-icon :size="40"><UploadFilled /></el-icon>
                <div class="upload-text">拖拽或点击上传</div>
                <div class="upload-hint">支持 MP4 / MOV / WebM，最大 15MB</div>
              </el-upload>
              <div v-else class="video-preview">
                <div class="video-info">
                  <el-icon :size="20"><VideoCamera /></el-icon>
                  <span class="video-name" :title="videoFile.name">{{ videoFile.name }}</span>
                  <span class="video-size">{{ formatSize(videoFile.size) }}</span>
                </div>
                <el-button
                  type="danger"
                  :icon="Close"
                  circle
                  size="small"
                  @click="clearVideo"
                />
              </div>
              <!-- 链接解析后的视频信息 -->
              <div v-if="!videoFile && importedFromUrl" class="video-preview">
                <div class="video-info">
                  <el-icon :size="20"><Link /></el-icon>
                  <span class="video-name">链接解析成功</span>
                  <el-tag size="small" type="success">{{ videoSource }}</el-tag>
                </div>
                <el-button type="danger" :icon="Close" circle size="small" @click="clearVideoUrl" />
              </div>
            </el-form-item>

            <!-- 2. 商品图 -->
            <el-form-item label="商品图（可选但推荐，1-3 张）">
              <el-upload
                :file-list="productImageList"
                :auto-upload="false"
                :show-file-list="true"
                list-type="picture-card"
                :on-change="handleProductImageChange"
                :on-remove="handleProductImageRemove"
                accept="image/*"
                :limit="3"
                multiple
              >
                <el-icon><Plus /></el-icon>
              </el-upload>
            </el-form-item>

            <!-- 3. 商品信息 -->
            <el-form-item label="商品信息（可选）">
              <el-input
                v-model="productInfo"
                type="textarea"
                :rows="3"
                placeholder="商品名称 / 卖点 / 受众 / 目标市场。可粘贴 listing 描述。留空时 AI 会从商品图自动分析。"
              />
            </el-form-item>

            <!-- 4. 额外要求 -->
            <el-form-item label="额外要求（可选）">
              <el-input
                v-model="extraPrompt"
                type="textarea"
                :rows="2"
                placeholder="如：3 份都聚焦某个卖点 / 全部英文 prompt / 强调某种风格"
              />
            </el-form-item>

            <!-- 提交 -->
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="loading"
                :disabled="!canSubmit"
                @click="handleSubmit"
                style="width: 100%"
              >
                {{ loading ? `AI 分析中（${currentStep}）...` : '开始裂变（约 1-2 分钟）' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：结果区 -->
      <el-col :span="14">
        <!-- 无结果 -->
        <el-card v-if="!result && !loading">
          <el-empty description="上传爆款视频 + 商品后点击「开始裂变」" />
        </el-card>

        <!-- 加载中 -->
        <el-card v-else-if="loading">
          <div class="loading-state">
            <el-icon :size="32" class="spin"><Loading /></el-icon>
            <p class="step-text">{{ currentStep }}</p>
            <p class="loading-hint">3 步链路：骨架提取 → 商品分析 → 裂变变体，预计 1-2 分钟</p>
          </div>
        </el-card>

        <!-- 结果展示 -->
        <div v-else-if="result" class="result-wrap">
          <!-- 骨架摘要 -->
          <el-card class="structure-card">
            <template #header>
              <div class="result-header">
                <div class="result-title">
                  <el-icon><TrendCharts /></el-icon>
                  <span>原视频叙事骨架</span>
                </div>
                <el-tag size="small" type="info">{{ result.video_source === 'link' ? '链接解析' : '文件上传' }}</el-tag>
              </div>
            </template>
            <div class="structure-meta">
              <el-tag size="small">{{ result.structure.duration || '?' }}s</el-tag>
              <el-tag size="small" type="success">{{ result.structure.shot_count || '?'}} 个镜头</el-tag>
              <el-tag size="small" type="warning">{{ result.structure.pacing || '未知节奏' }}</el-tag>
              <el-tag size="small" type="info">{{ result.structure.vibe || '未知基调' }}</el-tag>
            </div>
            <p v-if="result.structure.why_viral" class="why-viral">
              <el-icon><MagicStick /></el-icon>
              <span>{{ result.structure.why_viral }}</span>
            </p>
          </el-card>

          <!-- 3 张变体卡片 -->
          <el-row :gutter="12" class="variations-row">
            <el-col
              v-for="(v, idx) in result.variations"
              :key="idx"
              :span="24"
              class="variation-col"
            >
              <el-card class="variation-card">
                <div class="variation-header">
                  <div class="variation-title">
                    <el-tag :type="variationTagType(v.variation_type)" size="small">
                      {{ v.variation_type || `变体 ${idx + 1}` }}
                    </el-tag>
                    <span class="variation-title-text">{{ v.title || '' }}</span>
                  </div>
                  <div class="variation-actions">
                    <el-button size="small" :icon="CopyDocument" @click="copyVariation(v)">
                      复制
                    </el-button>
                    <el-button
                      size="small"
                      type="primary"
                      :icon="VideoCameraFilled"
                      @click="openGenerateDialog(v)"
                    >
                      生成视频
                    </el-button>
                  </div>
                </div>
                <p v-if="v.reason" class="variation-reason">{{ v.reason }}</p>
                <pre class="variation-prompt">{{ v.prompt }}</pre>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-col>
    </el-row>

    <!-- 生成视频弹窗 -->
    <el-dialog
      v-model="generateDialogVisible"
      title="生成视频"
      width="540px"
    >
      <el-form label-width="80px">
        <el-form-item label="Prompt">
          <el-input
            v-model="generateForm.prompt"
            type="textarea"
            :rows="5"
            disabled
          />
        </el-form-item>
        <el-form-item label="视频时长">
          <el-radio-group v-model="generateForm.duration">
            <el-radio :value="5">5 秒</el-radio>
            <el-radio :value="10">10 秒</el-radio>
            <el-radio :value="15">15 秒</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="画面比例">
          <el-radio-group v-model="generateForm.ratio">
            <el-radio value="9:16">9:16 竖屏</el-radio>
            <el-radio value="16:9">16:9 横屏</el-radio>
            <el-radio value="1:1">1:1 方形</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="分辨率">
          <el-radio-group v-model="generateForm.resolution">
            <el-radio value="480p">480p</el-radio>
            <el-radio value="720p">720p</el-radio>
            <el-radio value="1080p">1080p</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submittingVideo"
          @click="handleGenerateVideo"
        >
          确认生成（提交到视频任务）
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadFiles, UploadRawFile } from 'element-plus'
import {
  UploadFilled,
  VideoCamera,
  VideoCameraFilled,
  Close,
  Loading,
  CopyDocument,
  MagicStick,
  TrendCharts,
  Plus,
  Link,
} from '@element-plus/icons-vue'
import {
  replicateAnalyze,
  submitVideo,
  getErrorMessage,
  type ReplicateResult,
  type ReplicateVariation,
} from '../api'

const router = useRouter()

const MAX_VIDEO_SIZE = 15 * 1024 * 1024

// === 输入 ===
const videoUrl = ref('')
const videoFile = ref<File | null>(null)
const importedFromUrl = ref(false) // 标记链接已解析
const videoSource = ref('') // 链接解析后的标识（如 'tiktok.com'）
const productInfo = ref('')
const extraPrompt = ref('')

const productImageList = ref<UploadFiles>([])
const productImages = ref<UploadRawFile[]>([])

const loading = ref(false)
const importing = ref(false) // 链接解析中
const currentStep = ref('提取叙事骨架...')
const result = ref<ReplicateResult | null>(null)

// === 生成视频弹窗 ===
const generateDialogVisible = ref(false)
const submittingVideo = ref(false)
const generateForm = reactive({
  prompt: '',
  duration: 5 as number,
  ratio: '9:16',
  resolution: '720p',
})

const canSubmit = computed(
  () => (!!videoFile.value || importedFromUrl.value) && !loading.value
)

// === 视频处理 ===
function handleVideoChange(file: UploadFile) {
  if (!file.raw) return
  if (file.raw.size > MAX_VIDEO_SIZE) {
    ElMessage.error(`视频大小 ${formatSize(file.raw.size)} 超过 15MB 限制`)
    return
  }
  videoFile.value = file.raw
  // 切换到上传模式时清空链接
  videoUrl.value = ''
  importedFromUrl.value = false
  result.value = null
}

function clearVideo() {
  videoFile.value = null
}

function clearVideoUrl() {
  videoUrl.value = ''
  importedFromUrl.value = false
  videoSource.value = ''
}

async function handleImportLink() {
  if (!videoUrl.value) return
  importing.value = true
  // 链接解析实际在后端 analyze 时一起做（避免两次下载），这里只做 UI 标记 + 提示
  // 真正下载需要服务器网络，提前解析可能被风控浪费。这里只验证 URL 形态合法。
  try {
    const u = new URL(videoUrl.value)
    if (!u.protocol.startsWith('http')) throw new Error()
    importedFromUrl.value = true
    videoSource.value = u.host
    videoFile.value = null
    result.value = null
    ElMessage.success(`链接已就绪（点击「开始裂变」时后端会下载并解析）`)
  } catch {
    ElMessage.error('链接格式无效，请粘贴 http(s):// 开头的完整链接')
  } finally {
    importing.value = false
  }
}

// === 商品图处理 ===
function handleProductImageChange(_file: UploadFile, files: UploadFiles) {
  if (files.length > 3) {
    ElMessage.warning('最多 3 张商品图')
  }
  productImageList.value = files.slice(0, 3)
  productImages.value = productImageList.value
    .map((f) => f.raw)
    .filter((f): f is UploadRawFile => !!f)
}

function handleProductImageRemove(_file: UploadFile, files: UploadFiles) {
  productImageList.value = files
  productImages.value = files
    .map((f) => f.raw)
    .filter((f): f is UploadRawFile => !!f)
}

// === 主流程 ===
async function handleSubmit() {
  if (!canSubmit.value) return
  loading.value = true
  result.value = null
  currentStep.value = '提取叙事骨架...'
  // 模拟分步进度提示
  const steps = [
    '提取叙事骨架...',
    'Gemini 视频分析中（1 FPS 采样）...',
    '商品分析中...',
    '裂变 3 份差异化 prompt...',
    '整理结果...',
  ]
  let stepIdx = 0
  const timer = setInterval(() => {
    stepIdx = Math.min(stepIdx + 1, steps.length - 1)
    currentStep.value = steps[stepIdx]
  }, 20000)

  try {
    const res = await replicateAnalyze({
      video: videoFile.value || undefined,
      videoUrl: importedFromUrl.value ? videoUrl.value : undefined,
      productImages: productImages.value,
      productInfo: productInfo.value,
      extraPrompt: extraPrompt.value,
    })
    result.value = res
    ElMessage.success(`裂变完成，共 ${res.variations.length} 份变体`)
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '爆品复刻失败，请重试'))
  } finally {
    clearInterval(timer)
    loading.value = false
  }
}

// === 工具 ===
function formatSize(bytes: number): string {
  const mb = bytes / 1024 / 1024
  if (mb < 1) return `${(bytes / 1024).toFixed(0)} KB`
  return `${mb.toFixed(2)} MB`
}

function variationTagType(type: string): 'primary' | 'success' | 'warning' {
  const map: Record<string, 'primary' | 'success' | 'warning'> = {
    场景迁移: 'primary',
    受众错位: 'success',
    风格变体: 'warning',
  }
  return map[type] || 'primary'
}

async function copyVariation(v: ReplicateVariation) {
  try {
    await navigator.clipboard.writeText(v.prompt)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选择文本')
  }
}

// === 生成视频 ===
function openGenerateDialog(v: ReplicateVariation) {
  generateForm.prompt = v.prompt
  generateForm.duration = 5
  generateForm.ratio = '9:16'
  generateForm.resolution = '720p'
  generateDialogVisible.value = true
}

async function handleGenerateVideo() {
  if (!generateForm.prompt) return
  submittingVideo.value = true
  try {
    await submitVideo({
      description: generateForm.prompt,
      product_images: productImages.value,
      duration: generateForm.duration,
      ratio: generateForm.ratio,
      resolution: generateForm.resolution,
      model_has_face: true,
    })
    ElMessage.success('视频任务已提交，跳转到视频生成页...')
    generateDialogVisible.value = false
    router.push('/video')
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '视频提交失败'))
  } finally {
    submittingVideo.value = false
  }
}
</script>

<style scoped>
.replicate-view {
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

.link-input-row {
  width: 100%;
}

.link-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.5;
}

.divider {
  display: flex;
  align-items: center;
  text-align: center;
  margin: 16px 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid var(--el-border-color);
}

.divider span {
  padding: 0 12px;
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  padding: 30px 20px;
}

.upload-text {
  font-size: 14px;
  color: var(--el-text-color-regular);
  margin-top: 8px;
}

.upload-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.video-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  border: 1px solid var(--el-border-color);
  margin-top: 8px;
}

.video-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.video-name {
  font-size: 13px;
  color: var(--el-text-color-regular);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.video-size {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 8px;
}

.loading-state p {
  margin: 0;
  color: var(--el-text-color-regular);
}

.step-text {
  font-weight: 600;
  font-size: 15px;
}

.loading-hint {
  font-size: 12px !important;
  color: var(--el-text-color-secondary) !important;
}

.spin {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.result-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.structure-card {
  flex-shrink: 0;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.result-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.structure-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.why-viral {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  margin: 0;
  padding: 10px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  border-left: 3px solid var(--el-color-primary);
}

.why-viral :deep(.el-icon) {
  margin-top: 3px;
  flex-shrink: 0;
  color: var(--el-color-primary);
}

.variations-row {
  gap: 0 !important;
}

.variation-col {
  margin-bottom: 12px;
}

.variation-card {
  width: 100%;
}

.variation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.variation-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.variation-title-text {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.variation-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.variation-reason {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 0 0 8px 0;
  font-style: italic;
  line-height: 1.5;
}

.variation-prompt {
  background: var(--el-fill-color-darker, #f5f7fa);
  border-radius: 6px;
  padding: 12px;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 280px;
  overflow-y: auto;
  margin: 0;
  color: var(--el-text-color-regular);
}
</style>
