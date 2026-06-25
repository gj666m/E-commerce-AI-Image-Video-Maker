<template>
  <div class="mention-textarea-wrap">
    <!-- 引用预览栏：当前 prompt 里 @ 引用的图片缩略图（不进入 textarea，避免光标错位） -->
    <div v-if="referencedItems.length > 0" class="ref-preview-bar">
      <span class="bar-label">引用：</span>
      <div
        v-for="item in referencedItems"
        :key="item.idx"
        class="preview-chip"
        :title="item.filename"
      >
        <img :src="item.preview_url" class="preview-thumb" />
        <span class="preview-num">图片{{ item.idx + 1 }}</span>
      </div>
    </div>

    <!-- textarea 容器：mirror 和 el-input 必须在同一父元素内，否则 absolute 定位错乱 -->
    <div class="textarea-inner-wrap">
      <!-- 背景渲染层：高亮 chip（纯颜色，不加 padding/缩略图，保持光标对齐） -->
      <div ref="mirrorRef" class="mirror-layer" v-html="renderedHtml"></div>

      <!-- 顶层 textarea：文字透明 caret 可见，所有交互保留 -->
      <el-input
        ref="inputRef"
        :model-value="modelValue"
        type="textarea"
        :rows="rows"
        :placeholder="computedPlaceholder"
        :disabled="disabled"
        @update:model-value="onUpdate"
        @scroll="onScroll"
      />
    </div>

    <!-- @ 浮层 -->
    <ReferenceMentionPopover
      :visible="mention.visible.value"
      :items="mention.items.value"
      :active-idx="mention.activeIdx.value"
      :anchor-ref="inputRef"
      @select="mention.selectMention"
      @hover="mention.hoverItem"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import ReferenceMentionPopover from './ReferenceMentionPopover.vue'
import { useReferenceMention, type RefItem } from '../composables/useReferenceMention'

const props = withDefaults(
  defineProps<{
    modelValue: string
    /** 参考图源（响应式数组，会随上传变化） */
    refsSource: RefItem[]
    rows?: number
    placeholder?: string
    disabled?: boolean
  }>(),
  {
    rows: 3,
    placeholder: '',
    disabled: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const inputRef = ref<any>(null)
const mirrorRef = ref<HTMLDivElement | null>(null)

// 参考图源 → ComputedRef（useReferenceMention 需要 ComputedRef 类型）
const refsComputed = computed(() => props.refsSource)
// modelValue 可写代理
const modelProxy = computed({
  get: () => props.modelValue,
  set: (v: string) => emit('update:modelValue', v),
})

const mention = useReferenceMention(inputRef, refsComputed, modelProxy)

const computedPlaceholder = computed(() =>
  props.placeholder
    ? `${props.placeholder}（输入 @ 可引用参考图）`
    : '输入 @ 可引用已上传参考图',
)

function onUpdate(v: string) {
  emit('update:modelValue', v)
}

/** textarea 滚动时同步背景 mirror 层 */
function onScroll(e: Event) {
  const ta = e.target as HTMLTextAreaElement
  if (mirrorRef.value) {
    mirrorRef.value.scrollTop = ta.scrollTop
    mirrorRef.value.scrollLeft = ta.scrollLeft
  }
}

/** 把 @图片N 渲染成蓝色高亮（其他文字原样保留，不加 padding/缩略图，保持光标对齐） */
const renderedHtml = computed(() => {
  const text = props.modelValue || ''
  // 先转义 HTML 特殊字符，避免注入
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  // 匹配 @图片N，只改颜色（不加 padding/border/缩略图，否则光标错位）
  return escaped.replace(/@图片(\d+)/g, (match, numStr) => {
    const idx = parseInt(numStr, 10) - 1
    const item = props.refsSource[idx]
    if (!item) {
      // 序号越界：黄色警告色
      return `<span class="ref-chip ref-chip-warn">${match}</span>`
    }
    return `<span class="ref-chip">${match}</span>`
  })
})

/** 当前 prompt 里被 @ 引用的图片列表（用于上方预览栏） */
const referencedItems = computed(() => {
  const text = props.modelValue || ''
  const matches = [...text.matchAll(/@图片(\d+)/g)]
  const result: { idx: number; preview_url: string; filename: string }[] = []
  const seen = new Set<number>()
  for (const m of matches) {
    const idx = parseInt(m[1], 10) - 1
    if (idx < 0 || seen.has(idx)) continue
    const item = props.refsSource[idx]
    if (!item) continue
    seen.add(idx)
    result.push({ idx, preview_url: item.preview_url, filename: item.filename || `图${idx + 1}` })
  }
  return result
})
</script>

<style scoped>
.mention-textarea-wrap {
  position: relative;
  width: 100%;
}

/* textarea 容器：mirror-layer 和 el-input 共同的定位上下文 */
.textarea-inner-wrap {
  position: relative;
  width: 100%;
}

/* 背景渲染层：绝对定位撑满 inner-wrap，复制 el-input textarea 的样式 */
.mirror-layer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  /* 与 el-textarea__inner 对齐：border-box + 同 padding + 同 border 占位 */
  border: 1px solid transparent;
  padding: 8px 11px;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: auto;
  box-sizing: border-box;
  color: var(--el-text-color-primary);
  /* 隐藏滚动条（视觉由 textarea 主导） */
  scrollbar-width: none;
  z-index: 0;
}
.mirror-layer::-webkit-scrollbar {
  display: none;
}

/* 让 el-input 的 textarea 文字透明、caret 可见、背景透明 */
.mention-textarea-wrap :deep(.el-textarea__inner) {
  background: transparent;
  color: transparent;
  caret-color: var(--el-text-color-primary);
  position: relative;
  z-index: 1;
}
/* placeholder 保留可见（透明文字时仍能看到占位符） */
.mention-textarea-wrap :deep(.el-textarea__inner)::placeholder {
  color: var(--el-text-color-placeholder);
}
/* 聚焦时边框仍由 el-input 控制 */

/* 引用预览栏（textarea 上方，独立显示，不影响光标对齐） */
.ref-preview-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding: 4px 0 6px 0;
  margin-bottom: 2px;
}
.bar-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}
.preview-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 4px;
  padding: 2px 6px 2px 3px;
}
.preview-thumb {
  width: 22px;
  height: 22px;
  object-fit: cover;
  border-radius: 3px;
}
.preview-num {
  font-size: 12px;
  color: #409eff;
  font-weight: 600;
}

/* chip 样式：只改颜色，不加 padding/border（保持字符等宽，光标对齐） */
.mirror-layer :deep(.ref-chip) {
  background: rgba(64, 158, 255, 0.16);
  color: #409eff;
  border-radius: 2px;
  font-weight: 600;
}
/* 越界 chip：黄色警告 */
.mirror-layer :deep(.ref-chip-warn) {
  background: rgba(230, 162, 60, 0.16);
  color: #e6a23c;
}
</style>
