<template>
  <div class="prompt-library">
    <div class="page-header">
      <div>
        <h2>Prompt 复用库</h2>
        <p class="hint">收藏效果好的 Prompt 供日后复用，减少重复试错成本</p>
      </div>
      <div class="header-actions">
        <el-select v-model="filterTaskType" placeholder="全部类型" clearable style="width: 160px" @change="fetchList">
          <el-option v-for="t in taskTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-button @click="fetchList" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-empty v-if="!loading && items.length === 0" description="还没有收藏任何 Prompt，去历史页点⭐收藏一个吧" />

    <div v-else class="grid">
      <div v-for="item in items" :key="item.id" class="card">
        <!-- 缩略图 -->
        <div class="thumb-wrap">
          <img
            v-if="item.sample_image && item.sample_kind === 'image'"
            :src="fileUrl(item.sample_image)"
            class="thumb"
            @error="onThumbError($event)"
            alt=""
          />
          <video
            v-else-if="item.sample_image && item.sample_kind === 'video'"
            :src="fileUrl(item.sample_image)"
            class="thumb"
            preload="metadata"
            muted
          />
          <div v-else class="thumb thumb-placeholder">
            <el-icon :size="32"><Picture /></el-icon>
          </div>
          <el-tag v-if="item.is_shared" size="small" type="success" class="shared-tag">共享</el-tag>
          <el-tag v-else size="small" type="info" class="shared-tag">私有</el-tag>
        </div>

        <!-- 内容 -->
        <div class="card-body">
          <div class="card-title-row">
            <h4>{{ item.title }}</h4>
            <el-tag size="small">{{ taskTypeLabel(item.task_type) }}</el-tag>
          </div>
          <p v-if="item.description" class="desc">{{ item.description }}</p>

          <div class="meta-row">
            <span v-if="item.model_used" class="meta-item">模型: {{ item.model_used }}</span>
            <span v-if="item.aspect_ratio" class="meta-item">比例: {{ item.aspect_ratio }}</span>
            <span class="meta-item">复用 {{ item.use_count }} 次</span>
          </div>

          <div v-if="item.tags?.length" class="tags-row">
            <el-tag v-for="t in item.tags" :key="t" size="small" effect="plain">{{ t }}</el-tag>
          </div>

          <details class="prompt-detail">
            <summary>查看完整 Prompt</summary>
            <pre>{{ item.full_prompt }}</pre>
          </details>

          <div class="meta-footer">
            <span class="owner">{{ item.is_owner ? '我' : item.owner_name }} · {{ formatTime(item.created_at) }}</span>
            <div class="actions">
              <el-button size="small" text @click="openInWorkshop(item)" v-if="!isVideoTask(item.task_type)">
                <el-icon><MagicStick /></el-icon>在工坊打开
              </el-button>
              <el-button size="small" text @click="copyPrompt(item)">
                <el-icon><CopyDocument /></el-icon>复制
              </el-button>
              <el-button v-if="item.is_owner" size="small" text @click="openEdit(item)">
                <el-icon><Edit /></el-icon>编辑
              </el-button>
              <el-button v-if="item.is_owner" size="small" text @click="toggleShare(item)">
                {{ item.is_shared ? '取消共享' : '设为共享' }}
              </el-button>
              <el-button v-if="item.is_owner || isAdmin" size="small" text type="danger" @click="handleDelete(item)">
                <el-icon><Delete /></el-icon>删除
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="showEdit" title="编辑 Prompt" width="500px">
      <el-form label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" maxlength="100" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
        <el-form-item label="完整 Prompt">
          <el-input v-model="editForm.full_prompt" type="textarea" :rows="6" />
        </el-form-item>
        <el-form-item label="标签">
          <div class="tag-editor">
            <el-tag
              v-for="(t, idx) in editForm.tags"
              :key="idx"
              closable
              size="small"
              @close="editForm.tags!.splice(idx, 1)"
            >{{ t }}</el-tag>
            <el-input
              v-if="tagInputVisible"
              v-model="tagInputValue"
              ref="tagInputRef"
              size="small"
              style="width: 100px"
              @keyup.enter="addTag"
              @blur="addTag"
            />
            <el-button v-else size="small" @click="showTagInput">+ 标签</el-button>
          </div>
        </el-form-item>
        <el-form-item label="共享">
          <el-switch v-model="editForm.is_shared" />
          <span class="hint" style="margin-left: 8px">开启后全员可见</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh, Picture, CopyDocument, Edit, Delete, MagicStick,
} from '@element-plus/icons-vue'
import { listPrompts, updatePrompt, deletePrompt, getErrorMessage } from '../api'
import type { PromptLibraryItem, PromptTaskType, UpdatePromptPayload } from '../types'
import { useAuth } from '../composables/useAuth'
import { fileUrl } from '../utils/fileUrl'

