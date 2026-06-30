<template>
  <div class="video-shot-view">
    <div class="page-header">
      <h1 class="page-title">
        分镜视频
        <el-tooltip content="查看使用说明" placement="top">
          <el-icon class="help-icon" @click="goGuide('video-shot')"><QuestionFilled /></el-icon>
        </el-tooltip>
      </h1>
      <p class="page-desc">
        AI 策划视频分镜（Hook → Detail → Recall 三段式叙事结构），
        每个分镜独立设计动作+运镜+视觉焦点，拼装后提交到 Seedance。比单段 prompt 叙事更有层次
      </p>
    </div>

    <el-row :gutter="20" class="main-content">
      <!-- 左侧：输入区 -->
      <el-col :span="10">
        <el-card>
          <el-form label-position="top">
            <el-form-item required>
              <template #label>
                <span>主题/创意描述</span>
                <el-button text size="small" @click="showPromptPicker = true" style="margin-left: 8px;">
                  <el-icon><Collection /></el-icon>从 Prompt 库选用
                </el-button>
                <EnhancePromptButton
                  task-type="video_shots"
                  :user-text="form.theme"
                  :duration="form.totalDuration"
                  size="small"
                  @enhanced="form.theme = $event"
                />
              </template>
              <el-input
                v-model="form.theme"
                type="textarea"
                :rows="3"
                placeholder="如：夏日优雅裙装，巴黎街头漫步感；或：美式街头皮夹克酷感穿搭"
              />
            </el-form-item>

            <el-form-item label="商品信息（可选）">
              <el-input
                v-model="form.productInfo"
                type="textarea"
                :rows="3"
                placeholder="商品描述/卖点/面料等，AI 会基于此规划服装强调点"
              />
            </el-form-item>

            <el-form-item label="商品图/参考图（可选）">
              <el-upload
                :file-list="refFileList"
                list-type="picture-card"
                :auto-upload="false"
                :on-change="handleRefChange"
                :on-remove="handleRefRemove"
                accept="image/*"
                :limit="1"
              >
                <el-icon><Plus /></el-icon>
              </el-upload>
            </el-form-item>

            <el-form-item label="总时长">
              <div class="duration-control">
                <el-slider
                  v-model="form.totalDuration"
                  :min="4"
                  :max="15"
                  :step="1"
                  :show-tooltip="false"
                  class="duration-slider"
                  :marks="{ 4: '4s', 10: '10s', 15: '15s' }"
                />
                <el-input-number
                  v-model="form.totalDuration"
                  :min="4"
                  :max="15"
                  :step="1"
                  size="small"
                  controls-position="right"
                  class="duration-input"
                />
                <span class="duration-unit">秒</span>
              </div>
            </el-form-item>

            <el-form-item label="额外要求（可选）">
              <el-input
                v-model="form.extraPrompt"
                type="textarea"
                :rows="2"
                placeholder="如：色调偏冷 / 强调动态感 / 突出面料质感"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="planning"
                :disabled="!form.theme.trim()"
                @click="handlePlan"
                style="width: 100%"
              >
                <el-icon style="margin-right: 4px"><MagicStick /></el-icon>
                AI 策划分镜
              </el-button>
            </el-form-item>

            <div class="tips">
              <p><el-icon><InfoFilled /></el-icon> 说明</p>
              <ul>
                <li>AI 按 Hook → Detail → Recall 三段式规划 2-3 个分镜</li>
                <li>分镜结果可编辑（动作/运镜/焦点都可改）</li>
                <li>提交后跳转「视频生成」页查看任务进度</li>
                <li>4-6 秒约 1 个分镜，7-10 秒约 2 个，11-15 秒约 3 个</li>
              </ul>
            </div>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：分镜结果区 -->
      <el-col :span="14">
        <el-card v-if="shots.length === 0 && !planning">
          <el-empty description="点击「AI 策划分镜」开始" />
        </el-card>

        <div v-else class="shots-container">
          <el-card v-if="planning" class="loading-card">
            <el-icon :size="28" class="spin"><Loading /></el-icon>
            <p>AI 正在规划分镜（约 10-20 秒）...</p>
          </el-card>

          <template v-else>
            <!-- 策划完成后：编辑区 -->
            <el-card class="visual-style-card">
              <div class="visual-style-label">整体视觉风格：</div>
              <el-input
                v-model="visualStyle"
                type="textarea"
                :rows="2"
                placeholder="所有分镜共享的视觉风格（如：烈日硬光 + 复古胶片颗粒 + 美式街头酷感）"
              />
            </el-card>

            <div v-for="(shot, idx) in shots" :key="idx" class="shot-card-wrapper">
              <el-card>
                <template #header>
                  <div class="shot-header">
                    <div class="shot-title">
                      <el-tag :type="purposeTagType(shot.purpose)" size="small">
                        {{ shot.purpose || `Shot ${idx + 1}` }}
                      </el-tag>
                      <span class="shot-time">
                        {{ shot.start_time }}-{{ shot.end_time }}s · {{ shot.duration }}s
                      </span>
                    </div>
                    <el-button
                      size="small"
                      text
                      type="danger"
                      :icon="Delete"
                      @click="removeShot(idx)"
                      :disabled="shots.length <= 1 || submitting"
                    />
                  </div>
                </template>

                <el-form label-position="top" class="shot-form">
                  <el-form-item label="动作">
                    <MentionTextarea
                      v-model="shot.action"
                      :refs-source="refsSource"
                      :rows="3"
                      :disabled="submitting"
                      placeholder="动作描述"
                    />
                  </el-form-item>
                  <el-form-item label="镜头语言">
                    <el-input
                      v-model="shot.camera"
                      type="textarea"
                      :rows="2"
                      placeholder="景别 + 运镜（如：中景→近景 / 手持跟拍 + 急速推近）"
                      :disabled="submitting"
                    />
                  </el-form-item>
                  <el-form-item label="视觉焦点">
                    <el-input
                      v-model="shot.focus"
                      type="textarea"
                      :rows="2"
                      :disabled="submitting"
                    />
                  </el-form-item>
                  <el-form-item label="服装强调">
                    <el-input
                      v-model="shot.garment_focus"
                      type="textarea"
                      :rows="2"
                      :disabled="submitting"
                    />
                  </el-form-item>
                  <div class="shot-duration-row">
                    <span>时长分配：</span>
                    <el-input-number
                      v-model="shot.duration"
                      :min="3"
                      :max="15"
                      :disabled="submitting"
                      size="small"
                      @change="recalcTimes()"
                    />
                    <span class="shot-total-hint">秒</span>
                  </div>
                </el-form>
              </el-card>
            </div>

            <!-- 提交生成区 -->
            <el-card class="submit-section">
              <el-divider content-position="left">提交参数</el-divider>
              <el-form label-position="top">
                <el-form-item label="商品图（1-6张，可选）">
                  <el-upload
                    :file-list="productFileList"
                    list-type="picture-card"
                    :auto-upload="false"
                    :on-change="(_f: any, fl: any) => handleProductChange(fl)"
                    :on-remove="(_f: any, fl: any) => handleProductChange(fl)"
                    accept="image/*"
                    :limit="6"
                  >
                    <el-icon><Plus /></el-icon>
                  </el-upload>
                </el-form-item>
                <el-form-item label="模特素材图（0-3张，可选）">
                  <el-upload
                    :file-list="modelFileList"
                    list-type="picture-card"
                    :auto-upload="false"
                    :on-change="(_f: any, fl: any) => handleModelChange(fl)"
                    :on-remove="(_f: any, fl: any) => handleModelChange(fl)"
                    accept="image/*"
                    :limit="3"
                  >
                    <el-icon><Plus /></el-icon>
                  </el-upload>
                </el-form-item>
                <el-form-item v-if="modelFiles.length > 0" label="模特图含人脸">
                  <el-switch v-model="form.modelHasFace" :disabled="submitting" />
                  <span class="hint-text">含真人脸的图会自动风格化为水彩插画</span>
                </el-form-item>
                <el-form-item label="视频比例">
                  <el-radio-group v-model="form.ratio" :disabled="submitting">
                    <el-radio-button value="16:9">16:9 横版</el-radio-button>
                    <el-radio-button value="9:16">9:16 竖版</el-radio-button>
                    <el-radio-button value="1:1">1:1 方形</el-radio-button>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="分辨率">
                  <el-radio-group v-model="form.resolution" :disabled="submitting">
                    <el-radio-button value="480p">480p</el-radio-button>
                    <el-radio-button value="720p">720p</el-radio-button>
                    <el-radio-button value="1080p">1080p</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-form>
              <el-button
                type="primary"
                size="large"
                :loading="submitting"
                :disabled="shots.length === 0 || totalDurationSum !== form.totalDuration"
                @click="handleSubmit"
                style="width: 100%"
              >
                <span v-if="totalDurationSum !== form.totalDuration" class="warn-text">
                  ⚠ 分镜时长合计 {{ totalDurationSum }}s ≠ 总时长 {{ form.totalDuration }}s，请调整
                </span>
                <span v-else>提交生成（{{ shots.length }} 分镜 / {{ form.totalDuration }}s）</span>
              </el-button>
            </el-card>
          </template>
        </div>
      </el-col>
    </el-row>

    <!-- Prompt 库选用弹窗 -->
    <PromptLibraryPicker v-model="showPromptPicker" task-type="video_shots" @pick="handlePickPrompt" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, MagicStick, InfoFilled, Loading, Delete, QuestionFilled, Collection,
} from '@element-plus/icons-vue'
import {
  planVideoShots, submitShotVideo, getErrorMessage,
  type VideoShot,
} from '../api'
import MentionTextarea from '../components/MentionTextarea.vue'
import PromptLibraryPicker from '../components/PromptLibraryPicker.vue'
import EnhancePromptButton from '../components/EnhancePromptButton.vue'
import type { RefItem } from '../composables/useReferenceMention'
import type { PromptLibraryItem } from '../types'

