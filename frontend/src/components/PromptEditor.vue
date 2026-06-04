<template>
  <div class="prompt-editor">
    <el-collapse v-model="activeNames">
      <el-collapse-item title="查看 / 编辑 Prompt" name="prompt">
        <el-input
          :model-value="modelValue"
          @update:model-value="$emit('update:modelValue', $event)"
          type="textarea"
          :rows="8"
          placeholder="Prompt 将在生成时自动拼装，你也可以手动编辑"
        />
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  modelValue: string
}>()

defineEmits<{
  'update:modelValue': [value: string]
}>()

const activeNames = ref<string[]>([])
</script>

<style scoped>
.prompt-editor {
  margin-top: 12px;
}
</style>
