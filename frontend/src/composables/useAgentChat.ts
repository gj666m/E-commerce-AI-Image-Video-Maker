// Agent 对话 composable - SSE 消费 + 消息管理
// 用 fetch + ReadableStream（非 EventSource，因需 POST + Authorization header）
import { ref, reactive } from 'vue'
import type {
  ChatMessage,
  AgentImage,
  ToolStep,
  QcStatus,
  UploadedRef,
} from '../types/agent'
import { genId } from '../utils/genId'

const THREAD_KEY = 'agent_thread_id'

export interface UseAgentChatOptions {
  scrollFn?: () => void  // 滚动到底部回调
}

export function useAgentChat(options: UseAgentChatOptions = {}) {
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  // 持久化 threadId 到 localStorage：刷新/重进页面可恢复同一对话
  const savedThreadId = localStorage.getItem(THREAD_KEY)
  const threadId = ref<string>(savedThreadId || genId())
  if (!savedThreadId) localStorage.setItem(THREAD_KEY, threadId.value)
  const uploadedRefs = ref<UploadedRef[]>([])
  const abortController = ref<AbortController | null>(null)

  function newConversation() {
    // 停止当前请求
    stop()
    messages.value = []
    threadId.value = genId()
    localStorage.setItem(THREAD_KEY, threadId.value)
    // 释放本地缩略图 objectURL，避免内存泄漏
    uploadedRefs.value.forEach((r) => {
      if (r.thumb_url) URL.revokeObjectURL(r.thumb_url)
    })
    uploadedRefs.value = []
  }

  /** 从后端恢复历史对话（页面加载时调一次） */
  async function restoreHistory(): Promise<boolean> {
    const token = localStorage.getItem('ai-zw-token')
    try {
      const resp = await fetch(`/api/agent/history/${threadId.value}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!resp.ok) return false
      const data = await resp.json()
      if (!data || !data.exists || !Array.isArray(data.messages) || data.messages.length === 0) {
        return false
      }
      // 把后端还原的 plain object 包装成响应式 ChatMessage
      messages.value = data.messages.map((m: any) => ({
        id: m.id || genId(),
        role: m.role,
        content: m.content || '',
        images: Array.isArray(m.images) ? m.images : [],
        toolSteps: Array.isArray(m.toolSteps) ? m.toolSteps : [],
        qcHistory: [],
      }))
      return true
    } catch {
      return false
    }
  }

  function stop() {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    loading.value = false
  }

  async function uploadImages(files: File[]): Promise<UploadedRef[]> {
    if (!files.length) return []
    const token = localStorage.getItem('ai-zw-token')
    const formData = new FormData()
    for (const f of files) formData.append('files', f)
    const resp = await fetch('/api/agent/upload-images', {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!resp.ok) {
      const detail = await resp.json().catch(() => ({}))
      throw new Error(detail.detail || `上传失败 ${resp.status}`)
    }
    const data = await resp.json()
    const remoteRefs: UploadedRef[] = data.images || []
    // 后端按入参顺序返回，本地 File → objectURL 配对（供 ChatInput 显示缩略图）
    const refs: UploadedRef[] = remoteRefs.map((r, i) => ({
      ...r,
      thumb_url: files[i] ? URL.createObjectURL(files[i]) : undefined,
    }))
    uploadedRefs.value.push(...refs)
    return refs
  }

  function removeRef(imageId: string) {
    const target = uploadedRefs.value.find((r) => r.image_id === imageId)
    if (target?.thumb_url) URL.revokeObjectURL(target.thumb_url)
    uploadedRefs.value = uploadedRefs.value.filter((r) => r.image_id !== imageId)
  }

  async function sendMessage(text: string) {
    const content = text.trim()
    if (!content || loading.value) return

    // 用户消息
    const userMsg: ChatMessage = {
      id: genId(),
      role: 'user',
      content,
      images: [],
      toolSteps: [],
      qcHistory: [],
    }
    // AI 消息（流式追加）
    // 用 reactive() 包裹：push 进 messages.value 后，闭包里持有的就是响应式 proxy，
    // 后续 aiMsg.content += token 的修改才能触发模板重渲染
    // （若用裸对象，闭包持有 raw 引用，改 raw 不会触发 Vue 更新 — 表现为"必须刷新才看到内容"）
    const aiMsg: ChatMessage = reactive({
      id: genId(),
      role: 'assistant',
      content: '',
      images: [],
      toolSteps: [],
      qcHistory: [],
      pending: true,
    })
    messages.value.push(userMsg, aiMsg)

    loading.value = true
    abortController.value = new AbortController()

    const token = localStorage.getItem('ai-zw-token')
    try {
      const resp = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: content,
          thread_id: threadId.value,
          uploaded_image_ids: uploadedRefs.value.map((r) => r.image_id),
        }),
        signal: abortController.value.signal,
      })

      if (!resp.ok || !resp.body) {
        const detail = await resp.json().catch(() => ({}))
        aiMsg.error = detail.detail || `请求失败 ${resp.status}`
        aiMsg.pending = false
        return
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      // 解析 SSE：按 \n\n 分帧，提取 data: {...}
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        let sepIdx: number
        // SSE 帧以空行分隔
        while ((sepIdx = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, sepIdx)
          buffer = buffer.slice(sepIdx + 2)
          // 提取 data: 行
          const dataLine = frame
            .split('\n')
            .find((l) => l.startsWith('data:'))
          if (!dataLine) continue
          const jsonStr = dataLine.slice(5).trim()
          if (!jsonStr) continue

          let ev
          try {
            ev = JSON.parse(jsonStr)
          } catch {
            continue
          }
          handleEvent(ev, aiMsg)
          options.scrollFn?.()
        }
      }
    } catch (e: unknown) {
      if ((e as Error).name === 'AbortError') {
        aiMsg.content += '\n\n_(已停止)_'
      } else {
        aiMsg.error = (e as Error).message || '请求异常'
      }
    } finally {
      aiMsg.pending = false
      loading.value = false
      abortController.value = null
      options.scrollFn?.()
    }
  }

  function handleEvent(ev: { type: string; [k: string]: unknown }, aiMsg: ChatMessage) {
    switch (ev.type) {
      case 'token': {
        aiMsg.content += ev.content as string
        break
      }
      case 'tool_start': {
        const step: ToolStep = {
          id: genId(),
          tool: ev.tool as string,
          args: (ev.args as Record<string, unknown>) || {},
          status: 'running',
          started_at: Date.now(),
        }
        aiMsg.toolSteps.push(step)
        break
      }
      case 'tool_end': {
        // 更新最后一个同名 running 的 step
        const step = [...aiMsg.toolSteps]
          .reverse()
          .find((s) => s.tool === ev.tool && s.status === 'running')
        if (step) {
          step.status = 'done'
          step.result = ev.result as string
        }
        break
      }
      case 'image': {
        const img: AgentImage = {
          image_id: ev.image_id as string,
          data_url: ev.data_url as string,
          prompt_used: ev.prompt_used as string,
          model_used: ev.model_used as string,
          cost: ev.cost as number,
          currency: ev.currency as string,
          aspect_ratio: ev.aspect_ratio as string,
        }
        aiMsg.images.push(img)
        break
      }
      case 'qc_checking': {
        const st: QcStatus = { state: 'checking', retry: ev.retry as number }
        aiMsg.qcStatus = st
        aiMsg.qcHistory.push(st)
        break
      }
      case 'qc_passed': {
        const st: QcStatus = { state: 'passed', score: ev.score as number, retry: ev.retry as number }
        // 更新最后一条 checking
        if (aiMsg.qcHistory.length && aiMsg.qcHistory[aiMsg.qcHistory.length - 1].state === 'checking') {
          aiMsg.qcHistory[aiMsg.qcHistory.length - 1] = st
        } else {
          aiMsg.qcHistory.push(st)
        }
        aiMsg.qcStatus = st
        break
      }
      case 'qc_retry': {
        const st: QcStatus = {
          state: 'retry',
          score: ev.score as number,
          issues: ev.issues as string[],
          suggestions: ev.suggestions as string,
          retry: ev.retry as number,
        }
        if (aiMsg.qcHistory.length && aiMsg.qcHistory[aiMsg.qcHistory.length - 1].state === 'checking') {
          aiMsg.qcHistory[aiMsg.qcHistory.length - 1] = st
        } else {
          aiMsg.qcHistory.push(st)
        }
        aiMsg.qcStatus = st
        break
      }
      case 'qc_error': {
        const st: QcStatus = { state: 'error', retry: 0, message: ev.message as string }
        aiMsg.qcStatus = st
        break
      }
      case 'error': {
        aiMsg.error = ev.message as string
        break
      }
      case 'done': {
        // 结束
        break
      }
    }
  }

  return {
    messages,
    loading,
    threadId,
    uploadedRefs,
    sendMessage,
    stop,
    newConversation,
    uploadImages,
    removeRef,
    restoreHistory,
  }
}
