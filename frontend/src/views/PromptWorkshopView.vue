<!-- Prompt 工坊页：纯 prompt 输出工具（续16 重构）
     定位：AI 帮你写专业 prompt 的地方。不在工坊内生成图/视频，只输出结构化专业 prompt。
     - 图片类 6 种：AI 拆 8 要素 → ElementCardsGrid 可编辑 → 本地拼装中文 prompt → 跳转 QuickImage 预填
     - video（单段）：AI 智能扩写中文 prompt → 跳转 VideoGenView 预填
     - video_shots（分镜）：AI 分镜策划 → ShotsTable 可编辑 → 跳转 VideoShotView 预填
     - 所有任务类型支持参考图上传（辅助 AI 写更贴商品的 prompt，不参与生成） -->
<template>
  <div class="prompt-workshop-view">
    <div class="page-header">
      <h2 class="page-title">
        Prompt 工坊
        <el-icon class="help-icon" @click="goGuide('quick-image')"><QuestionFilled /></el-icon>
      </h2>
      <p class="page-desc">
        AI 帮你写专业 prompt：选任务类型 → 传参考图（可选）→ AI 拆要素 → 改字段本地拼装 → 复制 / 存库 / 跳转生成页。
        工坊只加工 prompt，生成在专门页面。
      </p>
    </div>

    <el-row :gutter="16">
      <!-- 左：输入面板 -->
      <el-col :xs="24" :md="11">
        <el-card class="editor-card">
          <el-form label-position="top">
            <el-form-item label="任务类型">
              <el-select v-model="form.taskType" @change="onTaskTypeChange">
                <el-option-group label="图片类（跳转 QuickImage）">
                  <el-option v-for="t in IMAGE_TASK_TYPES" :key="t.value" :label="t.label" :value="t.value" />
                </el-option-group>
                <el-option-group label="视频类（跳转视频生成页）">
                  <el-option v-for="t in VIDEO_TASK_TYPES" :key="t.value" :label="t.label" :value="t.value" />
                </el-option-group>
              </el-select>
            </el-form-item>

            <!-- 图片类：比例 -->
            <el-form-item v-if="isImageTask(form.taskType)" label="比例">
              <el-select v-model="form.aspectRatio">
                <el-option v-for="r in ASPECT_RATIOS" :key="r" :label="r" :value="r" />
              </el-select>
            </el-form-item>

            <!-- 图片类：描述 + 智能创意（拆要素） -->
            <el-form-item v-if="isImageTask(form.taskType)">
              <template #label>
                <span>简单描述你的想法（可选）</span>
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
                v-model="imageUserText"
                type="textarea"
                :rows="3"
                placeholder="如：夏日海边度假裙装，阳光、海风、慢走。留空则 AI 完全自由创意"
              />
            </el-form-item>

            <!-- video：描述 + 智能扩写 -->
            <el-form-item v-else-if="form.taskType === 'video'">
              <template #label>
                <span>视频描述</span>
                <span class="enhance-wrap">
                  <EnhancePromptButton
                    :task-type="form.taskType"
                    :user-text="form.prompt"
                    :duration="videoDuration"
                    :image="refFiles[0] || null"
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

            <!-- video_shots：主题 + 总时长 + 智能创意 -->
            <template v-else-if="form.taskType === 'video_shots'">
              <el-form-item>
                <template #label>
                  <span>主题描述</span>
                  <span class="enhance-wrap">
                    <EnhancePromptButton
                      :task-type="form.taskType"
                      :user-text="videoShotsTheme"
                      :duration="videoShotsTotalDuration"
                      :image="refFiles[0] || null"
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
              <el-form-item>
                <el-button type="primary" plain :loading="planningShots" @click="runPlanShots">
                  <el-icon style="margin-right: 4px"><MagicStick /></el-icon>
                  AI 规划分镜
                </el-button>
              </el-form-item>
            </template>

            <!-- 参考图（所有任务类型通用，辅助 AI 写 prompt） -->
            <el-form-item label="参考图（可选，0-6 张，辅助 AI 写更贴商品的 prompt）">
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

            <!-- 三按钮：复制 / 保存到库 / 跳转 -->
            <el-form-item>
              <el-button plain :disabled="!finalPrompt.trim()" @click="copyPrompt">
                <el-icon style="margin-right: 4px"><CopyDocument /></el-icon>
                复制 Prompt
              </el-button>
              <el-button plain :disabled="!finalPrompt.trim()" @click="openSaveDialog">
                <el-icon style="margin-right: 4px"><StarFilled /></el-icon>
                保存到 Prompt 库
              </el-button>
              <el-button
                type="primary"
                :disabled="!canJump"
                @click="jumpToGenerate"
              >
                <el-icon style="margin-right: 4px"><Position /></el-icon>
                {{ jumpLabel }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右：结构化输出区 -->
      <el-col :xs="24" :md="13">
        <!-- 图片类：要素卡片 -->
        <el-card v-if="isImageTask(form.taskType) && elements" class="structure-card">
          <template #header>
            <span>要素卡片（改字段后下方 prompt 实时拼装）</span>
          </template>
          <ElementCardsGrid v-model="elements" />
        </el-card>

        <!-- video_shots：分镜表 -->
        <el-card v-else-if="form.taskType === 'video_shots' && shots.length > 0" class="structure-card">
          <template #header>
            <span>分镜表（行可编辑 / 增删）</span>
          </template>
          <ShotsTable v-model="shots" />
        </el-card>

        <el-empty
          v-else
          description="点左侧「智能创意」按钮，AI 会帮你拆解要素 / 规划分镜"
        />

        <!-- 最终 prompt 预览（所有任务类型，有内容时显示） -->
        <el-card v-if="finalPrompt.trim()" class="preview-card">
          <template #header>
            <div class="preview-header">
              <span>最终 Prompt（{{ isImageTask(form.taskType) ? '本地拼装' : 'AI 生成' }}）</span>
              <el-button size="small" plain @click="copyPrompt">复制</el-button>
            </div>
          </template>
          <pre class="preview-text">{{ finalPrompt }}</pre>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Close, Position, QuestionFilled, StarFilled, MagicStick, CopyDocument } from '@element-plus/icons-vue'
