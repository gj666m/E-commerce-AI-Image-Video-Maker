<template>
  <div class="result-card-manager">
    <div class="cards-header">
      <span class="cards-title">生成结果（{{ cards.length }} 张）</span>
      <div class="meta-info">
        <el-tag size="small">{{ modelUsed }}</el-tag>
        <el-tag size="small" type="info">{{ currency }}{{ totalCost.toFixed(2) }}</el-tag>
        <el-button
          v-if="successCount > 1"
          size="small"
          type="primary"
          plain
          @click="goVideoAll"
        >
          全部传视频({{ successCount }})
        </el-button>
      </div>
    </div>

    <div class="cards-grid">
      <div
        v-for="(card, index) in cards"
        :key="index"
        class="result-card"
        :class="{ 'is-loading': card.status === 'loading', 'is-failed': card.status === 'failed' }"
      >
        <!-- 图片区域 -->
        <div class="card-image-area">
          <el-image
            v-if="card.status === 'success'"
            :src="'data:image/png;base64,' + card.imageBase64"
            fit="contain"
            :preview-src-list="allSuccessImages"
            :initial-index="successIndexMap[index] ?? 0"
            class="card-img"
          />
          <div v-else-if="card.status === 'loading'" class="card-placeholder">
            <el-icon :size="32" class="is-loading"><Loading /></el-icon>
            <p>生成中...</p>
          </div>
          <div v-else class="card-placeholder card-error">
            <el-icon :size="32" color="#f56c6c"><CircleCloseFilled /></el-icon>
            <p>{{ card.error || '生成失败' }}</p>
          </div>
          <span class="card-number">{{ labels?.[index] || '#' + (index + 1) }}</span>
        </div>

        <!-- 操作按钮 -->
        <div class="card-actions">
          <el-tooltip content="重试" placement="top">
            <el-button size="small" :loading="card.status === 'loading'" @click="$emit('retry', index)">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="编辑 Prompt" placement="top">
            <el-button size="small" @click="openEditPrompt(index)">
              <el-icon><EditPen /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="下载" placement="top">
            <el-button size="small" :disabled="card.status !== 'success'" @click="downloadCard(index)">
              <el-icon><Download /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="生成视频" placement="top">
            <el-button size="small" :disabled="card.status !== 'success'" @click="goVideo(index)">
              <el-icon><VideoCamera /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="换模型对比" placement="top" v-if="models.length > 0">
            <el-button size="small" type="warning" plain :disabled="card.status !== 'success'" @click="openCompareDialog(index)">
              <el-icon><Sort /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip v-if="showSaveModel" content="保存到模特库" placement="top">
            <el-button size="small" type="success" :disabled="card.status !== 'success'" @click="$emit('saveModel', index)">
              <el-icon><Star /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="删除" placement="top">
            <el-button size="small" type="danger" plain @click="$emit('remove', index)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>
    </div>

    <!-- Prompt 编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑 Prompt" width="640px">
      <div class="edit-section">
        <label class="edit-label">当前 Prompt（参考）</label>
        <pre class="prompt-ref">{{ editOriginalPrompt }}</pre>
      </div>
      <div class="edit-section" style="margin-top: 16px;">
        <label class="edit-label">额外指令</label>
        <el-input
          v-model="editExtra"
          type="textarea"
          :rows="4"
          placeholder="输入额外要求，如「换为户外背景」「改变姿势为坐姿」"
        />
      </div>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEditPrompt">重新生成</el-button>
      </template>
    </el-dialog>

    <!-- 换模型对比弹窗 -->
    <el-dialog v-model="compareDialogVisible" title="换模型对比" width="480px">
      <p style="color: #909399; margin-bottom: 12px;">选择一个不同的模型，用相同参数重新生成</p>
      <el-select v-model="compareModelName" placeholder="选择模型" style="width: 100%">
        <el-option
          v-for="m in models"
          :key="m.name"
          :label="m.display_name"
          :value="m.name"
          :disabled="!m.available"
        />
      </el-select>
      <template #footer>
        <el-button @click="compareDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!compareModelName" @click="submitCompare">对比生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Loading, CircleCloseFilled, Refresh, EditPen,
  Download, VideoCamera, Star, Delete, Sort,
} from '@element-plus/icons-vue'
import type { ResultCard, ModelInfo } from '../types'

