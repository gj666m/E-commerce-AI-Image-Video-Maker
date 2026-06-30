<!-- Prompt 工坊页：场景驱动结构化生成器（续15 升级）
     - 图片类 6 种 task_type：AI 返回 8 要素 → ElementCardsGrid 可编辑 → 本地拼装 → 工坊内生成
     - video（单段）：AI 智能扩写 → 编辑框 → 跳转 VideoGenView 预填
     - video_shots（分镜）：AI 分镜策划 → ShotsTable 可编辑 → 跳转 VideoShotView 预填 shots -->
<template>
  <div class="prompt-workshop-view">
    <div class="page-header">
      <h2 class="page-title">
        Prompt 工坊
        <el-icon class="help-icon" @click="goGuide('quick-image')"><QuestionFilled /></el-icon>
      </h2>
      <p class="page-desc">
        场景驱动结构化生成器：选任务类型 → AI 拆要素 → 改字段本地拼装 → 一键生成或跳转。
        图片类工坊内直接出图，视频类跳转专门视频页预填。
      </p>
    </div>

    <el-row :gutter="16">
      <!-- 左：编辑面板 -->
      <el-col :xs="24" :md="9">
        <el-card class="editor-card">
          <el-form label-position="top">
            <el-form-item label="任务类型">
              <el-select v-model="form.taskType" @change="onTaskTypeChange">
                <el-option-group label="图片类（工坊内生成）">
                  <el-option v-for="t in IMAGE_TASK_TYPES" :key="t.value" :label="t.label" :value="t.value" />
                </el-option-group>
                <el-option-group label="视频类（跳转预填）">
                  <el-option v-for="t in VIDEO_TASK_TYPES" :key="t.value" :label="t.label" :value="t.value" />
                </el-option-group>
              </el-select>
            </el-form-item>

            <!-- 图片类：比例 + 张数 -->
            <el-row v-if="isImageTask(form.taskType)" :gutter="12">
              <el-col :span="12">
                <el-form-item label="比例">
                  <el-select v-model="form.aspectRatio">
                    <el-option v-for="r in ASPECT_RATIOS" :key="r" :label="r" :value="r" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="张数">
                  <el-select v-model="form.count">
                    <el-option :value="1" label="1 张" />
                    <el-option :value="2" label="2 张" />
                    <el-option :value="3" label="3 张" />
                    <el-option :value="4" label="4 张" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <!-- video_shots：主题 + 总时长 -->
            <template v-else-if="form.taskType === 'video_shots'">
              <el-form-item>
                <template #label>
                  <span>主题描述</span>
                  <span class="enhance-wrap">
                    <EnhancePromptButton
                      :task-type="form.taskType"
                      :user-text="videoShotsTheme"
                      :duration="videoShotsTotalDuration"
                      size="small"
                      @enhanced="videoShotsTheme = $event"
                    />
                  </span>
                </template>
                <el-input
                  v-model="videoShotsTheme"
                  type="textarea"
                  :rows="3"
                  placeholder="如：夏日海边度假裙装展示，阳光、海风、慢走"
                />
              </el-form-item>
              <el-form-item label="总时长（秒）">
                <el-slider v-model="videoShotsTotalDuration" show-input :min="4" :max="15" style="min-width: 0" />
              </el-form-item>
            </template>

            <!-- video：描述 + 智能扩写 -->
            <el-form-item v-else>
              <template #label>
                <span>视频描述</span>
                <span class="enhance-wrap">
                  <EnhancePromptButton
                    :task-type="form.taskType"
                    :user-text="form.prompt"
                    :duration="videoDuration"
                    size="small"
                    @enhanced="form.prompt = $event"
                  />
                </span>
              </template>
              <el-input
                v-model="form.prompt"
                type="textarea"
                :rows="5"
                placeholder="在此描述视频画面，或点「智能创意」让 AI 帮你生成"
              />
            </el-form-item>

            <!-- 图片类的 Prompt 编辑框（仅在已有 elements 时显示，让用户能看到拼装结果） -->
            <el-form-item v-if="isImageTask(form.taskType)">
              <template #label>
                <span>Prompt（本地拼装 + 可手改）</span>
                <span class="enhance-wrap">
                  <el-button
                    size="small"
                    plain
                    type="primary"
                    :loading="enhancing"
                    @click="runStructuredEnhance"
                  >
                    <el-icon style="margin-right: 4px"><MagicStick /></el-icon>
                    智能创意（拆要素）
                  </el-button>
                </span>
              </template>
              <el-input
                v-model="form.prompt"
                type="textarea"
                :rows="6"
                placeholder="点击「智能创意（拆要素）」让 AI 拆 8 要素；改字段后自动同步"
              />
            </el-form-item>

            <!-- 图片类才有的模型 + 张数 + 参考图 -->
            <template v-if="isImageTask(form.taskType)">
              <el-form-item label="模型">
                <ModelSelector v-model="form.modelName" :models="modelList" />
              </el-form-item>

              <el-form-item label="参考图（可选，0-6 张）">
                <div class="ref-grid">
                  <div v-for="(img, idx) in refImages" :key="idx" class="ref-item">
                    <el-image :src="img" fit="contain" />
                    <el-button class="ref-remove" circle size="small" @click="removeRef(idx)">
                      <el-icon><Close /></el-icon>
                    </el-button>
                  </div>
                  <el-upload
                    v-if="refImages.length < 6"
                    :show-file-list="false"
                    accept="image/*"
                    :before-upload="onRefUpload"
                    class="ref-uploader"
                  >
                    <el-icon class="ref-uploader-icon"><Plus /></el-icon>
                  </el-upload>
                </div>
              </el-form-item>
            </template>

            <el-form-item>
              <!-- 图片类：生成 -->
              <el-button
                v-if="isImageTask(form.taskType)"
                type="primary"
                :loading="generating"
                :disabled="!canGenerate"
                @click="handleGenerate"
              >
                <el-icon style="margin-right: 4px"><Promotion /></el-icon>
                生成（{{ form.count }} 张）
              </el-button>

              <!-- video_shots：跳转分镜视频页 -->
              <el-button
                v-else-if="form.taskType === 'video_shots'"
                type="primary"
                :disabled="shots.length === 0"
                @click="jumpToShotVideo"
              >
                <el-icon style="margin-right: 4px"><Position /></el-icon>
                跳转到分镜视频页（{{ shots.length }} 镜）
              </el-button>

              <!-- video：跳转视频生成页 -->
              <el-button
                v-else
                type="primary"
                :disabled="!form.prompt.trim()"
                @click="jumpToVideo"
              >
                <el-icon style="margin-right: 4px"><Position /></el-icon>
                跳转到视频生成页
              </el-button>

              <el-button
                v-if="isImageTask(form.taskType)"
                plain
                :disabled="!form.prompt.trim()"
                @click="openSaveDialog"
              >
                <el-icon style="margin-right: 4px"><StarFilled /></el-icon>
                保存到 Prompt 库
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 中：要素卡片 / 分镜表 + 拼装预览 -->
      <el-col :xs="24" :md="10">
        <el-card v-if="isImageTask(form.taskType) && elements" class="structure-card">
          <ElementCardsGrid v-model="elements" />
        </el-card>

        <el-card v-else-if="form.taskType === 'video_shots'" class="structure-card">
          <ShotsTable v-model="shots" />
        </el-card>

        <el-empty
          v-else
          description="点击左栏「智能创意」按钮，AI 会帮你拆解要素 / 规划分镜"
        />

        <!-- 本地拼装预览（图片类 + video_shots 都展示） -->
        <el-card v-if="showPreview" class="preview-card">
          <template #header>
            <div class="preview-header">
              <span>本地拼装预览（只读）</span>
              <el-button size="small" plain @click="copyPreview">复制</el-button>
            </div>
          </template>
          <pre class="preview-text">{{ assembledPreview }}</pre>
        </el-card>
      </el-col>

      <!-- 右：结果 + 历史（仅图片类） -->
      <el-col v-if="isImageTask(form.taskType)" :xs="24" :md="5">
        <el-card class="result-card">
          <template #header>
            <div class="result-header">
              <span>生成结果</span>
              <span v-if="totalCost > 0" class="cost-hint">本次花费 ${{ totalCost.toFixed(4) }}</span>
            </div>
          </template>

          <el-empty v-if="cards.length === 0 && !generating" description="编辑 prompt 后点击生成" />

          <ResultCardManager
            v-else
            :cards="cards"
            :model-used="modelUsed"
            :total-cost="totalCost"
            :currency="currency"
            :models="modelList"
            @compare-model="handleCompareModel"
          />
        </el-card>

        <el-card v-if="history.length > 0" class="history-card">
          <template #header>
            <span>本次会话历史（点击回填到编辑框）</span>
          </template>
          <div class="history-list">
            <div
              v-for="(h, idx) in history"
              :key="idx"
              class="history-item"
              @click="loadHistory(h)"
            >
              <div class="history-meta">
                <el-tag size="small" :type="taskTagType(h.taskType)">{{ taskLabel(h.taskType) }}</el-tag>
                <span class="history-time">{{ h.time }}</span>
              </div>
              <div class="history-prompt">{{ h.prompt.slice(0, 100) }}{{ h.prompt.length > 100 ? '...' : '' }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 保存到 Prompt 库 -->
    <SaveToPromptLibraryDialog
      v-model="showSaveDialog"
      :initial="saveInitial"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Close, Promotion, Position, QuestionFilled, StarFilled, MagicStick } from '@element-plus/icons-vue'
