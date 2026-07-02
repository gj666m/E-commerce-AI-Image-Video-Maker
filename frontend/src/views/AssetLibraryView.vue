<template>
  <div class="asset-library">
    <div class="page-header">
      <div>
        <h2>素材资产库</h2>
        <p class="hint">沉淀已生成的好图好视频，打标签、加店铺应用、追踪价值</p>
      </div>
      <div class="header-actions">
        <el-select v-model="filterType" placeholder="全部类型" clearable style="width: 130px" @change="fetchList">
          <el-option label="图片" value="image" />
          <el-option label="视频" value="video" />
        </el-select>
        <el-select v-model="filterTag" placeholder="全部标签" clearable style="width: 150px" @change="fetchList">
          <el-option v-for="t in tags" :key="t.name" :label="`${t.name} (${t.count})`" :value="t.name" />
        </el-select>
        <el-input v-model="filterQ" placeholder="搜标题 / 描述" clearable style="width: 180px" @keyup.enter="fetchList" @clear="fetchList" />
        <el-button v-if="isAdmin" v-model="filterUser" :placeholder="filterUser || '所有用户'" style="display:none" />
        <el-select v-if="isAdmin" v-model="filterUser" placeholder="所有用户" clearable filterable style="width: 140px" @change="fetchList">
          <el-option v-for="u in userOptions" :key="u" :label="u" :value="u" />
        </el-select>
        <el-button @click="fetchList" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-empty v-if="!loading && items.length === 0" description="还没有沉淀的素材，去历史页点「沉淀」按钮加入吧" />

    <div v-else class="grid">
      <div v-for="item in items" :key="item.id" class="card">
        <!-- 缩略图 -->
        <div class="thumb-wrap">
          <img
            v-if="item.source_type === 'image' && item.thumbnail_url && !item.file_expired"
            :src="fileUrl(item.thumbnail_url)"
            class="thumb"
            @error="onThumbError($event, item)"
            alt=""
          />
          <video
            v-else-if="item.source_type === 'video' && item.thumbnail_url && !item.file_expired"
            :src="fileUrl(item.thumbnail_url)"
            class="thumb"
            preload="metadata"
            muted
          />
          <div v-else class="thumb thumb-placeholder">
            <el-icon :size="32"><Picture /></el-icon>
            <span class="placeholder-text">源文件不可用</span>
          </div>
          <el-tag class="type-tag" :type="item.source_type === 'image' ? '' : 'warning'" size="small">
            {{ item.source_type === 'image' ? '图片' : '视频' }}
          </el-tag>
          <el-tag v-if="item.applied_count && item.applied_count > 0" class="applied-tag" type="success" size="small">
            已应用 {{ item.applied_count }}
          </el-tag>
        </div>

        <!-- 内容 -->
        <div class="card-body">
          <h4 class="title">{{ item.title }}</h4>
          <p v-if="item.description" class="desc">{{ item.description }}</p>

          <div v-if="item.tags?.length" class="tags-row">
            <el-tag v-for="t in item.tags" :key="t" size="small" effect="plain">{{ t }}</el-tag>
          </div>

          <div class="meta-footer">
            <span class="owner">{{ item.is_owner ? '我' : item.owner_name }} · {{ formatTime(item.created_at) }}</span>
          </div>

          <div class="actions">
            <el-button size="small" text @click="openApplicationsDialog(item)">
              <el-icon><Connection /></el-icon>应用记录{{ item.applied_count ? ` (${item.applied_count})` : '' }}
            </el-button>
            <el-button size="small" text @click="openEdit(item)">
              <el-icon><Edit /></el-icon>编辑
            </el-button>
            <el-button v-if="item.is_owner || isAdmin" size="small" text type="danger" @click="handleDelete(item)">
              <el-icon><Delete /></el-icon>移出
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="showEdit" title="编辑素材" width="500px">
      <el-form label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" maxlength="100" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="2" maxlength="500" />
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
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 应用记录弹窗 -->
    <el-dialog v-model="showApplications" title="店铺应用记录" width="640px">
      <div v-if="currentAsset">
        <div class="app-header">
          <span class="app-asset-title">{{ currentAsset.title }}</span>
          <el-button size="small" type="primary" plain @click="openAddApplication">+ 新增应用</el-button>
        </div>
        <p class="app-hint">每条记录 = 该素材被一个店铺应用一次（同一素材可被多店应用）</p>

        <el-empty v-if="applications.length === 0" description="还没有应用记录，点上方「新增应用」标记该素材被哪个店铺使用了" />

        <div v-else class="app-list">
          <div v-for="app in applications" :key="app.id" class="app-item">
            <div class="app-item-main">
              <div class="app-shop">
                <el-icon><Shop /></el-icon>
                <span class="shop-name">{{ app.shop_name }}</span>
                <span class="app-time">{{ formatTime(app.applied_at) }}</span>
              </div>
              <a v-if="app.applied_url" :href="app.applied_url" target="_blank" rel="noopener" class="app-url">
                {{ app.applied_url }}
              </a>
              <p v-if="app.notes" class="app-notes">{{ app.notes }}</p>
            </div>
            <div class="app-item-actions">
              <el-button size="small" text @click="openEditApplication(app)">编辑</el-button>
              <el-button size="small" text type="danger" @click="handleDeleteApplication(app)">删除</el-button>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 新增/编辑应用记录弹窗 -->
    <el-dialog
      v-model="showAppForm"
      :title="editingApp ? '编辑应用记录' : '新增应用记录'"
      width="500px"
      @closed="resetAppForm"
    >
      <el-form label-width="80px">
        <el-form-item label="店铺名">
          <el-input v-model="appForm.shop_name" placeholder="如：TikTok US / 亚马逊 NA" maxlength="200">
            <template #append v-if="shopSuggestions.length > 0">
              <el-dropdown trigger="click" @command="pickShop">
                <el-button><el-icon><ArrowDown /></el-icon></el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-for="s in shopSuggestions" :key="s" :command="s">{{ s }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="应用链接">
          <el-input v-model="appForm.applied_url" placeholder="亚马逊 listing / TikTok 视频 URL（可选）" maxlength="1000" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="appForm.notes" type="textarea" :rows="2" placeholder="可选" maxlength="1000" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAppForm = false">取消</el-button>
        <el-button type="primary" :loading="savingApp" @click="saveApplicationForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh, Picture, Edit, Delete, Connection, Shop, ArrowDown,
} from '@element-plus/icons-vue'
import {
  listAssets, listAssetTags, updateAsset, deleteAsset,
  listApplications, createApplication, updateApplication, deleteApplication,
  listApplicationShops, getErrorMessage,
} from '../api'
import type { AssetLibraryItem, AssetTag, AssetApplication, AssetSourceType } from '../types'
import { useAuth } from '../composables/useAuth'
import { fileUrl } from '@/utils/fileUrl'

