// @ 引用 composable - 在 textarea 输入 @ 时弹出参考图浮层，选中后插入 @图片N token
// 复用层：QuickImageView / VideoGenView / VideoShotView 共享
import { ref, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import type { Ref, ComputedRef } from 'vue'

export interface RefItem {
  /** 缩略图 URL（objectURL 或 data URL） */
  preview_url: string
  /** 文件名（浮层显示，可选） */
  filename?: string
}

export function useReferenceMention(
  textareaRef: Ref<any>,
  refsSource: ComputedRef<RefItem[]>,
  modelValue: Ref<string>,
) {
  const visible = ref(false)
  const activeIdx = ref(0)
  /** 触发 @ 时的光标位置（用于替换字符），-1 表示未触发 */
  let triggerStart = -1
  /** 已绑定的原生 textarea 元素（用于解绑） */
  let boundTa: HTMLTextAreaElement | null = null

  /** 从 el-input ref 或裸 textarea ref 拿到原生 textarea */
  function getTextarea(): HTMLTextAreaElement | null {
    const r = textareaRef.value
    if (!r) return null
    // el-input 模式：ref.$el 是根 div，textarea 是子元素
    if (r.$el && typeof r.$el.querySelector === 'function') {
      return r.$el.querySelector('textarea') as HTMLTextAreaElement | null
    }
    // 裸 textarea 模式
    if (r instanceof HTMLTextAreaElement) {
      return r
    }
    return null
  }

  function openPopover() {
    visible.value = true
    activeIdx.value = 0
  }

  function closePopover() {
    visible.value = false
    triggerStart = -1
  }

  /** @input 回调：检测刚输入的字符是 @（且有参考图）就弹浮层 */
  function onInput(e: Event) {
    const ta = e.target as HTMLTextAreaElement
    const val = ta.value
    const pos = ta.selectionStart
    const lastChar = val[pos - 1]
    if (lastChar !== '@') {
      if (visible.value) closePopover()
      return
    }
    // 无参考图不弹（@ 当普通字符）
    if (refsSource.value.length === 0) {
      if (visible.value) closePopover()
      return
    }
    triggerStart = pos - 1
    openPopover()
  }

  /** @keydown 回调：浮层可见时拦截方向键/Enter/Esc/Tab */
  function onKeydown(e: KeyboardEvent) {
    if (!visible.value) return
    const n = refsSource.value.length
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      activeIdx.value = (activeIdx.value + 1) % n
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      activeIdx.value = (activeIdx.value - 1 + n) % n
    } else if (e.key === 'Enter') {
      e.preventDefault()
      selectMention(activeIdx.value)
    } else if (e.key === 'Escape') {
      e.preventDefault()
      closePopover()
    } else if (e.key === 'Tab') {
      e.preventDefault()
      selectMention(0)
    }
  }

  /** 选中第 idx 张图：把触发的 @ 替换为 @图片N 空格 */
  function selectMention(idx: number) {
    const ta = getTextarea()
    if (!ta || triggerStart < 0) {
      closePopover()
      return
    }
    const token = `@图片${idx + 1} `
    const before = modelValue.value.slice(0, triggerStart)
    const after = modelValue.value.slice(triggerStart + 1) // 跳过触发的 @
    modelValue.value = before + token + after
    closePopover()
    // Vue 重渲染后光标会跳到末尾，需要手动恢复到 token 后
    nextTick(() => {
      const newPos = before.length + token.length
      ta.focus()
      ta.setSelectionRange(newPos, newPos)
    })
  }

  function hoverItem(idx: number) {
    activeIdx.value = idx
  }

  /** 失焦时延迟关闭（避免 click 先于 blur） */
  function onBlur() {
    setTimeout(() => closePopover(), 150)
  }

  function bind() {
    const ta = getTextarea()
    if (!ta || boundTa === ta) return
    ta.addEventListener('input', onInput as EventListener)
    ta.addEventListener('keydown', onKeydown as EventListener)
    ta.addEventListener('blur', onBlur as EventListener)
    boundTa = ta
  }

  function unbind() {
    if (!boundTa) return
    boundTa.removeEventListener('input', onInput as EventListener)
    boundTa.removeEventListener('keydown', onKeydown as EventListener)
    boundTa.removeEventListener('blur', onBlur as EventListener)
    boundTa = null
  }

  onMounted(() => {
    // el-input 内部 textarea 可能在 onMounted 后才挂载，nextTick 确保拿到
    nextTick(bind)
  })
  // ref 变化（v-if 切换 mode 时 el-input 重新挂载）→ 重新绑定
  watch(textareaRef, () => {
    unbind()
    nextTick(bind)
  })
  onBeforeUnmount(unbind)

  // refsSource 变化（用户上传新图）时，若浮层已打开，同步关闭（避免引用越界）
  watch(refsSource, (list) => {
    if (visible.value && list.length === 0) closePopover()
  })

  return {
    visible,
    activeIdx,
    items: refsSource,
    selectMention,
    hoverItem,
    closePopover,
  }
}