const router = useRouter()
function goGuide(anchor: string) {
  router.push({ path: '/user-guide', hash: `#${anchor}` })
}

const form = reactive({
  theme: '',
  productInfo: '',
  extraPrompt: '',
  totalDuration: 15 as 10 | 15,
  ratio: '16:9' as '16:9' | '9:16' | '1:1',
  resolution: '720p' as '480p' | '720p' | '1080p',
  modelHasFace: true,
})

const planning = ref(false)
const submitting = ref(false)
const shots = ref<VideoShot[]>([])
const visualStyle = ref('')

// 从 Prompt 库选用
const showPromptPicker = ref(false)
function handlePickPrompt(item: PromptLibraryItem) {
  form.theme = item.full_prompt
  if (item.aspect_ratio === '16:9' || item.aspect_ratio === '9:16' || item.aspect_ratio === '1:1') {
    form.ratio = item.aspect_ratio
  }
}

// 参考图（用于 AI 策划）
const refFileList = ref<any[]>([])
const refFile = ref<File | null>(null)

// 商品图 / 模特图（用于提交生成）
const productFileList = ref<any[]>([])
const modelFileList = ref<any[]>([])
const productFiles = ref<File[]>([])
const modelFiles = ref<File[]>([])

// 参考图预览（用于 @ 引用浮层显示）：productFiles + modelFiles 合并全局序号
// 用 watch 同步创建/释放 objectURL，避免内存泄漏
const productPreviews = ref<{ preview_url: string; filename: string }[]>([])
const modelPreviews = ref<{ preview_url: string; filename: string }[]>([])

