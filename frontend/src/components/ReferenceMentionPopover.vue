<template>
  <Teleport to="body">
    <div
      v-if="visible && items.length > 0"
      class="ref-mention-popover"
      :style="{ top: `${pos.top}px`, left: `${pos.left}px` }"
      @mousedown.prevent
    >
      <div class="popover-header">选择参考图</div>
      <ul class="popover-list">
        <li
          v-for="(item, idx) in items"
          :key="idx"
          :class="['popover-item', { active: idx === activeIdx }]"
          @mouseenter="$emit('hover', idx)"
          @click="$emit('select', idx)"
        >
          <span class="item-idx">图片{{ idx + 1 }}</span>
          <img :src="item.preview_url" class="item-thumb" :alt="item.filename || ''" />
          <span class="item-name" :title="item.filename">{{ item.filename || `图${idx + 1}` }}</span>
        </li>
      </ul>
      <div class="popover-footer">
        <span>↑↓ 切换</span>
        <span>Enter 选中</span>
        <span>Esc 取消</span>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { PropType } from 'vue'
import type { RefItem } from '../composables/useReferenceMention'

const props = defineProps({
  visible: { type: Boolean, default: false },
  items: { type: Array as PropType<RefItem[]>, default: () => [] },
  activeIdx: { type: Number, default: 0 },
  /** el-input ref 或裸 textarea ref，用于定位浮层 */
  anchorRef: { type: Object as PropType<any>, default: null },
})

defineEmits<{
  select: [idx: number]
  hover: [idx: number]
  close: []
}>()

const pos = ref({ top: 0, left: 0 })

function getNativeTextarea(el: any): HTMLTextAreaElement | null {
  if (!el) return null
  if (el.$el && typeof el.$el.querySelector === 'function') {
    return el.$el.querySelector('textarea') as HTMLTextAreaElement | null
  }
  if (el instanceof HTMLTextAreaElement) return el
  return null
}

function updatePos() {
  const ta = getNativeTextarea(props.anchorRef)
  if (!ta) return
  const rect = ta.getBoundingClientRect()
  // 浮层挂在 textarea 下方左对齐（MVP：不跟随光标 x 坐标）
  pos.value = {
    top: rect.bottom + 4,
    left: rect.left,
  }
}

watch(
  () => props.visible,
  async (v) => {
    if (v) {
      // 浮层出现前等 DOM 就绪
      await nextTick()
      updatePos()
    }
  },
)

// 滚动/resize 时更新位置（轻量监听）
watch(
  () => props.visible,
  (v, _, onCleanup) => {
    if (!v) return
    const handler = () => updatePos()
    window.addEventListener('scroll', handler, true)
    window.addEventListener('resize', handler)
    onCleanup(() => {
      window.removeEventListener('scroll', handler, true)
      window.removeEventListener('resize', handler)
    })
  },
)
</script>

<style scoped>
.ref-mention-popover {
  position: fixed;
  z-index: 3000;
  min-width: 280px;
  max-width: 360px;
  background: var(--el-bg-color, #fff);
  border: 1px solid var(--el-border-color-light, #dcdfe6);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  user-select: none;
}

.popover-header {
  padding: 6px 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
  background: var(--el-fill-color-light, #f5f7fa);
  border-bottom: 1px solid var(--el-border-color-lighter, #ebeef5);
}

.popover-list {
  list-style: none;
  margin: 0;
  padding: 4px;
  max-height: 240px;
  overflow-y: auto;
}

.popover-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s;
}

.popover-item.active,
.popover-item:hover {
  background: var(--el-color-primary-light-9, #ecf5ff);
}

.item-idx {
  flex-shrink: 0;
  min-width: 48px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary, #409eff);
}

.item-thumb {
  width: 32px;
  height: 32px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
}

.item-name {
  flex: 1;
  font-size: 12px;
  color: var(--el-text-color-primary, #303133);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.popover-footer {
  display: flex;
  justify-content: space-around;
  padding: 6px 12px;
  font-size: 11px;
  color: var(--el-text-color-placeholder, #a8abb2);
  background: var(--el-fill-color-lighter, #fafafa);
  border-top: 1px solid var(--el-border-color-lighter, #ebeef5);
}
</style>