const { isAdmin } = useAuth()

const items = ref<AssetLibraryItem[]>([])
const tags = ref<AssetTag[]>([])
const loading = ref(false)
const filterType = ref<AssetSourceType | ''>('')
const filterTag = ref<string>('')
const filterQ = ref<string>('')
const filterUser = ref<string>('')

const userOptions = computed(() => {
  const set = new Set<string>()
  for (const it of items.value) {
    if (it.owner_name) set.add(it.owner_name)
  }
  return Array.from(set).sort()
})

function formatTime(s: string) {
  return (s || '').replace('T', ' ')
}

async function fetchList() {
  loading.value = true
  try {
    const data = await listAssets({
      source_type: filterType.value || undefined,
      tag: filterTag.value || undefined,
      q: filterQ.value.trim() || undefined,
    })
    items.value = data.items
    // admin 视角的用户筛选在前端做（API 不直接支持按 username）
    if (filterUser.value) {
      items.value = items.value.filter(it => (it.is_owner ? '我' : it.owner_name) === filterUser.value)
    }
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '加载失败'))
  } finally {
    loading.value = false
  }
}

async function fetchTags() {
  try {
    const r = await listAssetTags()
    tags.value = r.tags
  } catch { /* 忽略 */ }
}

function onThumbError(ev: Event, _item: AssetLibraryItem) {
  const img = ev.target as HTMLImageElement
  img.style.display = 'none'
}

// ====== 编辑素材 ======
const showEdit = ref(false)
const saving = ref(false)
const editForm = ref<{ title: string; description: string; tags: string[] }>({ title: '', description: '', tags: [] })
const editingId = ref('')

const tagInputVisible = ref(false)
const tagInputValue = ref('')
const tagInputRef = ref<{ focus: () => void } | null>(null)

function showTagInput() {
  tagInputVisible.value = true
  nextTick(() => tagInputRef.value?.focus())
}

function addTag() {
  const v = tagInputValue.value.trim()
  if (v && !editForm.value.tags.includes(v)) {
    editForm.value.tags = [...editForm.value.tags, v]
  }
  tagInputVisible.value = false
  tagInputValue.value = ''
}

function openEdit(item: AssetLibraryItem) {
  editingId.value = item.id
  editForm.value = {
    title: item.title,
    description: item.description || '',
    tags: [...(item.tags || [])],
  }
  showEdit.value = true
}

