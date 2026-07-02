<template>
  <div class="video-history-view">
    <div class="page-header">
      <h2 class="section-title">
        <el-icon class="section-icon"><VideoCamera /></el-icon>
        视频历史
      </h2>
      <p class="section-desc">自动记录所有生成完成的视频。文件保留 {{ fileExpireDays }} 天，元数据保留 {{ recordExpireDays }} 天。</p>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="filter-group">
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
        <el-icon :size="48" color="#c0c4cc"><VideoCamera /></el-icon>
        <p>暂无视频历史</p>
      </div>

      <div v-else class="grid">
        <div v-for="item in displayedItems" :key="item.id" class="card" :class="{ 'card-expired': item.file_expired }">
          <!-- 文件不可用：文件过期 / 用户软删 -->
          <div
            v-if="item.file_expired || (isAdmin && item.user_deleted)"
            class="thumb-wrap thumb-expired thumb-clickable"
            @click="preview(item)"
          >
            <div class="expired-placeholder">
              <el-icon :size="32">
                <Delete v-if="isAdmin && item.user_deleted" />
                <VideoPause v-else />
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
          <!-- 正常：视频首帧 + 点击播放 -->
          <div v-else class="thumb-wrap" @click="preview(item)">
            <video
              :src="fileUrl(item.video_url || '')"
              preload="metadata"
              muted
              class="thumb-video"
            ></video>
            <div class="thumb-overlay">
              <el-icon :size="32"><VideoPlay /></el-icon>
              <span>播放</span>
            </div>
            <div class="duration-badge" v-if="item.resolution">{{ item.resolution }}</div>
          </div>
          <div class="card-meta">
            <div class="meta-row">
              <el-tag size="small" type="warning">{{ providerLabel(item.provider_name) }}</el-tag>
              <el-tag v-if="isAdmin && item.username" size="small" type="primary" class="user-tag">
                {{ item.username }}
              </el-tag>
              <span class="meta-time">{{ formatTime(item.created_at) }}</span>
            </div>
            <div class="meta-prompt">{{ item.prompt || '—' }}</div>
            <div class="meta-cost" v-if="item.cost && item.cost > 0">
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
              <el-button size="small" plain :icon="Files" @click="openSaveToAsset(item)">沉淀</el-button>
              <el-button v-if="isAdmin" size="small" type="danger" plain :icon="Delete" @click="handleDelete(item)">删除</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 预览弹窗 -->
    <el-dialog v-model="previewVisible" width="80%" :show-close="true" align-center>
      <div v-if="previewItem" class="preview-video-wrap">
        <video
          v-if="!videoLoadFailed && previewItem.video_url"
          :src="fileUrl(previewItem.video_url)"
          controls
          autoplay
          class="preview-video"
          @error="videoLoadFailed = true"
        ></video>
        <div v-else class="preview-video-fallback">
          <el-icon :size="40"><VideoPause /></el-icon>
          <span>文件不可用（已过期或已删除）</span>
        </div>
      </div>
      <div v-if="previewItem" class="preview-info">
        <p><b>模型：</b>{{ providerLabel(previewItem.provider_name) }}</p>
        <p><b>分辨率：</b>{{ previewItem.resolution || '—' }}</p>
        <p><b>时间：</b>{{ formatTime(previewItem.created_at) }}</p>
        <p v-if="previewItem.cost && previewItem.cost > 0"><b>花费：</b>{{ previewItem.cost.toFixed(2) }} {{ previewItem.currency }}</p>
        <p v-if="previewItem.prompt"><b>Prompt：</b><span class="prompt-text">{{ previewItem.prompt }}</span></p>
      </div>
    </el-dialog>

    <!-- 收藏到 Prompt 库 -->
    <SaveToPromptLibraryDialog v-model="showSaveDialog" :initial="saveInitial || undefined" />

    <!-- 沉淀到素材库 -->
    <SaveToAssetLibraryDialog v-model="showAssetDialog" :initial="assetInitial || undefined" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { VideoCamera, Refresh, Delete, Download, VideoPlay, VideoPause, StarFilled, Files } from '@element-plus/icons-vue'
import { listVideoHistory, deleteVideoHistory, clearVideoHistory } from '../api'
import { useAuth } from '../composables/useAuth'
import { fileUrl } from '@/utils/fileUrl'
import type { VideoHistoryItem, AssetSourceType } from '../types'
import SaveToPromptLibraryDialog from '../components/SaveToPromptLibraryDialog.vue'
import SaveToAssetLibraryDialog from '../components/SaveToAssetLibraryDialog.vue'

const { isAdmin } = useAuth()