function syncPreviews() {
  productPreviews.value.forEach((p) => URL.revokeObjectURL(p.preview_url))
  modelPreviews.value.forEach((p) => URL.revokeObjectURL(p.preview_url))
  productPreviews.value = productFiles.value.map((f, i) => ({
    preview_url: URL.createObjectURL(f),
    filename: `商品图${i + 1}`,
  }))
  modelPreviews.value = modelFiles.value.map((f, i) => ({
    preview_url: URL.createObjectURL(f),
    filename: `模特图${i + 1}`,
  }))
}

watch([productFiles, modelFiles], syncPreviews, { deep: true, immediate: true })

onMounted(() => {
  // 续15：从 Prompt 工坊接收预填分镜（跳过 plan 直接展示可编辑表）
  const prefillShots = sessionStorage.getItem('workshop_prefill_video_shots')
  if (prefillShots) {
    try {
      const parsed = JSON.parse(prefillShots) as VideoShot[]
      if (Array.isArray(parsed) && parsed.length > 0) {
        shots.value = parsed.map((s, i) => ({ ...s, index: i + 1 }))
        const theme = sessionStorage.getItem('workshop_prefill_video_shots_theme')
        if (theme) form.theme = theme
        // 取最后一个非空 visual_style 作为整体
        const vs = parsed.find((s) => s.visual_style?.trim())
        if (vs) visualStyle.value = vs.visual_style || ''
        ElMessage.success(`已从工坊预填 ${parsed.length} 个分镜，可直接提交或编辑`)
      }
    } catch {
      /* 忽略解析错误 */
    } finally {
      sessionStorage.removeItem('workshop_prefill_video_shots')
      sessionStorage.removeItem('workshop_prefill_video_shots_theme')
    }
  }
})

onUnmounted(() => {
  productPreviews.value.forEach((p) => URL.revokeObjectURL(p.preview_url))
  modelPreviews.value.forEach((p) => URL.revokeObjectURL(p.preview_url))
})

// @ 引用数据源：商品图 1-N + 模特图 N+1-M（全局序号）
const refsSource = computed<RefItem[]>(() => [
  ...productPreviews.value,
  ...modelPreviews.value,
])

const totalDurationSum = computed(() =>
  shots.value.reduce((sum, s) => sum + (Number(s.duration) || 0), 0)
)