async function saveEdit() {
  if (!editForm.value.title.trim()) {
    ElMessage.warning('标题不能为空')
    return
  }
  saving.value = true
  try {
    await updateAsset(editingId.value, editForm.value)
    ElMessage.success('已保存')
    showEdit.value = false
    await Promise.all([fetchList(), fetchTags()])
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function handleDelete(item: AssetLibraryItem) {
  try {
    await ElMessageBox.confirm(
      `确定把「${item.title}」移出素材库？关联的店铺应用记录和价值数据会一并删除（源历史图/视频不受影响）`,
      '移出确认',
      { type: 'warning' }
    )
    await deleteAsset(item.id)
    ElMessage.success('已移出素材库')
    await Promise.all([fetchList(), fetchTags()])
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(getErrorMessage(e, '移出失败'))
    }
  }
}

// ====== 应用记录弹窗 ======
const showApplications = ref(false)
const currentAsset = ref<AssetLibraryItem | null>(null)
const applications = ref<AssetApplication[]>([])

async function openApplicationsDialog(item: AssetLibraryItem) {
  currentAsset.value = item
  showApplications.value = true
  try {
    const r = await listApplications(item.id)
    applications.value = r.items
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '加载应用记录失败'))
  }
}

// 新增/编辑应用记录
const showAppForm = ref(false)
const editingApp = ref<AssetApplication | null>(null)
const savingApp = ref(false)
const shopSuggestions = ref<string[]>([])
const appForm = ref<{ shop_name: string; applied_url: string; notes: string }>({
  shop_name: '', applied_url: '', notes: '',
})

async function openAddApplication() {
  editingApp.value = null
  appForm.value = { shop_name: '', applied_url: '', notes: '' }
  // 拉店铺历史用于联想
  try {
    const r = await listApplicationShops()
    shopSuggestions.value = r.shops
  } catch {
    shopSuggestions.value = []
  }
  showAppForm.value = true
}

function openEditApplication(app: AssetApplication) {
  editingApp.value = app
  appForm.value = {
    shop_name: app.shop_name,
    applied_url: app.applied_url || '',
    notes: app.notes || '',
  }
  showAppForm.value = true
}

function resetAppForm() {
  appForm.value = { shop_name: '', applied_url: '', notes: '' }
  editingApp.value = null
}

function pickShop(name: string) {
  appForm.value.shop_name = name
}

async function saveApplicationForm() {
  if (!appForm.value.shop_name.trim()) {
    ElMessage.warning('店铺名不能为空')
    return
  }
  if (!currentAsset.value) return
  savingApp.value = true
  try {
    if (editingApp.value) {
      await updateApplication(editingApp.value.id, appForm.value)
      ElMessage.success('已更新')
    } else {
      await createApplication(currentAsset.value.id, appForm.value)
      ElMessage.success('已新增应用记录')
    }
    showAppForm.value = false
    // 刷新应用记录列表 + 素材列表（applied_count 会变）
    const r = await listApplications(currentAsset.value.id)
    applications.value = r.items
    await fetchList()
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '保存失败'))
  } finally {
    savingApp.value = false
  }
}

async function handleDeleteApplication(app: AssetApplication) {
  try {
    await ElMessageBox.confirm(`确定删除店铺「${app.shop_name}」的应用记录？关联的价值数据会一并删除`, '删除确认', { type: 'warning' })
    await deleteApplication(app.id)
    ElMessage.success('已删除')
    if (currentAsset.value) {
      const r = await listApplications(currentAsset.value.id)
      applications.value = r.items
    }
    await fetchList()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(getErrorMessage(e, '删除失败'))
    }
  }
}

onMounted(async () => {
  await Promise.all([fetchList(), fetchTags()])
})
</script>

<style scoped>
.asset-library {
  max-width: 1200px;
  padding: 16px;
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
  flex-wrap: wrap;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
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
  aspect-ratio: 4 / 3;
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
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--el-text-color-placeholder);
}

.placeholder-text {
  font-size: 12px;
}

.type-tag {
  position: absolute;
  top: 8px;
  left: 8px;
}

.applied-tag {
  position: absolute;
  top: 8px;
  right: 8px;
}

.card-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
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

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.meta-footer {
  margin-top: auto;
  padding-top: 6px;
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

/* 应用记录弹窗 */
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.app-asset-title {
  font-weight: 600;
  font-size: 15px;
}

.app-hint {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.app-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.app-item {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  background: var(--el-fill-color-blank);
}

.app-item-main {
  flex: 1;
  min-width: 0;
}

.app-shop {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.shop-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.app-time {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.app-url {
  display: block;
  font-size: 12px;
  color: var(--el-color-primary);
  word-break: break-all;
  text-decoration: none;
}

.app-url:hover {
  text-decoration: underline;
}

.app-notes {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.app-item-actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
</style>