import ModelSelector from '../components/ModelSelector.vue'
import ResultCardManager from '../components/ResultCardManager.vue'
import EnhancePromptButton from '../components/EnhancePromptButton.vue'
import ElementCardsGrid from '../components/ElementCardsGrid.vue'
import ShotsTable from '../components/ShotsTable.vue'
import SaveToPromptLibraryDialog from '../components/SaveToPromptLibraryDialog.vue'
import {
  generateImage,
  getModels,
  listPrompts,
  getErrorMessage,
  enhanceImagePromptStructured,
  planVideoShots,
} from '../api'
import type { VideoShot } from '../api'
import type { ModelInfo, ResultCard, PromptTaskType, PromptLibraryItem, PromptElements } from '../types'
import { assembleImagePrompt, assembleShotsPreview } from '../utils/promptAssembly'

const route = useRoute()
const router = useRouter()
function goGuide(anchor: string) {
  router.push({ path: '/user-guide', hash: `#${anchor}` })
}

// === 任务类型分组 ===
const IMAGE_TASK_TYPES: { value: PromptTaskType; label: string }[] = [
  { value: 'quick', label: '快速生图（通用）' },
  { value: 'outfit', label: '一键穿搭' },
  { value: 'model_gen', label: '模特生成' },
  { value: 'seed_grass', label: '种草图' },
  { value: 'product_main', label: '商品主图（白底）' },
  { value: 'aplus', label: 'A+ 图（杂志风）' },
]
const VIDEO_TASK_TYPES: { value: PromptTaskType; label: string }[] = [
  { value: 'video', label: '视频（单段）' },
  { value: 'video_shots', label: '视频（分镜）' },
]
const ALL_TASK_TYPES = [...IMAGE_TASK_TYPES, ...VIDEO_TASK_TYPES]
const ASPECT_RATIOS = ['1:1', '3:4', '4:3', '4:5', '9:16', '16:9']