const items = ref<VideoHistoryItem[]>([])
const loading = ref(false)
const filterUser = ref<string>('')
const showDeleted = ref(false)

// 收藏到 Prompt 库
const showSaveDialog = ref(false)
const saveInitial = ref<{
  task_type: 'video' | 'video_shots'
  title?: string
  description?: string
  full_prompt: string
  model_used?: string | null
  aspect_ratio?: string | null
  sample_image?: string | null
  sample_kind?: 'image' | 'video'
} | null>(null)

// 沉淀到素材库
const showAssetDialog = ref(false)
const assetInitial = ref<{
  source_type: AssetSourceType
  source_id: string
  title?: string
  description?: string
  tags?: string[]
} | null>(null)

const fileExpireDays = 3
const recordExpireDays = 90
const previewVisible = ref(false)
const previewItem = ref<VideoHistoryItem | null>(null)
const videoLoadFailed = ref(false)

const providerLabelMap: Record<string, string> = {
  seedance_apiyi: 'Seedance 2.0',
  seedance: 'Seedance 2.0',
  seedance_mini: 'Seedance 2.0 Mini',
  mock_video: 'Mock',
}

function providerLabel(name: string) {
  return providerLabelMap[name] || name
}

const userOptions = computed(() => {
  const set = new Set<string>()
  for (const it of items.value) {
    if (it.username) set.add(it.username)
  }
  return Array.from(set).sort()
})

const displayedItems = computed(() => {
  if (!filterUser.value) return items.value
  return items.value.filter(it => it.username === filterUser.value)
})

function formatTime(t: string | null) {
  if (!t) return ''
  return t.replace('T', ' ')
}

async function loadHistory() {
  loading.value = true
  try {
    const res = await listVideoHistory({
      includeDeleted: isAdmin.value && showDeleted.value,
    })
    items.value = res.items
  } catch (e) {
    ElMessage.error('加载视频历史失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

function preview(item: VideoHistoryItem) {
  previewItem.value = item
  videoLoadFailed.value = false
  previewVisible.value = true
}

async function download(item: VideoHistoryItem) {
  if (!item.video_url) {
    ElMessage.warning('视频文件不可用')
    return
  }
  try {
    const resp = await fetch(fileUrl(item.video_url))
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${item.id}.mp4`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败')
    console.error(e)
  }
}

function openSaveToLibrary(item: VideoHistoryItem) {
  // 视频历史的 task_type 暂统一为 'video'
  saveInitial.value = {
    task_type: 'video',
    title: item.prompt?.slice(0, 40) || '未命名视频 Prompt',
    description: '',
    full_prompt: item.prompt || '',
    model_used: item.provider_name || '',
    aspect_ratio: item.resolution || '',
    sample_image: item.video_url || '',
    sample_kind: 'video',
  }
  showSaveDialog.value = true
}

function openSaveToAsset(item: VideoHistoryItem) {
  assetInitial.value = {
    source_type: 'video',
    source_id: item.id,
    title: item.prompt?.slice(0, 40) || '未命名视频素材',
    description: '',
    tags: [],
  }
  showAssetDialog.value = true
}

async function handleDelete(item: VideoHistoryItem) {
  // 仅 admin 可调（按钮已隐藏，此处兜底）
  if (!isAdmin.value) return
  const tip = `管理员将【永久硬删】这条视频记录，不可恢复。确定？`
  try {
    await ElMessageBox.confirm(tip, '删除确认', { type: 'error' })
  } catch {
    return
  }
  try {
    await deleteVideoHistory(item.id)
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
      `将【永久硬删】${target}全部视频历史（当前显示 ${displayedItems.value.length} 条）。\n此操作不可恢复，确定？`,
      `清空${scope}视频历史`,
      { type: 'error', confirmButtonText: '永久清空', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const res = await clearVideoHistory(filterUser.value || undefined)
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
.video-history-view {
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

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
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
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
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
  aspect-ratio: 16 / 9;
  background: #000;
  cursor: pointer;
  overflow: hidden;
}

.thumb-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.duration-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  padding: 2px 8px;
  background: rgba(0, 0, 0, 0.65);
  color: #fff;
  font-size: 12px;
  border-radius: 4px;
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

.meta-prompt {
  font-size: 12px;
  color: var(--el-text-color-regular);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
  min-height: 32px;
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

.preview-video {
  width: 100%;
  display: block;
  border-radius: 4px;
  background: #000;
}

.preview-video-wrap {
  width: 100%;
}

.preview-video-fallback {
  width: 100%;
  aspect-ratio: 16 / 9;
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