import EnhancePromptButton from '../components/EnhancePromptButton.vue'
import ElementCardsGrid from '../components/ElementCardsGrid.vue'
import ShotsTable from '../components/ShotsTable.vue'
import SaveToPromptLibraryDialog from '../components/SaveToPromptLibraryDialog.vue'
import {
  listPrompts,
  getErrorMessage,
  enhanceImagePromptStructured,
  planVideoShots,
} from '../api'
import type { VideoShot } from '../api'
import type { PromptTaskType, PromptLibraryItem, PromptElements } from '../types'
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
const ASPECT_RATIOS = ['1:1', '3:4', '4:3', '4:5', '9:16', '16:9']

const IMAGE_TASK_SET = new Set<string>(IMAGE_TASK_TYPES.map((t) => t.value))
function isImageTask(t: PromptTaskType): boolean {
  return IMAGE_TASK_SET.has(t)
}

// === 表单状态 ===
const form = reactive({
  taskType: 'quick' as PromptTaskType,
  prompt: '',            // video 单段直接用；图片类由 elements 拼装覆盖
  aspectRatio: '9:16',
})

// 图片类独立状态
const imageUserText = ref('')       // 图片类描述框（给 AI 拆要素用）
const elements = ref<PromptElements | null>(null)

// video_shots 独立状态
const videoShotsTheme = ref('')
const videoShotsTotalDuration = ref(10)
const shots = ref<VideoShot[]>([])

// video 单段时长（仅供 EnhancePromptButton 显示用）
const videoDuration = ref(8)

// 参考图（所有任务类型通用）
const refImages = ref<string[]>([])      // base64 data URLs（预览）
const refFiles = ref<File[]>([])         // 对应 File（调 AI 时传）

const enhancing = ref(false)
const planningShots = ref(false)

// === 最终 prompt（右栏预览 + 复制/存库/跳转的数据源） ===
const finalPrompt = computed(() => {
  if (isImageTask(form.taskType)) {
    return elements.value ? assembleImagePrompt(elements.value, form.aspectRatio) : ''
  }
  if (form.taskType === 'video_shots') {
    return shots.value.length > 0 ? assembleShotsPreview(shots.value) : ''
  }
  // video 单段
  return form.prompt
})

// === 跳转可用性 + 按钮文案 ===
const canJump = computed(() => {
  if (isImageTask(form.taskType)) return elements.value !== null
  if (form.taskType === 'video_shots') return shots.value.length > 0
  return form.prompt.trim().length > 0
})
const jumpLabel = computed(() => {
  if (isImageTask(form.taskType)) return '跳转 QuickImage 生成'
  if (form.taskType === 'video_shots') return `跳转分镜视频页（${shots.value.length} 镜）`
  return '跳转视频生成页'
})