// === AI 策划分镜 ===
async function handlePlan() {
  if (!form.theme.trim()) {
    ElMessage.warning('请输入主题/创意描述')
    return
  }

  planning.value = true
  shots.value = []
  try {
    const resp = await planVideoShots({
      theme: form.theme.trim(),
      totalDuration: form.totalDuration,
      productInfo: form.productInfo.trim() || undefined,
      extraPrompt: form.extraPrompt.trim() || undefined,
      referenceImage: refFile.value,
    })

    if (!resp.success || resp.shots.length === 0) {
      ElMessage.error('AI 策划返回为空，请换主题再试')
      return
    }

    shots.value = resp.shots.map((s, i) => ({ ...s, index: i + 1 }))
    // 取最后一个非空 visual_style 作为整体（AI 应该所有分镜共享）
    const vs = resp.shots.find((s) => s.visual_style?.trim())
    visualStyle.value = vs?.visual_style || ''
    ElMessage.success(`AI 策划完成，共 ${shots.value.length} 个分镜`)
  } catch (e) {
    ElMessage.error('AI 策划失败：' + getErrorMessage(e, '请重试'))
  } finally {
    planning.value = false
  }
}

// === 编辑操作 ===
function removeShot(idx: number) {
  shots.value.splice(idx, 1)
  recalcTimes()
}

function recalcTimes() {
  // 根据每镜 duration 重算 start_time / end_time
  let cursor = 0
  shots.value.forEach((s, i) => {
    s.index = i + 1
    s.start_time = cursor
    s.duration = Number(s.duration) || 0
    s.end_time = cursor + s.duration
    cursor = s.end_time
  })
}

// === 文件上传处理 ===
function handleRefChange(file: any, fileList: any[]) {
  refFileList.value = fileList
  refFile.value = file?.raw || null
}

function handleRefRemove(_file: any, fileList: any[]) {
  refFileList.value = fileList
  refFile.value = null
}

function handleProductChange(fileList: any[]) {
  productFileList.value = fileList
  productFiles.value = fileList.map((f) => f.raw)
}

function handleModelChange(fileList: any[]) {
  modelFileList.value = fileList
  modelFiles.value = fileList.map((f) => f.raw)
}

// === 提交生成 ===
async function handleSubmit() {
  if (shots.value.length === 0) return
  if (totalDurationSum.value !== form.totalDuration) {
    ElMessage.warning(`分镜时长合计 ${totalDurationSum.value}s ≠ 总时长 ${form.totalDuration}s`)
    return
  }

  // 同步 visualStyle 到所有 shot
  const finalShots = shots.value.map((s) => ({
    ...s,
    visual_style: visualStyle.value || s.visual_style,
  }))

  // 确认弹窗（二次确认，防误触）
  try {
    await ElMessageBox.confirm(
      `将提交 ${finalShots.length} 个分镜（${form.totalDuration}秒 ${form.ratio} ${form.resolution}）到 Seedance，预计耗时 1-3 分钟。是否继续？`,
      '确认提交',
      { confirmButtonText: '提交', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return // 用户取消
  }

  submitting.value = true
  try {
    const resp = await submitShotVideo({
      shots: finalShots,
      productImages: productFiles.value,
      modelImages: modelFiles.value,
      modelHasFace: form.modelHasFace,
      duration: form.totalDuration,
      ratio: form.ratio,
      resolution: form.resolution,
      productInfo: form.productInfo,
    })

    if (resp.success) {
      ElMessage.success('已提交，跳转视频生成页')
      router.push('/video')
    } else {
      ElMessage.error('提交失败')
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || getErrorMessage(e, '请重试')
    ElMessage.error('提交失败：' + msg)
  } finally {
    submitting.value = false
  }
}

// === 工具 ===
function purposeTagType(purpose: string): 'primary' | 'success' | 'warning' | 'info' {
  const p = (purpose || '').toLowerCase()
  if (p.includes('hook')) return 'warning'
  if (p.includes('detail')) return 'primary'
  if (p.includes('recall')) return 'success'
  return 'info'
}
</script>

<style scoped>
.video-shot-view {
  max-width: 1400px;
  margin: 0 auto;
}

.duration-control {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}
.duration-slider {
  flex: 1 1 200px;
  min-width: 0;
}
.duration-input {
  width: 110px;
  flex-shrink: 0;
}
.duration-unit {
  color: #909399;
  font-size: 13px;
  flex-shrink: 0;
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

.shots-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.loading-card {
  text-align: center;
  padding: 40px 20px;
}

.loading-card .spin {
  animation: spin 1.2s linear infinite;
}

.loading-card p {
  margin-top: 12px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.visual-style-card {
  flex-shrink: 0;
}

.visual-style-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 6px;
}

.shot-card-wrapper {
  width: 100%;
}

.shot-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.shot-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.shot-time {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  font-weight: 600;
}

.shot-form :deep(.el-form-item) {
  margin-bottom: 10px;
}

.shot-form :deep(.el-form-item__label) {
  font-size: 12px;
  padding-bottom: 4px;
}

.shot-duration-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.shot-total-hint {
  color: var(--el-text-color-secondary);
}

.submit-section {
  flex-shrink: 0;
}

.submit-section .hint-text {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.warn-text {
  color: var(--el-color-warning);
  font-weight: 600;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
