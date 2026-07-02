<template>
  <el-dialog v-model="visible" :title="`Prompt 库${taskType ? ' · ' + taskTypeLabel(taskType) : ''}`" width="720px" append-to-body>
    <div class="picker-toolbar">
      <el-input v-model="keyword" placeholder="搜索标题 / Prompt 关键词" clearable style="flex: 1">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filterShared" placeholder="来源" style="width: 130px">
        <el-option label="全部" value="" />
        <el-option label="我的" value="mine" />
        <el-option label="共享" value="shared" />
      </el-select>
    </div>

    <div v-loading="loading" class="picker-list">
      <el-empty v-if="!loading && filtered.length === 0" description="没有匹配的 Prompt" />
      <div
        v-for="item in filtered"
        :key="item.id"
        class="picker-item"
        @click="handlePick(item)"
      >
        <div class="thumb">
          <img
            v-if="item.sample_image && item.sample_kind === 'image'"
            :src="fileUrl(item.sample_image)"
            @error="onThumbError"
            alt=""
          />
          <video
            v-else-if="item.sample_image && item.sample_kind === 'video'"
            :src="fileUrl(item.sample_image)"
            preload="metadata"
            muted
          />
          <el-icon v-else :size="20"><Picture /></el-icon>
        </div>
        <div class="info">
          <div class="title-row">
            <span class="title">{{ item.title }}</span>
            <el-tag v-if="item.is_shared && !item.is_owner" size="small" type="success">共享</el-tag>
            <el-tag v-else-if="item.is_owner" size="small" type="info">我的</el-tag>
          </div>
          <p class="prompt-preview">{{ item.full_prompt }}</p>
          <div class="meta">
            <span v-if="item.model_used">{{ item.model_used }}</span>
            <span v-if="item.aspect_ratio">{{ item.aspect_ratio }}</span>
            <span>复用 {{ item.use_count }} 次</span>
          </div>
        </div>
        <el-button type="primary" size="small" plain>选用</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Picture } from '@element-plus/icons-vue'
import { listPrompts, markPromptUsed, getErrorMessage } from '../api'
import { fileUrl } from '@/utils/fileUrl'
import type { PromptLibraryItem, PromptTaskType } from '../types'

const props = defineProps<{
  modelValue: boolean
  /** 限定 task_type 筛选（不传则全部） */
  taskType?: PromptTaskType
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'pick', item: PromptLibraryItem): void
}>()

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v) fetchList()
})
watch(visible, (v) => emit('update:modelValue', v))

const items = ref<PromptLibraryItem[]>([])
const loading = ref(false)
const keyword = ref('')
const filterShared = ref<'' | 'mine' | 'shared'>('')

const TASK_TYPE_LABELS: Record<string, string> = {
  quick: '快速生图',
  outfit: '一键穿搭',
  model_gen: 'AI 生成模特',
  seed_grass: '种草图',
  product_main: '商品主图',
  aplus: 'A+ 图',
  video: '视频生成',
  video_shots: '分镜视频',
}

function taskTypeLabel(t?: string) {
  return t ? (TASK_TYPE_LABELS[t] || t) : ''
}

async function fetchList() {
  loading.value = true
  try {
    const data = await listPrompts(props.taskType)
    items.value = data.items
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '加载失败'))
  } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return items.value.filter((it) => {
    if (filterShared.value === 'mine' && !it.is_owner) return false
    if (filterShared.value === 'shared' && !(it.is_shared && !it.is_owner)) return false
    if (!kw) return true
    return (
      it.title.toLowerCase().includes(kw) ||
      it.full_prompt.toLowerCase().includes(kw) ||
      (it.description || '').toLowerCase().includes(kw)
    )
  })
})

function onThumbError(ev: Event) {
  ;(ev.target as HTMLImageElement).style.display = 'none'
}

async function handlePick(item: PromptLibraryItem) {
  try {
    await markPromptUsed(item.id)
  } catch {
    /* 不阻塞流程 */
  }
  ElMessage.success(`已套用「${item.title}」`)
  emit('pick', item)
  visible.value = false
}
</script>

<style scoped>
.picker-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.picker-list {
  max-height: 480px;
  overflow-y: auto;
}

.picker-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.picker-item:hover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.thumb {
  width: 80px;
  height: 60px;
  border-radius: 6px;
  overflow: hidden;
  background: var(--el-fill-color-light);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-placeholder);
  flex-shrink: 0;
}

.thumb img,
.thumb video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.info {
  flex: 1;
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}

.title {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.prompt-preview {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: var(--el-text-color-placeholder);
}
</style>