// === 改 elements/比例 → 自动重拼装（finalPrompt computed 自动响应，无需手动同步） ===
// 改比例仅影响图片类拼装，finalPrompt 已依赖 form.aspectRatio，自动响应

onMounted(() => {
  // 从 query.prompt_id 加载 Prompt 库中的某条（预填）
  const pid = route.query.prompt_id
  if (typeof pid === 'string' && pid) {
    listPrompts()
      .then((resp) => {
        const item = resp.items.find((x) => x.id === pid)
        if (item) loadFromLibrary(item)
      })
      .catch(() => { /* 忽略 */ })
  }
})

function loadFromLibrary(item: PromptLibraryItem) {
  form.taskType = item.task_type
  form.prompt = item.full_prompt
  if (item.aspect_ratio) form.aspectRatio = item.aspect_ratio
  // 图片类：把 full_prompt 作为 userText 起点，用户可再点「智能创意」重新拆
  if (isImageTask(form.taskType)) {
    imageUserText.value = item.full_prompt
    elements.value = null
  }
  ElMessage.success(`已加载：${item.title}`)
}

function onTaskTypeChange() {
  const defaults: Record<string, string> = {
    product_main: '1:1', aplus: '4:5', outfit: '3:4', seed_grass: '9:16',
  }
  if (defaults[form.taskType]) form.aspectRatio = defaults[form.taskType]

  // 切换任务类型时清空对应结构化状态
  if (isImageTask(form.taskType)) {
    shots.value = []
    videoShotsTheme.value = ''
    form.prompt = ''
  } else if (form.taskType === 'video_shots') {
    elements.value = null
    imageUserText.value = ''
    form.prompt = ''
  } else {
    // video 单段
    elements.value = null
    imageUserText.value = ''
    shots.value = []
  }
}

// 参考图上传
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
    const userText = imageUserText.value.trim() || elements.value?.subject || ''
    const result = await enhanceImagePromptStructured(
      userText,
      form.taskType,
      form.aspectRatio,
      refFiles.value[0] || null,
    )
    if (!result.success || !result.structured) {
      ElMessage.error('智能创意返回为空')
      return
    }
    elements.value = result.structured.elements
    ElMessage.success('已拆解 8 要素，可在右侧卡片编辑')
  } catch (e) {
    ElMessage.error('智能创意失败：' + getErrorMessage(e, '请重试'))
  } finally {
    enhancing.value = false
  }
}

// === video_shots：AI 规划分镜 ===
async function runPlanShots() {
  if (form.taskType !== 'video_shots') return
  if (!videoShotsTheme.value.trim()) {
    ElMessage.warning('请先填写主题描述')
    return
  }
  planningShots.value = true
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
  } finally {
    planningShots.value = false
  }
}

// === 跳转生成页（sessionStorage 预填） ===
function jumpToGenerate() {
  if (!canJump.value) return
  if (isImageTask(form.taskType)) {
    sessionStorage.setItem('workshop_prefill_image', finalPrompt.value)
    if (form.aspectRatio) sessionStorage.setItem('workshop_prefill_image_ratio', form.aspectRatio)
    ElMessage.success('已准备预填，跳转 QuickImage')
    router.push('/quick-image')
    return
  }
  if (form.taskType === 'video_shots') {
    sessionStorage.setItem('workshop_prefill_video_shots', JSON.stringify(shots.value))
    if (videoShotsTheme.value) {
      sessionStorage.setItem('workshop_prefill_video_shots_theme', videoShotsTheme.value)
    }
    ElMessage.success('已准备预填分镜，跳转分镜视频页')
    router.push('/video-shots')
    return
  }
  // video 单段
  sessionStorage.setItem('workshop_prefill_video', form.prompt)
  ElMessage.success('已准备预填，跳转视频生成页')
  router.push('/video')
}

// 复制 prompt
async function copyPrompt() {
  if (!finalPrompt.value.trim()) return
  try {
    await navigator.clipboard.writeText(finalPrompt.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选中复制')
  }
}

// 保存到 Prompt 库
const showSaveDialog = ref(false)
const saveInitial = ref<any>(null)
function openSaveDialog() {
  const p = finalPrompt.value
  if (!p.trim()) return
  saveInitial.value = {
    task_type: form.taskType,
    title: p.slice(0, 30) + (p.length > 30 ? '...' : ''),
    description: '',
    full_prompt: p,
    model_used: '',
    aspect_ratio: form.aspectRatio,
    sample_image: '',
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

.editor-card, .structure-card, .preview-card { margin-bottom: 12px; }

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
  max-height: 320px;
  overflow-y: auto;
}

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
</style>
