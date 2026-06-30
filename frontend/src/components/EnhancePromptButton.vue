<!-- 智能创意按钮：AI 策划好 prompt 给用户 -->
<template>
  <el-button
    :type="type"
    :plain="plain"
    :size="size"
    :loading="loading"
    :disabled="disabled"
    @click="onClick"
  >
    <el-icon style="margin-right: 4px"><MagicStick /></el-icon>{{ label }}
  </el-button>
</template>

<script setup lang="ts">
import { MagicStick } from '@element-plus/icons-vue'
import { useEnhancePrompt, type EnhanceParams } from '../composables/useEnhancePrompt'

interface Props {
  taskType: EnhanceParams['taskType']
  userText?: string
  aspectRatio?: string
  image?: File | null
  duration?: number
  style?: string
  videoImage?: File | null
  label?: string
  type?: 'primary' | 'success' | 'default'
  plain?: boolean
  size?: 'small' | 'default' | 'large'
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  label: '智能创意',
  type: 'primary',
  plain: true,
  size: 'default',
  disabled: false,
})

const emit = defineEmits<{
  (e: 'enhanced', text: string): void
}>()

const { loading, enhance } = useEnhancePrompt()

async function onClick() {
  const text = await enhance({
    taskType: props.taskType,
    userText: props.userText,
    aspectRatio: props.aspectRatio,
    image: props.image,
    duration: props.duration,
    style: props.style,
    videoImage: props.videoImage,
  })
  if (text) emit('enhanced', text)
}
</script>
