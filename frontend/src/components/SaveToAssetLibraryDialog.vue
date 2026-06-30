<template>
  <el-dialog v-model="visible" title="沉淀到素材库" width="480px" @closed="resetForm">
    <el-alert
      v-if="alreadyPreserved"
      type="warning"
      :closable="false"
      title="该素材已在素材库中"
      description="可以重复点击保存会更新标题/描述/标签"
      style="margin-bottom: 12px"
    />
    <el-form label-width="80px">
      <el-form-item label="标题">
        <el-input v-model="form.title" placeholder="一句话描述这个素材的特色" maxlength="100" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选" maxlength="500" />
      </el-form-item>
      <el-form-item label="标签">
        <div class="tag-editor">
          <el-tag
            v-for="(t, idx) in form.tags"
            :key="idx"
            closable
            size="small"
            @close="form.tags!.splice(idx, 1)"
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
        <div class="tag-hint">自定义标签便于后续筛选（如：白裙、海边、夏季）</div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">沉淀</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { createAsset, updateAsset, checkAssetPreserved, getErrorMessage } from '../api'
import type { CreateAssetPayload, AssetSourceType } from '../types'

const props = defineProps<{
  modelValue: boolean
  /** 初始数据（从历史卡片传入） */
  initial?: {
    source_type: AssetSourceType
    source_id: string
    title?: string
    description?: string
    tags?: string[]
    /** 已沉淀时传入 asset_id 走更新；不传走创建 */
    existing_asset_id?: string
  }
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'saved'): void
}>()

const visible = ref(props.modelValue)
watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => emit('update:modelValue', v))

const saving = ref(false)
const alreadyPreserved = ref(false)
const existingAssetId = ref<string | undefined>(undefined)

const form = ref<CreateAssetPayload>({
  source_type: 'image',
  source_id: '',
  title: '',
  description: '',
  tags: [],
})

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
  if (v && !form.value.tags?.includes(v)) {
    form.value.tags = [...(form.value.tags || []), v]
  }
  tagInputVisible.value = false
  tagInputValue.value = ''
}

// 接收 props.initial 填表 + 检查是否已沉淀
watch(() => props.initial, async (init) => {
  if (init) {
    form.value = {
      source_type: init.source_type,
      source_id: init.source_id,
      title: init.title || '',
      description: init.description || '',
      tags: init.tags ? [...init.tags] : [],
    }
    existingAssetId.value = init.existing_asset_id
    // 已沉淀态：existing_asset_id 优先（避免每次都打 is-preserved 接口）
    if (init.existing_asset_id) {
      alreadyPreserved.value = true
    } else {
      try {
        const r = await checkAssetPreserved(init.source_type, init.source_id)
        alreadyPreserved.value = r.preserved
      } catch {
        alreadyPreserved.value = false
      }
    }
  }
}, { immediate: true })

function resetForm() {
  form.value = {
    source_type: 'image',
    source_id: '',
    title: '',
    description: '',
    tags: [],
  }
  alreadyPreserved.value = false
  existingAssetId.value = undefined
}

async function handleSave() {
  if (!form.value.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  if (!form.value.source_id) {
    ElMessage.error('源素材 id 缺失')
    return
  }
  saving.value = true
  try {
    if (existingAssetId.value) {
      // 更新已沉淀的素材
      await updateAsset(existingAssetId.value, {
        title: form.value.title,
        description: form.value.description,
        tags: form.value.tags,
      })
      ElMessage.success('已更新素材信息')
    } else {
      await createAsset(form.value)
      ElMessage.success('已沉淀到素材库')
    }
    visible.value = false
    emit('saved')
  } catch (e: any) {
    // 409 = 已沉淀过 → 提示并切更新态
    if (e?.response?.status === 409) {
      alreadyPreserved.value = true
      ElMessage.warning('该素材已在素材库中，请改用素材库页编辑')
    } else {
      ElMessage.error(getErrorMessage(e, '沉淀失败'))
    }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.tag-editor {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}
.tag-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
</style>
