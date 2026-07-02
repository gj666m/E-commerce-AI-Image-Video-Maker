<template>
  <div class="model-library">
    <div class="library-header">
      <span class="title">模特库</span>
      <el-button type="primary" text size="small" @click="$router.push('/model-gen')">
        + 生成新模特
      </el-button>
    </div>

    <div v-if="loading" class="loading-area">
      <el-skeleton :rows="2" animated />
    </div>

    <div v-else-if="models.length === 0" class="empty-area">
      <el-empty description="模特库为空" :image-size="60" />
      <el-button type="primary" size="small" @click="$router.push('/model-gen')">
        去生成模特
      </el-button>
    </div>

    <div v-else class="model-grid">
      <div
        v-for="model in models"
        :key="model.id"
        class="model-card"
        :class="{ selected: selectedId === model.id }"
        @click="handleSelect(model)"
      >
        <el-image
          :src="fileUrl(`/model-files/${model.thumbnail}`)"
          fit="cover"
          class="model-thumb"
        />
        <div class="model-name">{{ model.name }}</div>
        <el-button
          type="danger"
          text
          size="small"
          class="delete-btn"
          @click.stop="handleDelete(model.id)"
        >
          删除
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getModelList, deleteModel } from '../api'
import { fileUrl } from '../utils/fileUrl'
import type { ModelItem } from '../types'

const props = defineProps<{
  selectedId?: string | null
}>()

const emit = defineEmits<{
  select: [model: ModelItem]
}>()

const loading = ref(true)
const models = ref<ModelItem[]>([])

onMounted(async () => {
  await loadModels()
})

async function loadModels() {
  loading.value = true
  try {
    const data = await getModelList()
    models.value = data.models
  } catch {
    ElMessage.error('加载模特库失败')
  } finally {
    loading.value = false
  }
}

function handleSelect(model: ModelItem) {
  emit('select', model)
}

async function handleDelete(modelId: string) {
  try {
    await ElMessageBox.confirm('确定删除这个模特？', '提示', { type: 'warning' })
    await deleteModel(modelId)
    models.value = models.value.filter(m => m.id !== modelId)
    ElMessage.success('已删除')
  } catch {
    // 用户取消
  }
}
</script>

<style scoped>
.model-library {
  width: 100%;
}

.library-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
  padding: 4px;
}

.model-card {
  border: 2px solid #ebeef5;
  border-radius: 8px;
  cursor: pointer;
  text-align: center;
  padding: 4px;
  position: relative;
  transition: border-color 0.2s;
}

.model-card:hover {
  border-color: #409eff;
}

.model-card.selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.model-thumb {
  width: 80px;
  height: 100px;
  border-radius: 4px;
}

.model-name {
  font-size: 11px;
  color: #606266;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.delete-btn {
  position: absolute;
  top: 2px;
  right: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}

.model-card:hover .delete-btn {
  opacity: 1;
}

.empty-area {
  text-align: center;
  padding: 20px 0;
}
</style>