const IMAGE_TASK_SET = new Set<string>(IMAGE_TASK_TYPES.map((t) => t.value))
function isImageTask(t: PromptTaskType): boolean {
  return IMAGE_TASK_SET.has(t)
}

function taskLabel(t: PromptTaskType) {
  return ALL_TASK_TYPES.find((x) => x.value === t)?.label || t
}
function taskTagType(t: PromptTaskType): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    quick: 'primary', outfit: 'success', model_gen: 'warning',
    seed_grass: 'info', product_main: 'danger', aplus: 'primary',
    video: 'warning', video_shots: 'danger',
  }
  return map[t] || 'info'
}

// === 表单状态 ===
const form = reactive({
  taskType: 'quick' as PromptTaskType,
  prompt: '',
  aspectRatio: '9:16',
  count: 1,
  modelName: 'seedream5',
})

// 结构化要素（图片类用，AI 智能创意后填充）
const elements = ref<PromptElements | null>(null)
// 分镜表（video_shots 用）
const shots = ref<VideoShot[]>([])
// video_shots 模式独立字段（不走 form.prompt）
const videoShotsTheme = ref('')
const videoShotsTotalDuration = ref(10)
// video 模式时长（仅供 EnhancePromptButton 显示用，跳转后用户在视频页改）
const videoDuration = ref(8)

