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
      </div>
      <div class="action-group">
        <span class="count-text" v-if="!loading">共 {{ items.length }} 条</span>
        <el-button :icon="Refresh" @click="loadHistory" :loading="loading">刷新</el-button>
        <el-button
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
        <div v-for="item in items" :key="item.id" class="card" :class="{ 'card-expired': item.file_expired }">
          <!-- 过期：灰色占位 + 已过期徽章 -->
          <div v-if="item.file_expired" class="thumb-wrap thumb-expired">
            <div class="expired-placeholder">
              <el-icon :size="32"><PictureFilled /></el-icon>
              <span>文件已过期</span>
            </div>
            <div class="expired-badge">已过期</div>
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
              <el-button size="small" type="danger" plain :icon="Delete" @click="handleDelete(item)">删除</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 预览弹窗 -->
    <el-dialog v-model="previewVisible" width="80%" :show-close="true" align-center>
      <img v-if="previewItem" :src="`/gen-files/${previewItem.file}`" class="preview-img" />
      <div v-if="previewItem" class="preview-info">
        <p><b>类型：</b>{{ typeLabel(previewItem.task_type) }}</p>
        <p><b>模型：</b>{{ previewItem.model_used }}</p>
        <p><b>时间：</b>{{ formatTime(previewItem.created_at) }}</p>
        <p v-if="previewItem.prompt"><b>Prompt：</b><span class="prompt-text">{{ previewItem.prompt }}</span></p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Clock, Refresh, Delete, Download, Picture, ZoomIn, PictureFilled } from '@element-plus/icons-vue'
import { listHistory, deleteHistory, clearHistory } from '../api'
import type { HistoryItem } from '../types'

const items = ref<HistoryItem[]>([])
const loading = ref(false)
const filterType = ref<string>('')
const fileExpireDays = 3
const recordExpireDays = 90
const previewVisible = ref(false)
const previewItem = ref<HistoryItem | null>(null)

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
    const res = await listHistory(filterType.value || undefined)
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

async function handleDelete(item: HistoryItem) {
  try {
    await ElMessageBox.confirm(`确定删除这张${typeLabel(item.task_type)}历史图？`, '删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteHistory(item.id)
    items.value = items.value.filter(i => i.id !== item.id)
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error('删除失败')
    console.error(e)
  }
}

async function handleClear() {
  try {
    await ElMessageBox.confirm(
      `将清空你的全部历史（共 ${items.value.length} 条），此操作不可恢复。确定继续？`,
      '清空全部历史',
      { type: 'error', confirmButtonText: '清空', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const res = await clearHistory()
    ElMessage.success(res.message)
    items.value = []
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
  margin-bottom: 6px;
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
