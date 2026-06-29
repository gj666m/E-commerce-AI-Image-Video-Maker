<template>
  <div class="history-view">
    <div class="page-header">
      <h2 class="section-title">
        <el-icon class="section-icon"><Clock /></el-icon>
        生成历史
      </h2>
      <p class="section-desc">自动记录所有图片生成结果。文件保留 {{ fileExpireDays }} 天，元数据保留 {{ recordExpireDays }} 天。</p>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="filter-group">
        <el-select
          v-model="filterType"
          placeholder="全部类型"
          clearable
          style="width: 160px"
          @change="loadHistory"
        >
          <el-option
            v-for="opt in typeOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-select
          v-if="isAdmin"
          v-model="filterUser"
          placeholder="全部用户"
          clearable
          filterable
          style="width: 160px"
        >
          <el-option
            v-for="u in userOptions"
            :key="u"
            :label="u"
            :value="u"
          />
        </el-select>
        <el-tooltip
          v-if="isAdmin"
          content="开启后显示用户已软删的记录（仅管理员可见）"
          placement="top"
        >
          <el-switch
            v-model="showDeleted"
            inline-prompt
            active-text="含已删"
            inactive-text="全部"
            @change="loadHistory"
          />
        </el-tooltip>
      </div>
      <div class="action-group">
        <span class="count-text" v-if="!loading">共 {{ displayedItems.length }} 条</span>
        <el-button :icon="Refresh" @click="loadHistory" :loading="loading">刷新</el-button>
        <el-button
          v-if="isAdmin"
          type="danger"
          plain
          :icon="Delete"
          :disabled="items.length === 0"
          @click="handleClear"
        >清空全部</el-button>
      </div>
    </div>

    <!-- 网格 -->
    <div v-loading="loading">
      <div v-if="items.length === 0 && !loading" class="empty-state">
        <el-icon :size="48" color="#c0c4cc"><Picture /></el-icon>
        <p>暂无生成历史</p>
      </div>

      <div v-else class="grid">
        <div v-for="item in displayedItems" :key="item.id" class="card" :class="{ 'card-expired': item.file_expired }">
          <!-- 文件不可用：3 种情况共用占位（文件过期 / 用户软删 / admin 视角的用户软删）-->
          <div
            v-if="item.file_expired || (isAdmin && item.user_deleted)"
            class="thumb-wrap thumb-expired thumb-clickable"
            @click="preview(item)"
          >
            <div class="expired-placeholder">
              <el-icon :size="32">
                <Delete v-if="isAdmin && item.user_deleted" />
                <PictureFilled v-else />
              </el-icon>
              <span v-if="isAdmin && item.user_deleted">用户已删除</span>
              <span v-else>文件已过期</span>
              <span class="deleted-time" v-if="isAdmin && item.user_deleted && item.user_deleted_at">
                {{ formatTime(item.user_deleted_at) }}
              </span>
              <span class="click-hint">点击查看详情</span>
            </div>
            <div v-if="isAdmin && item.user_deleted" class="user-deleted-badge">用户已删</div>
            <div v-else class="expired-badge">已过期</div>
          </div>
          <!-- 正常：缩略图 + 预览 -->
          <div v-else class="thumb-wrap" @click="preview(item)">
            <img :src="`/gen-files/${item.thumbnail}`" :alt="item.task_type" loading="lazy" />
            <div class="thumb-overlay">
              <el-icon><ZoomIn /></el-icon>
              <span>查看</span>
            </div>
          </div>
          <div class="card-meta">
            <div class="meta-row">
              <el-tag size="small" :type="tagType(item.task_type)">
                {{ typeLabel(item.task_type) }}
              </el-tag>
              <el-tag v-if="isAdmin && item.username" size="small" type="primary" class="user-tag">
                {{ item.username }}
              </el-tag>
              <span class="meta-time">{{ formatTime(item.created_at) }}</span>
            </div>
            <div class="meta-model">{{ item.model_used || '—' }}</div>
            <div class="meta-cost" v-if="item.cost > 0">
              {{ item.cost.toFixed(2) }} {{ item.currency }}
            </div>
            <div class="card-actions">
              <el-button
                size="small"
                :icon="Download"
                :disabled="item.file_expired"
                @click="download(item)"
              >下载</el-button>
              <el-button size="small" :icon="StarFilled" @click="openSaveToLibrary(item)">收藏</el-button>
              <el-button v-if="isAdmin" size="small" type="danger" plain :icon="Delete" @click="handleDelete(item)">删除</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 预览弹窗 -->
    <el-dialog v-model="previewVisible" width="80%" :show-close="true" align-center>
      <div v-if="previewItem" class="preview-img-wrap">
        <img
          v-if="!imgLoadFailed"
          :src="`/gen-files/${previewItem.file}`"
          class="preview-img"
          @error="imgLoadFailed = true"
        />
        <div v-else class="preview-img-fallback">
          <el-icon :size="40"><PictureFilled /></el-icon>
          <span>文件不可用（已过期或已删除）</span>
        </div>
      </div>
      <div v-if="previewItem" class="preview-info">
        <p><b>类型：</b>{{ typeLabel(previewItem.task_type) }}</p>
        <p><b>模型：</b>{{ previewItem.model_used }}</p>
        <p><b>时间：</b>{{ formatTime(previewItem.created_at) }}</p>
        <p v-if="previewItem.prompt"><b>Prompt：</b><span class="prompt-text">{{ previewItem.prompt }}</span></p>
      </div>
    </el-dialog>

    <!-- 收藏到 Prompt 库 -->
    <SaveToPromptLibraryDialog v-model="showSaveDialog" :initial="saveInitial || undefined" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Clock, Refresh, Delete, Download, Picture, ZoomIn, PictureFilled, StarFilled } from '@element-plus/icons-vue'