const modelList = ref<ModelInfo[]>([])
const refImages = ref<string[]>([])      // base64 data URLs
const refFiles = ref<File[]>([])         // 对应 File（生成时传）

const generating = ref(false)
const enhancing = ref(false)
const cards = ref<ResultCard[]>([])
const modelUsed = ref('')
const totalCost = ref(0)
const currency = ref('$')

const canGenerate = computed(() => form.prompt.trim().length > 0)

// === 本地拼装预览 ===
const assembledPreview = computed(() => {
  if (isImageTask(form.taskType) && elements.value) {
    return assembleImagePrompt(elements.value, form.aspectRatio)
  }
  if (form.taskType === 'video_shots' && shots.value.length > 0) {
    return assembleShotsPreview(shots.value)
  }
  return ''
})

const showPreview = computed(() => {
  if (isImageTask(form.taskType)) return elements.value !== null
  if (form.taskType === 'video_shots') return shots.value.length > 0
  return false
})

// === 改 elements → 自动同步 form.prompt（覆盖式） ===
watch(elements, (val) => {
  if (val && isImageTask(form.taskType)) {
    form.prompt = assembleImagePrompt(val, form.aspectRatio)
  }
}, { deep: true })

// 改比例 → 重新拼装
watch(() => form.aspectRatio, () => {
  if (elements.value && isImageTask(form.taskType)) {
    form.prompt = assembleImagePrompt(elements.value, form.aspectRatio)
  }
})

// === 历史版本（仅图片类用） ===
interface HistoryItem {
  prompt: string
  taskType: PromptTaskType
  aspectRatio: string
  modelName: string
  time: string
}
const history = ref<HistoryItem[]>([])

onMounted(async () => {
  try {
    const resp = await getModels()
    modelList.value = (resp.models || []).filter((m) => m.available && m.name !== 'mock')
    if (modelList.value.length > 0 && !modelList.value.find((m) => m.name === form.modelName)) {
      form.modelName = modelList.value[0].name
    }
  } catch {
    ElMessage.error('获取模型列表失败')
  }

  // 从 query.prompt_id 加载 Prompt 库中的某条
  const pid = route.query.prompt_id
  if (typeof pid === 'string' && pid) {
    try {
      const resp = await listPrompts()
      const item = resp.items.find((x) => x.id === pid)
      if (item) loadFromLibrary(item)
    } catch {
      /* 忽略 */
    }
  }
})

function loadFromLibrary(item: PromptLibraryItem) {
  form.taskType = item.task_type
  form.prompt = item.full_prompt
  if (item.aspect_ratio) form.aspectRatio = item.aspect_ratio
  if (item.model_used) form.modelName = item.model_used
  ElMessage.success(`已加载：${item.title}`)
}

function onTaskTypeChange() {
  // 不同任务类型默认比例不同
  const defaults: Record<string, string> = {
    product_main: '1:1', aplus: '61:25', outfit: '3:4', seed_grass: '9:16',
  }
  if (defaults[form.taskType]) form.aspectRatio = defaults[form.taskType]

  // 切换任务类型时清空对应结构化状态
  if (isImageTask(form.taskType)) {
    shots.value = []
    videoShotsTheme.value = ''
  } else if (form.taskType === 'video_shots') {
    elements.value = null
    form.prompt = ''
  } else {
    // video 单段
    elements.value = null
    shots.value = []
  }
}

// 参考图上传：转 base64 + 保留 File
function onRefUpload(file: File): boolean {
  const reader = new FileReader()
  reader.onload = () => {
    refImages.value.push(reader.result as string)
    refFiles.value.push(file)
  }
  reader.readAsDataURL(file)
  return false
}