const props = withDefaults(defineProps<{
  cards: ResultCard[]
  modelUsed: string
  totalCost: number
  currency?: string
  showSaveModel?: boolean
  labels?: string[]
  models?: ModelInfo[]
}>(), {
  showSaveModel: false,
  currency: '¥',
  models: () => [],
})

const emit = defineEmits<{
  retry: [index: number]
  retryWithPrompt: [index: number, extraPrompt: string]
  remove: [index: number]
  saveModel: [index: number]
  compareModel: [index: number, modelName: string]
}>()

const router = useRouter()

// 预览列表：只包含成功的图片
const allSuccessImages = computed(() =>
  props.cards
    .filter(c => c.status === 'success')
    .map(c => 'data:image/png;base64,' + c.imageBase64)
)

// 卡片 index → 成功图片列表 index 的映射
const successIndexMap = computed(() => {
  const map: Record<number, number> = {}
  let si = 0
  props.cards.forEach((card, i) => {
    if (card.status === 'success') {
      map[i] = si++
    }
  })
  return map
})

// 成功图片数量
const successCount = computed(() =>
  props.cards.filter(c => c.status === 'success').length
)

// 编辑 Prompt
const editDialogVisible = ref(false)
const editCardIndex = ref(0)
const editOriginalPrompt = ref('')
const editExtra = ref('')

function openEditPrompt(index: number) {
  editCardIndex.value = index
  editOriginalPrompt.value = props.cards[index].promptUsed || ''
  editExtra.value = ''
  editDialogVisible.value = true
}

function submitEditPrompt() {
  emit('retryWithPrompt', editCardIndex.value, editExtra.value)
  editDialogVisible.value = false
}

// 换模型对比
const compareDialogVisible = ref(false)
const compareCardIndex = ref(0)
const compareModelName = ref('')

function openCompareDialog(index: number) {
  compareCardIndex.value = index
  compareModelName.value = ''
  compareDialogVisible.value = true
}

function submitCompare() {
  if (!compareModelName.value) return
  emit('compareModel', compareCardIndex.value, compareModelName.value)
  compareDialogVisible.value = false
}

// 下载
function downloadCard(index: number) {
  const card = props.cards[index]
  if (card.status !== 'success') return
  const link = document.createElement('a')
  link.href = 'data:image/png;base64,' + card.imageBase64
  link.download = `generated_${index + 1}.png`
  link.click()
}

// 跳转视频生成（单张）
function goVideo(index: number) {
  const card = props.cards[index]
  if (card.status !== 'success') return
  sessionStorage.setItem('video_ref_images', JSON.stringify([card.imageBase64]))
  router.push('/video')
}

// 批量传视频（所有成功的图片）
function goVideoAll() {
  const images = props.cards
    .filter(c => c.status === 'success')
    .map(c => c.imageBase64)
  if (images.length === 0) return
  sessionStorage.setItem('video_ref_images', JSON.stringify(images))
  router.push('/video')
}
</script>

<style scoped>
.cards-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.cards-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.meta-info {
  display: flex;
  gap: 8px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.result-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.result-card:hover {
  border-color: #409eff;
}

.result-card.is-loading {
  border-color: #e6a23c;
}

.result-card.is-failed {
  border-color: #f56c6c;
}

.card-image-area {
  position: relative;
  background: #fafafa;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-img {
  width: 100%;
  height: 280px;
}

.card-placeholder {
  text-align: center;
  color: #909399;
  padding: 40px 20px;
}

.card-placeholder p {
  margin-top: 8px;
  font-size: 13px;
}

.card-error {
  color: #f56c6c;
}

.card-number {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.card-actions {
  display: flex;
  gap: 4px;
  padding: 8px;
  flex-wrap: wrap;
  justify-content: center;
  border-top: 1px solid #ebeef5;
}

.card-actions .el-button {
  padding: 5px 8px;
}

/* 编辑 Prompt 弹窗 */
.edit-section {
  display: flex;
  flex-direction: column;
}

.edit-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 6px;
  font-weight: 500;
}

.prompt-ref {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;
}
</style>
