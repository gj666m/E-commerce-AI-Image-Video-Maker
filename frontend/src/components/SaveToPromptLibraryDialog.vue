<template>
  <el-dialog v-model="visible" title="收藏到 Prompt 库" width="480px" @closed="resetForm">
    <el-form label-width="80px">
      <el-form-item label="标题">
        <el-input v-model="form.title" placeholder="一句话描述这个 Prompt 的特色" maxlength="100" />
      </el-form-item>
      <el-form-item label="原始描述">
        <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选" maxlength="500" />
      </el-form-item>
      <el-form-item label="完整 Prompt">
        <el-input v-model="form.full_prompt" type="textarea" :rows="5" />
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
      </el-form-item>
      <el-form-item label="共享">
        <el-switch v-model="form.is_shared" />
        <span class="hint">开启后全员可见可复用</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">收藏</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { createPrompt, getErrorMessage } from '../api'
import type { CreatePromptPayload, PromptTaskType } from '../types'

const props = defineProps<{
  modelValue: boolean
  /** 初始数据（从历史卡片传入） */
  initial?: {
    task_type: PromptTaskType
    title?: string
    description?: string
    full_prompt: string
    model_used?: string | null
    aspect_ratio?: string | null
    sample_image?: string | null
    sample_kind?: 'image' | 'video'
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
const form = ref<CreatePromptPayload>({
  task_type: 'quick',
  title: '',
  description: '',
  full_prompt: '',
  model_used: '',
  aspect_ratio: '',
  sample_image: '',
  sample_kind: 'image',
  tags: [],
  is_shared: false,
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

// 接收 props.initial 填表
watch(() => props.initial, (init) => {
  if (init) {
    form.value = {
      task_type: init.task_type,
      title: init.title || '',
      description: init.description || '',
      full_prompt: init.full_prompt,
      model_used: init.model_used || '',
      aspect_ratio: init.aspect_ratio || '',
      sample_image: init.sample_image || '',
      sample_kind: init.sample_kind || 'image',
      tags: [],
      is_shared: false,
    }
  }
}, { immediate: true })

function resetForm() {
  form.value = {
    task_type: 'quick',
    title: '',
    description: '',
    full_prompt: '',
    model_used: '',
    aspect_ratio: '',
    sample_image: '',
    sample_kind: 'image',
    tags: [],
    is_shared: false,
  }
}

async function handleSave() {
  if (!form.value.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  if (!form.value.full_prompt.trim()) {
    ElMessage.warning('Prompt 内容为空')
    return
  }
  saving.value = true
  try {
    await createPrompt(form.value)
    ElMessage.success('已收藏到 Prompt 库')
    visible.value = false
    emit('saved')
  } catch (e) {
    ElMessage.error(getErrorMessage(e, '收藏失败'))
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

.hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