function removeRef(idx: number) {
  refImages.value.splice(idx, 1)
  refFiles.value.splice(idx, 1)
}

// === 图片类「智能创意」（结构化模式） ===
async function runStructuredEnhance() {
  if (!isImageTask(form.taskType)) return
  enhancing.value = true
  try {
    // userText 用 form.prompt 已有内容，或 elements.subject（二次优化时）
    const userText = form.prompt.trim() || elements.value?.subject || ''
    const result = await enhanceImagePromptStructured(
      userText,
      form.taskType,
      form.aspectRatio,
      refFiles.value[0],
    )
    if (!result.success || !result.structured) {
      ElMessage.error('智能创意返回为空')
      return
    }
    elements.value = result.structured.elements
    form.prompt = result.structured.prompt
    ElMessage.success('已拆解 8 要素，可在中部卡片编辑')
  } catch (e) {
    ElMessage.error('智能创意失败：' + getErrorMessage(e, '请重试'))
  } finally {
    enhancing.value = false
  }
}

// === video_shots：智能创意（按钮触发）后，调 planVideoShots 拉分镜 ===
watch(videoShotsTheme, async (newTheme, oldTheme) => {
  // 仅在 EnhancePromptButton 把空 theme 改成有内容时触发一次自动规划
  // 避免循环：只在用户从无到有填入主题时自动规划
  if (
    form.taskType === 'video_shots' &&
    newTheme && newTheme.trim() && !oldTheme &&
    shots.value.length === 0
  ) {
    await runPlanShots()
  }
})

async function runPlanShots() {
  if (form.taskType !== 'video_shots') return
  if (!videoShotsTheme.value.trim()) {
    ElMessage.warning('请先填写主题描述')
    return
  }
  try {
    const result = await planVideoShots({
      theme: videoShotsTheme.value.trim(),
      totalDuration: videoShotsTotalDuration.value,
      referenceImage: refFiles.value[0] || null,
    })
    if (!result.success || result.shots.length === 0) {
      ElMessage.error('AI 分镜规划返回为空')
      return
    }
    shots.value = result.shots.map((s, i) => ({ ...s, index: i + 1 }))
    ElMessage.success(`AI 规划完成，共 ${shots.value.length} 个分镜`)
  } catch (e) {
    ElMessage.error('AI 分镜规划失败：' + getErrorMessage(e, '请重试'))
  }
}

// 生成（图片类）
async function handleGenerate() {
  if (!canGenerate.value) return
  generating.value = true

  const initCards = Array.from({ length: form.count }, () => ({
    imageBase64: '',
    status: 'loading' as const,
    promptUsed: '',
  }))
  cards.value = initCards
  totalCost.value = 0
  modelUsed.value = ''

  try {
    const images = refFiles.value.slice()
    const data = await generateImage({
      task_type: form.taskType as 'quick' | 'outfit' | 'seed_grass' | 'product_main' | 'aplus',
      images: images.length > 0 ? images : undefined,
      description: form.prompt,
      model_name: form.modelName,
      aspect_ratio: form.aspectRatio,
      count: form.count,
    })

    cards.value = data.images.map((img) => ({
      imageBase64: img,
      status: 'success' as const,
      promptUsed: data.prompt_used,
    }))
    modelUsed.value = data.model_used
    totalCost.value = data.cost
    currency.value = data.currency || '$'

    // 推入历史
    history.value.unshift({
      prompt: form.prompt,
      taskType: form.taskType,
      aspectRatio: form.aspectRatio,
      modelName: form.modelName,
      time: new Date().toLocaleTimeString(),
    })
    if (history.value.length > 20) history.value.length = 20
  } catch (e) {
    cards.value = [{
      imageBase64: '',
      status: 'failed' as const,
      error: getErrorMessage(e, '生成失败'),
      promptUsed: '',
    }]
  } finally {
    generating.value = false
  }
}

// 多模型对比：换模型重新生成（prompt 不变）
async function handleCompareModel(_idx: number, newModel: string) {
  form.modelName = newModel
  await handleGenerate()
}

