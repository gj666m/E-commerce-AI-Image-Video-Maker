<template>
  <div class="asset-tracking">
    <div class="page-header">
      <div>
        <h2>素材应用与价值跟踪</h2>
        <p class="hint">汇总已应用素材的播放 / 转化 / GMV，按店铺和素材维度追踪价值产出</p>
      </div>
      <div class="header-actions">
        <el-select v-model="filterShop" placeholder="全部店铺" clearable filterable style="width: 180px" @change="fetchAll">
          <el-option v-for="s in shopOptions" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="filterTag" placeholder="全部标签" clearable style="width: 150px" @change="fetchAll">
          <el-option v-for="t in tags" :key="t.name" :label="`${t.name} (${t.count})`" :value="t.name" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="—"
          start-placeholder="开始"
          end-placeholder="结束"
          value-format="YYYY-MM-DD"
          style="width: 260px"
          @change="fetchAll"
        />
        <el-select v-if="isAdmin" v-model="filterUser" placeholder="所有用户" clearable filterable style="width: 140px" @change="fetchAll">
          <el-option v-for="u in userOptions" :key="u" :label="u" :value="u" />
        </el-select>
        <el-button @click="fetchAll" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 汇总卡片 -->
    <div class="summary-cards">
      <div class="summary-card">
        <div class="summary-label">已应用素材</div>
        <div class="summary-value">{{ summary?.asset_count ?? 0 }}</div>
        <div class="summary-sub">{{ summary?.application_count ?? 0 }} 条应用记录</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">总播放</div>
        <div class="summary-value">{{ formatNum(summary?.total_views) }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">总点击</div>
        <div class="summary-value">{{ formatNum(summary?.total_clicks) }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">总转化</div>
        <div class="summary-value">{{ formatNum(summary?.total_conversions) }}</div>
      </div>
      <div class="summary-card highlight">
        <div class="summary-label">总 GMV</div>
        <div class="summary-value">{{ formatMoney(summary?.total_gmv) }}</div>
      </div>
    </div>

    <!-- 店铺维度 -->
    <el-collapse v-if="summary && summary.by_shop.length" v-model="shopCollapse" class="shop-collapse">
      <el-collapse-item name="shop" title="店铺维度汇总">
        <el-table :data="summary.by_shop" size="small" stripe>
          <el-table-column prop="shop_name" label="店铺" min-width="160" />
          <el-table-column label="应用数" width="90" align="right">
            <template #default="{ row }">{{ row.app_count }}</template>
          </el-table-column>
          <el-table-column label="播放" width="120" align="right">
            <template #default="{ row }">{{ formatNum(row.sum_views) }}</template>
          </el-table-column>
          <el-table-column label="转化" width="100" align="right">
            <template #default="{ row }">{{ formatNum(row.sum_conversions) }}</template>
          </el-table-column>
          <el-table-column label="GMV" width="140" align="right">
            <template #default="{ row }">{{ formatMoney(row.sum_gmv) }}</template>
          </el-table-column>
        </el-table>
      </el-collapse-item>
    </el-collapse>

    <!-- 应用列表 -->
    <el-empty v-if="!loading && rows.length === 0" description="还没有已应用的素材，去素材资产库点「应用记录」标记一个店铺" />

    <div v-else class="rows">
      <div v-for="row in rows" :key="row.app_id" class="row">
        <!-- 缩略图 -->
        <div class="thumb-wrap">
          <img
            v-if="row.asset.source_type === 'image' && row.asset.thumbnail_url && !row.asset.file_expired"
            :src="fileUrl(row.asset.thumbnail_url)"
            class="thumb"
            alt=""
          />
          <video
            v-else-if="row.asset.source_type === 'video' && row.asset.thumbnail_url && !row.asset.file_expired"
            :src="fileUrl(row.asset.thumbnail_url)"
            class="thumb"
            preload="metadata"
            muted
          />
          <div v-else class="thumb thumb-placeholder">
            <el-icon :size="28"><Picture /></el-icon>
            <span class="placeholder-text">源文件不可用</span>
          </div>
          <el-tag class="type-tag" :type="row.asset.source_type === 'image' ? '' : 'warning'" size="small">
            {{ row.asset.source_type === 'image' ? '图' : '视' }}
          </el-tag>
        </div>

        <!-- 主体 -->
        <div class="row-body">
          <div class="row-head">
            <span class="row-title" :title="row.asset.title">{{ row.asset.title }}</span>
            <el-tag size="small" type="info">{{ row.shop_name }}</el-tag>
            <span class="row-owner">{{ row.is_owner ? '我' : row.owner_name }} · {{ formatTime(row.applied_at) }}</span>
          </div>

          <div v-if="row.asset.tags?.length" class="tags-row">
            <el-tag v-for="t in row.asset.tags" :key="t" size="small" effect="plain">{{ t }}</el-tag>
          </div>

          <div v-if="row.applied_url" class="url-line">
            <el-link type="primary" :href="row.applied_url" target="_blank" :underline="false">
              <el-icon><Link /></el-icon>{{ row.applied_url }}
            </el-link>
          </div>

          <!-- 价值数据 -->
          <div class="metrics-row">
            <template v-if="row.latest_tracking">
              <span class="metric"><b>最新播放</b> {{ formatNum(row.latest_tracking.views) }}</span>
              <span class="metric"><b>转化</b> {{ formatNum(row.latest_tracking.conversions) }}</span>
              <span class="metric"><b>GMV</b> {{ formatMoney(row.latest_tracking.gmv) }}</span>
              <span class="metric muted">数据时间 {{ formatTime(row.latest_tracking.recorded_at) }}</span>
            </template>
            <span v-else class="metric muted">尚未录入价值数据</span>
            <span class="metric muted">累计 GMV {{ formatMoney(row.cumulative.gmv) }}</span>
          </div>
        </div>

        <!-- 操作 -->
        <div class="row-actions">
          <el-button size="small" type="primary" @click="openTrackingDialog(row)">
            <el-icon><Edit /></el-icon>{{ row.tracking_count ? '录入 / 管理' : '录入价值' }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- 录入价值弹窗 -->
    <el-dialog v-model="showTracking" title="价值数据" width="640px" :close-on-click-modal="false">
      <div v-if="currentRow" class="tracking-dialog">
        <div class="dialog-asset-info">
          <span class="row-title">{{ currentRow.asset.title }}</span>
          <el-tag size="small" type="info">{{ currentRow.shop_name }}</el-tag>
        </div>

        <!-- 新增/编辑表单 -->
        <el-form label-width="90px" size="default">
          <el-form-item label="数据时间">
            <el-date-picker
              v-model="trackingForm.recorded_at"
              type="datetime"
              value-format="YYYY-MM-DD HH:mm:ss"
              placeholder="不填默认当前"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="播放量">
            <el-input-number v-model="trackingForm.views" :min="0" controls-position="right" />
          </el-form-item>
          <el-form-item label="点击">
            <el-input-number v-model="trackingForm.clicks" :min="0" controls-position="right" />
          </el-form-item>
          <el-form-item label="转化数">
            <el-input-number v-model="trackingForm.conversions" :min="0" controls-position="right" />
          </el-form-item>
          <el-form-item label="GMV">
            <el-input-number v-model="trackingForm.gmv" :min="0" :precision="2" controls-position="right" />
          </el-form-item>

          <el-form-item label="自定义指标">
            <div class="extra-metrics">
              <div v-for="(m, idx) in trackingForm.extra_metrics" :key="idx" class="extra-row">
                <el-input v-model="m.name" placeholder="指标名（如 点赞数）" style="width: 180px" />
                <el-input v-model="m.value" placeholder="数值" style="width: 140px" />
                <el-button text type="danger" @click="trackingForm.extra_metrics.splice(idx, 1)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
              <el-button size="small" text @click="trackingForm.extra_metrics.push({ name: '', value: '' })">
                <el-icon><Plus /></el-icon>添加指标
              </el-button>
            </div>
          </el-form-item>

          <el-form-item label="备注">
            <el-input v-model="trackingForm.notes" type="textarea" :rows="2" maxlength="1000" show-word-limit />
          </el-form-item>
        </el-form>

        <!-- 历史快照 -->
        <div v-if="currentRow.history.length" class="history-list">
          <h5>历史快照（{{ currentRow.history.length }}）</h5>
          <el-table :data="currentRow.history" size="small" max-height="240" stripe>
            <el-table-column label="时间" width="160">
              <template #default="{ row }">{{ formatTime(row.recorded_at) }}</template>
            </el-table-column>
            <el-table-column label="播放" width="100" align="right">
              <template #default="{ row }">{{ formatNum(row.views) }}</template>
            </el-table-column>
            <el-table-column label="转化" width="90" align="right">
              <template #default="{ row }">{{ formatNum(row.conversions) }}</template>
            </el-table-column>
            <el-table-column label="GMV" width="120" align="right">
              <template #default="{ row }">{{ formatMoney(row.gmv) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="130" align="center">
              <template #default="{ row }">
                <el-button text size="small" @click="loadToForm(row)">编辑</el-button>
                <el-button text size="small" type="danger" @click="handleDeleteTracking(row)">删</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      <template #footer>
        <el-button @click="showTracking = false">关闭</el-button>
        <el-button type="primary" :loading="saving" @click="saveTracking">
          {{ editingTrackingId ? '更新' : '录入' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Picture, Edit, Delete, Link, Plus } from '@element-plus/icons-vue'
import {
  getAssetTrackingSummary, getAssetTrackingList,
  listTrackingShops, createTracking, updateTracking, deleteTracking,
  listAssetTags, getErrorMessage,
} from '../api'
import type { AssetTrackingSummary, AssetTrackingRow, AssetTag, TrackingRecord, TrackingExtraMetric } from '../types'
import { useAuth } from '../composables/useAuth'
import { fileUrl } from '@/utils/fileUrl'

const { isAdmin } = useAuth()

const summary = ref<AssetTrackingSummary | null>(null)
const rows = ref<AssetTrackingRow[]>([])
const tags = ref<AssetTag[]>([])
const shopOptions = ref<string[]>([])
const loading = ref(false)

const filterShop = ref<string>('')
const filterTag = ref<string>('')
const dateRange = ref<[string, string] | null>(null)
const filterUser = ref<string>('')
const shopCollapse = ref<string>('')

const userOptions = computed(() => {
  const set = new Set<string>()
  for (const r of rows.value) set.add(r.is_owner ? '我' : r.owner_name)
  return Array.from(set).sort()
})

function formatTime(s?: string | null) {
  return (s || '').replace('T', ' ').slice(0, 16)
}
function formatNum(v?: number | null) {
  if (v === null || v === undefined) return '-'
  return Number(v).toLocaleString()
}
function formatMoney(v?: number | null) {
  if (v === null || v === undefined) return '-'
  return '$' + Number(v).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function buildParams() {
  const p: Record<string, string | number> = {}
  if (filterShop.value) p.shop = filterShop.value
  if (filterTag.value) p.tag = filterTag.value
  if (dateRange.value && dateRange.value.length === 2) {
    p.from_date = dateRange.value[0]
    p.to_date = dateRange.value[1]
  }
  return p
}

async function fetchAll() {
  loading.value = true
  try {
    const params = buildParams()
    const [s, l] = await Promise.all([
      getAssetTrackingSummary(params),
      getAssetTrackingList(params),
    ])
    summary.value = s.summary
    let list = l.items
    if (filterUser.value) {
      list = list.filter(r => (r.is_owner ? '我' : r.owner_name) === filterUser.value)
    }
    rows.value = list
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '加载失败'))
  } finally {
    loading.value = false
  }
}

async function fetchShops() {
  try {
    const r = await listTrackingShops()
    shopOptions.value = r.shops || []
  } catch { /* 忽略 */ }
}

async function fetchTags() {
  try {
    const r = await listAssetTags()
    tags.value = r.tags
  } catch { /* 忽略 */ }
}

// ====== 录入价值 ======
const showTracking = ref(false)
const saving = ref(false)
const currentRow = ref<AssetTrackingRow | null>(null)
const editingTrackingId = ref<string>('')
const trackingForm = ref<{
  views: number | null
  clicks: number | null
  conversions: number | null
  gmv: number | null
  extra_metrics: TrackingExtraMetric[]
  notes: string
  recorded_at: string
}>({ views: null, clicks: null, conversions: null, gmv: null, extra_metrics: [], notes: '', recorded_at: '' })

function openTrackingDialog(row: AssetTrackingRow) {
  currentRow.value = row
  resetForm()
  showTracking.value = true
}

function resetForm() {
  editingTrackingId.value = ''
  trackingForm.value = { views: null, clicks: null, conversions: null, gmv: null, extra_metrics: [], notes: '', recorded_at: '' }
}

function loadToForm(rec: TrackingRecord) {
  editingTrackingId.value = rec.id
  trackingForm.value = {
    views: rec.views ?? null,
    clicks: rec.clicks ?? null,
    conversions: rec.conversions ?? null,
    gmv: rec.gmv ?? null,
    extra_metrics: (rec.extra_metrics || []).map(m => ({ ...m })),
    notes: rec.notes || '',
    recorded_at: rec.recorded_at || '',
  }
}

async function saveTracking() {
  if (!currentRow.value) return
  saving.value = true
  try {
    const payload = {
      views: trackingForm.value.views,
      clicks: trackingForm.value.clicks,
      conversions: trackingForm.value.conversions,
      gmv: trackingForm.value.gmv,
      extra_metrics: trackingForm.value.extra_metrics.filter(m => m.name.trim()),
      notes: trackingForm.value.notes.trim() || undefined,
      recorded_at: trackingForm.value.recorded_at || undefined,
    }
    if (editingTrackingId.value) {
      await updateTracking(editingTrackingId.value, payload)
      ElMessage.success('已更新')
    } else {
      await createTracking(currentRow.value.app_id, payload)
      ElMessage.success('已录入')
    }
    resetForm()
    await fetchAll()
    // 重新定位 currentRow（fetchAll 后 rows 已更新）
    if (currentRow.value) {
      const updated = rows.value.find(r => r.app_id === currentRow.value!.app_id)
      if (updated) currentRow.value = updated
    }
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function handleDeleteTracking(rec: TrackingRecord) {
  try {
    await ElMessageBox.confirm(`确认删除 ${formatTime(rec.recorded_at)} 这条记录？`, '删除', { type: 'warning' })
  } catch { return }
  try {
    await deleteTracking(rec.id)
    ElMessage.success('已删除')
    await fetchAll()
    if (currentRow.value) {
      const updated = rows.value.find(r => r.app_id === currentRow.value!.app_id)
      if (updated) currentRow.value = updated
    }
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '删除失败'))
  }
}

onMounted(() => {
  fetchAll()
  fetchShops()
  fetchTags()
})
</script>

<style scoped>
.asset-tracking { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
.page-header h2 { margin: 0 0 4px; font-size: 20px; }
.hint { margin: 0; color: #909399; font-size: 13px; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }

.summary-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 20px; }
.summary-card { background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.summary-card.highlight { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; }
.summary-label { font-size: 13px; color: #909399; margin-bottom: 6px; }
.summary-card.highlight .summary-label { color: rgba(255,255,255,0.85); }
.summary-value { font-size: 26px; font-weight: 600; }
.summary-sub { font-size: 12px; color: #c0c4cc; margin-top: 4px; }

.shop-collapse { margin-bottom: 20px; }

.rows { display: flex; flex-direction: column; gap: 12px; }
.row { display: flex; gap: 14px; background: #fff; border-radius: 8px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.thumb-wrap { position: relative; flex-shrink: 0; }
.thumb { width: 96px; height: 96px; object-fit: cover; border-radius: 6px; background: #f5f7fa; display: block; }
.thumb-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; color: #c0c4cc; gap: 4px; }
.placeholder-text { font-size: 11px; }
.type-tag { position: absolute; top: 4px; left: 4px; }

.row-body { flex: 1; min-width: 0; }
.row-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.row-title { font-weight: 600; font-size: 15px; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row-owner { font-size: 12px; color: #909399; margin-left: auto; }
.tags-row { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 6px; }
.url-line { font-size: 12px; margin-bottom: 6px; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.metrics-row { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; align-items: center; }
.metric b { color: #909399; font-weight: 500; margin-right: 4px; font-size: 12px; }
.metric.muted { color: #c0c4cc; }
.row-actions { flex-shrink: 0; display: flex; align-items: center; }

.tracking-dialog { }
.dialog-asset-info { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #ebeef5; }
.extra-metrics { display: flex; flex-direction: column; gap: 6px; }
.extra-row { display: flex; gap: 6px; align-items: center; }
.history-list { margin-top: 16px; border-top: 1px dashed #ebeef5; padding-top: 12px; }
.history-list h5 { margin: 0 0 8px; font-size: 13px; color: #606266; }

@media (max-width: 1100px) {
  .summary-cards { grid-template-columns: repeat(2, 1fr); }
}
</style>