import { listHistory, deleteHistory, clearHistory } from '../api'
import { useAuth } from '../composables/useAuth'
import type { HistoryItem, PromptTaskType } from '../types'
import SaveToPromptLibraryDialog from '../components/SaveToPromptLibraryDialog.vue'

const { isAdmin } = useAuth()

const items = ref<HistoryItem[]>([])
const loading = ref(false)
const filterType = ref<string>('')
const filterUser = ref<string>('')
const showDeleted = ref(false)  // admin 专属：是否显示用户软删的记录
const fileExpireDays = 3
const recordExpireDays = 90
const previewVisible = ref(false)
const previewItem = ref<HistoryItem | null>(null)
const imgLoadFailed = ref(false)

// 收藏到 Prompt 库
const showSaveDialog = ref(false)
const saveInitial = ref<{
  task_type: PromptTaskType
  title?: string
  description?: string
  full_prompt: string
  model_used?: string | null
  aspect_ratio?: string | null
  sample_image?: string | null
  sample_kind?: 'image' | 'video'
} | null>(null)

// admin 视角：从所有记录中提取去重的用户名列表
const userOptions = computed(() => {
  const set = new Set<string>()
  for (const it of items.value) {
    if (it.username) set.add(it.username)
  }
  return Array.from(set).sort()
})

// 前端按用户筛选（admin 专属）
const displayedItems = computed(() => {
  if (!filterUser.value) return items.value
  return items.value.filter(it => it.username === filterUser.value)
})

const typeOptions = [
  { label: '快速生图', value: 'quick' },
  { label: '一键穿搭', value: 'outfit' },
  { label: '模特生成', value: 'model_gen' },
  { label: '模特参考', value: 'model_ref' },
  { label: '种草图', value: 'seed_grass' },
  { label: '商品主图', value: 'product_main' },
  { label: 'A+ 图', value: 'aplus' },
  { label: '商品视频图', value: 'product_video' },
]

const typeLabelMap: Record<string, string> = Object.fromEntries(typeOptions.map(o => [o.value, o.label]))

function typeLabel(t: string) {
  return typeLabelMap[t] || t
}

function tagType(t: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    quick: '',
    outfit: 'success',
    model_gen: 'warning',
    model_ref: 'warning',
    seed_grass: 'danger',
    product_main: 'info',
    aplus: 'info',
    product_video: 'info',
  }
  return map[t] || 'info'
}

function formatTime(t: string) {
  if (!t) return ''
  // 兼容 "2026-06-16T12:00:00" 和 "2026-06-16 12:00:00"
  return t.replace('T', ' ')
}