function loadHistory(h: HistoryItem) {
  form.prompt = h.prompt
  form.taskType = h.taskType
  form.aspectRatio = h.aspectRatio
  form.modelName = h.modelName
  ElMessage.success('已回填历史版本')
}

// === 跳转视频页（sessionStorage 预填） ===
function jumpToVideo() {
  if (!form.prompt.trim()) {
    ElMessage.warning('请先写描述')
    return
  }
  sessionStorage.setItem('workshop_prefill_video', form.prompt)
  ElMessage.success('已准备预填，跳转视频生成页')
  router.push('/video-gen')
}

function jumpToShotVideo() {
  if (shots.value.length === 0) {
    ElMessage.warning('请先生成分镜')
    return
  }
  sessionStorage.setItem('workshop_prefill_video_shots', JSON.stringify(shots.value))
  if (videoShotsTheme.value) {
    sessionStorage.setItem('workshop_prefill_video_shots_theme', videoShotsTheme.value)
  }
  ElMessage.success('已准备预填分镜，跳转分镜视频页')
  router.push('/video-shots')
}

// 复制预览
async function copyPreview() {
  if (!assembledPreview.value) return
  try {
    await navigator.clipboard.writeText(assembledPreview.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选中复制')
  }
}

// 保存到 Prompt 库
const showSaveDialog = ref(false)
const saveInitial = ref<any>(null)
function openSaveDialog() {
  saveInitial.value = {
    task_type: form.taskType,
    title: form.prompt.slice(0, 30) + (form.prompt.length > 30 ? '...' : ''),
    description: '',
    full_prompt: form.prompt,
    model_used: form.modelName,
    aspect_ratio: form.aspectRatio,
    sample_image: cards.value.find((c) => c.imageBase64)?.imageBase64 || '',
    sample_kind: 'image',
    tags: [],
    is_shared: false,
  }
  showSaveDialog.value = true
}
function onSaved() {
  showSaveDialog.value = false
  ElMessage.success('已保存到 Prompt 库')
}
</script>

<style scoped>
.prompt-workshop-view { padding: 16px; }
.page-header { margin-bottom: 16px; }
.page-title {
  margin: 0 0 4px 0;
  display: flex; align-items: center; gap: 8px;
  font-size: 22px; font-weight: 600;
}
.help-icon { cursor: pointer; color: #909399; font-size: 18px; }
.enhance-wrap { margin-left: 8px; }
.page-desc { margin: 0; color: #909399; font-size: 13px; }

.editor-card, .structure-card, .preview-card, .result-card, .history-card { margin-bottom: 12px; }

.preview-header {
  display: flex; justify-content: space-between; align-items: center;
}
.preview-text {
  margin: 0;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #303133;
  background: #fafafa;
  padding: 8px 10px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 240px;
  overflow-y: auto;
}

.result-header {
  display: flex; justify-content: space-between; align-items: center;
}
.cost-hint { color: #67c23a; font-size: 13px; }

.ref-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
  gap: 6px; width: 100%;
}
.ref-item {
  position: relative;
  aspect-ratio: 1;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
  background: #fafafa;
}
.ref-item .el-image { width: 100%; height: 100%; }
.ref-remove {
  position: absolute; top: 2px; right: 2px;
  background: rgba(255,255,255,0.85);
}
.ref-uploader {
  aspect-ratio: 1;
  border: 1px dashed #d9d9d9;
  border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
}
.ref-uploader:hover { border-color: #409eff; color: #409eff; }
.ref-uploader-icon { font-size: 22px; color: #909399; }

.history-list { display: flex; flex-direction: column; gap: 8px; }
.history-item {
  padding: 8px 10px;
  background: #fafafa;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid #ebeef5;
  transition: border-color 0.2s, background 0.2s;
}
.history-item:hover { border-color: #409eff; background: #f0f7ff; }
.history-meta {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 4px;
}
.history-time { color: #909399; font-size: 12px; }
.history-prompt {
  color: #606266; font-size: 13px;
  font-family: ui-monospace, monospace;
  line-height: 1.4;
  word-break: break-all;
}
</style>