const { isAdmin } = useAuth()
const router = useRouter()

// 视频类不能在工坊打开（工坊只做图片）
function isVideoTask(t: PromptTaskType): boolean {
  return t === 'video' || t === 'video_shots'
}
function openInWorkshop(item: PromptLibraryItem) {
  router.push({ path: '/prompt-workshop', query: { prompt_id: item.id } })
}

const items = ref<PromptLibraryItem[]>([])
const loading = ref(false)
const filterTaskType = ref<PromptTaskType | ''>('')

const taskTypeOptions: { value: PromptTaskType; label: string }[] = [
  { value: 'quick', label: '快速生图' },
  { value: 'outfit', label: '一键穿搭' },
  { value: 'model_gen', label: 'AI 生成模特' },
  { value: 'seed_grass', label: '种草图' },
  { value: 'product_main', label: '商品主图' },
  { value: 'aplus', label: 'A+ 图' },
  { value: 'video', label: '视频生成' },
  { value: 'video_shots', label: '分镜视频' },
]

function taskTypeLabel(t: string): string {
  return taskTypeOptions.find((o) => o.value === t)?.label || t
}

function formatTime(s: string): string {
  // 后端 localtime 字符串已经够用
  return s
}

async function fetchList() {
  loading.value = true
  try {
    const data = await listPrompts(filterTaskType.value || undefined)
    items.value = data.items
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '加载失败'))
  } finally {
    loading.value = false
  }
}

function onThumbError(ev: Event) {
  // 文件过期等情况，隐藏图片
  const img = ev.target as HTMLImageElement
  img.style.display = 'none'
}

async function copyPrompt(item: PromptLibraryItem) {
  try {
    await navigator.clipboard.writeText(item.full_prompt)
    ElMessage.success('已复制完整 Prompt')
  } catch {
    ElMessage.warning('复制失败，请手动选择复制')
  }
}

// ====== 编辑 ======
const showEdit = ref(false)
const saving = ref(false)
const editForm = ref<UpdatePromptPayload & { tags?: string[] }>({})
const editingId = ref('')

// 标签输入
const tagInputVisible = ref(false)
const tagInputValue = ref('')
const tagInputRef = ref<{ focus: () => void } | null>(null)

function showTagInput() {
  tagInputVisible.value = true
  nextTick(() => tagInputRef.value?.focus())
}

function addTag() {
  const v = tagInputValue.value.trim()
  if (v && !editForm.value.tags?.includes(v)) {
    editForm.value.tags = [...(editForm.value.tags || []), v]
  }
  tagInputVisible.value = false
  tagInputValue.value = ''
}

function openEdit(item: PromptLibraryItem) {
  editingId.value = item.id
  editForm.value = {
    title: item.title,
    description: item.description || '',
    full_prompt: item.full_prompt,
    tags: [...(item.tags || [])],
    is_shared: item.is_shared,
  }
  showEdit.value = true
}

async function saveEdit() {
  if (!editForm.value.title?.trim()) {
    ElMessage.warning('标题不能为空')
    return
  }
  saving.value = true
  try {
    await updatePrompt(editingId.value, editForm.value)
    ElMessage.success('已保存')
    showEdit.value = false
    await fetchList()
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function toggleShare(item: PromptLibraryItem) {
  try {
    await updatePrompt(item.id, { is_shared: !item.is_shared })
    ElMessage.success(item.is_shared ? '已设为私有' : '已共享给全员')
    await fetchList()
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '操作失败'))
  }
}

async function handleDelete(item: PromptLibraryItem) {
  try {
    await ElMessageBox.confirm(`确定删除 Prompt 「${item.title}」？`, '确认', { type: 'warning' })
    await deletePrompt(item.id)
    ElMessage.success('已删除')
    await fetchList()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(getErrorMessage(e, '删除失败'))
    }
  }
}

onMounted(fetchList)
</script>

<style scoped>
.prompt-library {
  max-width: 1200px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  gap: 12px;
  flex-wrap: wrap;
}

.page-header h2 {
  margin: 0 0 4px;
  font-size: 18px;
}

.hint {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: all 0.3s;
}

.card:hover {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
}

.thumb-wrap {
  position: relative;
  aspect-ratio: 16 / 10;
  background: var(--el-fill-color-light);
  overflow: hidden;
}

.thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-placeholder);
}

.shared-tag {
  position: absolute;
  top: 8px;
  right: 8px;
}

.card-body {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.card-title-row h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.desc {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.prompt-detail {
  font-size: 12px;
}

.prompt-detail summary {
  cursor: pointer;
  color: var(--el-color-primary);
  user-select: none;
}

.prompt-detail pre {
  margin: 6px 0 0;
  padding: 8px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow-y: auto;
}

.meta-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.owner {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.actions {
  display: flex;
  gap: 2px;
  flex-wrap: wrap;
}

.tag-editor {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}
</style>
