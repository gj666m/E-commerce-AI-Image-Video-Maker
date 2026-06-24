// 对话式 Agent 类型定义

// SSE 事件类型
export interface AgentTokenEvent {
  type: 'token'
  content: string
}

export interface AgentToolStartEvent {
  type: 'tool_start'
  tool: string
  args: Record<string, unknown>
}

export interface AgentToolEndEvent {
  type: 'tool_end'
  tool: string
  result: string
}

export interface AgentImageEvent {
  type: 'image'
  image_id: string
  data_url: string
  prompt_used: string
  model_used: string
  cost: number
  currency: string
  aspect_ratio: string
}

export interface AgentQcCheckingEvent {
  type: 'qc_checking'
  image_id: string
  retry: number
}

export interface AgentQcPassedEvent {
  type: 'qc_passed'
  score: number
  retry: number
}

export interface AgentQcRetryEvent {
  type: 'qc_retry'
  score: number
  issues: string[]
  suggestions: string
  retry: number
}

export interface AgentQcErrorEvent {
  type: 'qc_error'
  message: string
}

export interface AgentDoneEvent {
  type: 'done'
}

export interface AgentErrorEvent {
  type: 'error'
  message: string
}

export type AgentSSEEvent =
  | AgentTokenEvent
  | AgentToolStartEvent
  | AgentToolEndEvent
  | AgentImageEvent
  | AgentQcCheckingEvent
  | AgentQcPassedEvent
  | AgentQcRetryEvent
  | AgentQcErrorEvent
  | AgentDoneEvent
  | AgentErrorEvent

// 工具步骤（折叠展示）
export interface ToolStep {
  id: string
  tool: string
  args: Record<string, unknown>
  status: 'running' | 'done' | 'error'
  result?: string
}

// 质检状态
export interface QcStatus {
  state: 'checking' | 'passed' | 'retry' | 'error'
  score?: number
  issues?: string[]
  suggestions?: string
  retry: number
  message?: string
}

// 消息
export interface AgentImage {
  image_id: string
  data_url: string
  prompt_used: string
  model_used: string
  cost: number
  currency: string
  aspect_ratio: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string           // 文本内容（流式追加）
  images: AgentImage[]      // 生成图
  toolSteps: ToolStep[]     // 工具步骤
  qcStatus?: QcStatus       // 质检状态（最近一次）
  qcHistory: QcStatus[]     // 质检历史（多轮重试）
  pending?: boolean         // 是否正在生成
  error?: string            // 错误信息
}

// 上传参考图返回
export interface UploadedRef {
  image_id: string
  filename: string
}
