<!-- Prompt 工坊页：编辑/调试/对比/保存 prompt 的工作台（图片类专用，视频有独立页） -->
<template>
  <div class="prompt-workshop-view">
    <div class="page-header">
      <h2 class="page-title">
        Prompt 工坊
        <el-icon class="help-icon" @click="goGuide('quick-image')"><QuestionFilled /></el-icon>
      </h2>
      <p class="page-desc">编辑 prompt → 智能创意 → 一键生成 → 多版本对比 → 保存到 Prompt 库。视频类请用专门的视频生成页。</p>
    </div>

    <el-row :gutter="16">
      <!-- 左：编辑面板 -->
      <el-col :xs="24" :md="10" :lg="9">
        <el-card class="editor-card">
          <el-form label-position="top">
            <el-form-item label="任务类型">
              <el-select v-model="form.taskType" @change="onTaskTypeChange">
                <el-option v-for="t in TASK_TYPES" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>

            <el-form-item>
              <template #label>
                <span>Prompt</span>
                <span class="enhance-wrap">
                  <EnhancePromptButton
                    :task-type="form.taskType"
                    :user-text="form.prompt"
                    :aspect-ratio="form.aspectRatio"
                    size="small"
                    @enhanced="form.prompt = $event"
                  />
                </span>
              </template>
              <el-input
                v-model="form.prompt"
                type="textarea"
                :rows="8"
                placeholder="在此编辑 prompt，或点「智能创意」让 AI 帮你生成专业 prompt"
              />
            </el-form-item>

            <el-row :gutter="12">
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

            <el-form-item>
              <el-button
                type="primary"
                :loading="generating"
                :disabled="!canGenerate"
                @click="handleGenerate"
              >
                <el-icon style="margin-right: 4px"><Promotion /></el-icon>
                生成（{{ form.count }} 张）
              </el-button>
              <el-button
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

      <!-- 右：结果 + 历史 -->
      <el-col :xs="24" :md="14" :lg="15">
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Close, Promotion, QuestionFilled, StarFilled } from '@element-plus/icons-vue'
import ModelSelector from '../components/ModelSelector.vue'
import ResultCardManager from '../components/ResultCardManager.vue'
import EnhancePromptButton from '../components/EnhancePromptButton.vue'
import SaveToPromptLibraryDialog from '../components/SaveToPromptLibraryDialog.vue'
import { generateImage, getModels, listPrompts, getErrorMessage } from '../api'
import type { ModelInfo, ResultCard, PromptTaskType, PromptLibraryItem } from '../types'

const route = useRoute()
const router = useRouter()
function goGuide(anchor: string) {
  router.push({ path: '/user-guide', hash: `#${anchor}` })
}

// 图片类 6 种（视频类有专门页面）
const TASK_TYPES: { value: PromptTaskType; label: string }[] = [
  { value: 'quick', label: '快速生图（通用）' },
  { value: 'outfit', label: '一键穿搭' },
  { value: 'model_gen', label: '模特生成' },
  { value: 'seed_grass', label: '种草图' },
  { value: 'product_main', label: '商品主图（白底）' },
  { value: 'aplus', label: 'A+ 图（杂志风）' },
]
const ASPECT_RATIOS = ['1:1', '3:4', '4:3', '4:5', '9:16', '16:9']

function taskLabel(t: PromptTaskType) {
  return TASK_TYPES.find((x) => x.value === t)?.label || t
}
function taskTagType(t: PromptTaskType): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    quick: 'primary', outfit: 'success', model_gen: 'warning',
    seed_grass: 'info', product_main: 'danger', aplus: 'primary',
  }
  return map[t] || 'info'
}

const form = reactive({
  taskType: 'quick' as PromptTaskType,
  prompt: '',
  aspectRatio: '9:16',
  count: 1,
  modelName: 'seedream5',
})

const modelList = ref<ModelInfo[]>([])
const refImages = ref<string[]>([])      // base64 data URLs
const refFiles = ref<File[]>([])         // 对应 File（生成时传）

const generating = ref(false)
const cards = ref<ResultCard[]>([])
const modelUsed = ref('')
const totalCost = ref(0)
const currency = ref('$')

const canGenerate = computed(() => form.prompt.trim().length > 0)

// 历史版本（本地，刷新清空）
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
}

// 参考图上传：转 base64 + 保留 File
function onRefUpload(file: File): boolean {
  const reader = new FileReader()
  reader.onload = () => {
    refImages.value.push(reader.result as string)
    refFiles.value.push(file)
  }
  reader.readAsDataURL(file)
  return false // 阻止 el-upload 自动上传
}

function removeRef(idx: number) {
  refImages.value.splice(idx, 1)
  refFiles.value.splice(idx, 1)
}

// 生成
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

.editor-card, .result-card, .history-card { margin-bottom: 12px; }

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