async function loadHistory() {
  loading.value = true
  try {
    const res = await listHistory(filterType.value || undefined, {
      includeDeleted: isAdmin.value && showDeleted.value,
    })
    items.value = res.items
  } catch (e) {
    ElMessage.error('加载历史失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

function preview(item: HistoryItem) {
  previewItem.value = item
  imgLoadFailed.value = false
  previewVisible.value = true
}

async function download(item: HistoryItem) {
  try {
    const resp = await fetch(`/gen-files/${item.file}`)
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${item.task_type}_${item.id}.jpeg`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败')
    console.error(e)
  }
}

// 把生成历史记录映射成 Prompt 库可接受的 task_type
function toPromptTaskType(t: string): PromptTaskType {
  if (['quick', 'outfit', 'model_gen', 'seed_grass', 'product_main', 'aplus'].includes(t)) {
    return t as PromptTaskType
  }
  return 'quick'
}

function openSaveToLibrary(item: HistoryItem) {
  const params = item.params || {}
  saveInitial.value = {
    task_type: toPromptTaskType(item.task_type),
    title: item.prompt?.slice(0, 40) || '未命名 Prompt',
    description: typeof params.description === 'string' ? params.description : '',
    full_prompt: item.prompt || '',
    model_used: item.model_used || '',
    aspect_ratio: typeof params.aspect_ratio === 'string' ? params.aspect_ratio : '',
    sample_image: item.thumbnail ? `/gen-files/${item.thumbnail}` : '',
    sample_kind: 'image',
  }
  showSaveDialog.value = true
}

async function handleDelete(item: HistoryItem) {
  // 仅 admin 可调（按钮已隐藏，此处兜底）
  if (!isAdmin.value) return
  const tip = `管理员将【永久硬删】这张${typeLabel(item.task_type)}记录，不可恢复。确定？`
  try {
    await ElMessageBox.confirm(tip, '删除确认', { type: 'error' })
  } catch {
    return
  }
  try {
    await deleteHistory(item.id)
    items.value = items.value.filter(i => i.id !== item.id)
    ElMessage.success('已硬删')
  } catch (e) {
    ElMessage.error('删除失败')
    console.error(e)
  }
}

async function handleClear() {
  // 仅 admin 可调（按钮已隐藏，此处兜底）
  if (!isAdmin.value) return
  const target = filterUser.value
    ? `用户【${filterUser.value}】的`
    : '所有用户的'
  const scope = filterUser.value ? '当前筛选用户' : '所有用户'
  try {
    await ElMessageBox.confirm(
      `将【永久硬删】${target}全部历史（当前显示 ${displayedItems.value.length} 条）。\n此操作不可恢复，确定？`,
      `清空${scope}历史`,
      { type: 'error', confirmButtonText: '永久清空', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const res = await clearHistory(filterUser.value || undefined)
    ElMessage.success(res.message)
    await loadHistory()
  } catch (e) {
    ElMessage.error('清空失败')
    console.error(e)
  }
}

onMounted(loadHistory)
</script>

<style scoped>
.history-view {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 6px;
}

.section-icon {
  color: var(--el-color-primary);
}

.section-desc {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.action-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.count-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--el-text-color-secondary);
}

.empty-state p {
  margin-top: 12px;
  font-size: 14px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  overflow: hidden;
  transition: box-shadow 0.2s, transform 0.2s;
}

.card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-expired {
  opacity: 0.78;
}

.card-expired:hover {
  transform: none;
}

.thumb-expired {
  cursor: default;
}

.thumb-clickable {
  cursor: pointer;
}

.thumb-clickable:hover .expired-placeholder {
  opacity: 0.85;
}

.click-hint {
  font-size: 11px;
  opacity: 0.6;
  margin-top: 6px;
}

.expired-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--el-text-color-placeholder);
  background: var(--el-fill-color-light);
  font-size: 13px;
}

.expired-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 8px;
  background: var(--el-color-info-light-5);
  color: #fff;
  font-size: 12px;
  border-radius: 4px;
}

.user-deleted-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 8px;
  background: var(--el-color-danger-light-5);
  color: #fff;
  font-size: 12px;
  border-radius: 4px;
}

.deleted-time {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 4px;
}

.thumb-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  background: var(--el-fill-color-light);
  cursor: pointer;
  overflow: hidden;
}

.thumb-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #fff;
  font-size: 13px;
  opacity: 0;
  transition: opacity 0.2s;
}

.thumb-wrap:hover .thumb-overlay {
  opacity: 1;
}

.thumb-overlay .el-icon {
  font-size: 28px;
}

.card-meta {
  padding: 10px 12px 12px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.user-tag {
  margin-right: auto;
}

.meta-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.meta-model {
  font-size: 12px;
  color: var(--el-text-color-regular);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.meta-cost {
  font-size: 12px;
  color: var(--el-color-warning);
  margin-bottom: 8px;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.card-actions .el-button {
  flex: 1;
}

.preview-img {
  width: 100%;
  display: block;
  border-radius: 4px;
}

.preview-img-wrap {
  width: 100%;
}

.preview-img-fallback {
  width: 100%;
  aspect-ratio: 1;
  background: var(--el-fill-color-light);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--el-text-color-placeholder);
  font-size: 14px;
  border-radius: 4px;
}

.preview-info {
  margin-top: 16px;
  font-size: 13px;
  line-height: 1.8;
}

.preview-info p {
  margin: 0;
  word-break: break-word;
}

.prompt-text {
  color: var(--el-text-color-secondary);
}
</style>
