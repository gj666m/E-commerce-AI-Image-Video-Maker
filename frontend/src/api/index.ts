// 后端 API 封装
import axios from 'axios'
import type { GenerateParams, GenerateResult, ModelsResponse, HealthResponse, VideoGenerateParams, VideoGenerateResponse, VideoTaskStatus, VideoModelInfo, ModelGenerateParams, ModelGenerateResult, ModelSaveParams, ModelListResponse, AnalyzeResponse, AnalyzePersonaResponse, PlanShotsResponse, RecommendStylesResponse, PlanAplusResponse, LoginResponse, UserItem, HistoryItem, VideoHistoryItem } from '../types'

const api = axios.create({
  baseURL: '',
  timeout: 120000,  // 生图可能需要较长时间
})

// 请求拦截器：自动附加 JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ai-zw-token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：401 自动跳转登录
api.interceptors.response.use(undefined, async (error) => {
  if (error.response?.status === 401) {
    localStorage.removeItem('ai-zw-token')
    localStorage.removeItem('ai-zw-user')
    // 避免在登录页循环跳转
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }

  const config = error.config
  if (!config) return Promise.reject(error)

  // 429 限流/额度不足不重试，直接抛出让业务层处理
  if (error.response?.status === 429) {
    return Promise.reject(error)
  }

  // POST 视频生成/图片生成等写操作不重试（可能已执行，重试会重复扣费）
  if (config.method === 'post') {
    return Promise.reject(error)
  }

  // 只重试网络错误和 5xx，不重试 4xx 业务错误
  const isNetworkError = !error.response
  const isServerError = error.response?.status >= 500
  if (!isNetworkError && !isServerError) return Promise.reject(error)

  // 已达最大重试次数
  config.__retryCount = config.__retryCount || 0
  if (config.__retryCount >= 2) return Promise.reject(error)

  config.__retryCount++
  // 指数退避：1s, 2s
  await new Promise(r => setTimeout(r, 1000 * config.__retryCount))
  return api(config)
})

// 健康检查
export async function healthCheck(): Promise<HealthResponse> {
  const { data } = await api.get('/api/health')
  return data
}

// 获取模型列表
export async function getModels(): Promise<ModelsResponse> {
  const { data } = await api.get('/api/models')
  return data
}

// 生成图片
export async function generateImage(params: GenerateParams): Promise<GenerateResult> {
  const formData = new FormData()
  formData.append('task_type', params.task_type)
  formData.append('description', params.description)

  if (params.image) formData.append('image', params.image)
  if (params.style) formData.append('style', params.style)
  if (params.model_name) formData.append('model_name', params.model_name)
  if (params.aspect_ratio) formData.append('aspect_ratio', params.aspect_ratio)
  if (params.custom_prompt) formData.append('custom_prompt', params.custom_prompt)
  if (params.count) formData.append('count', String(params.count))
  if (params.product_info) formData.append('product_info', params.product_info)
  if (params.persona) formData.append('persona', params.persona)
  if (params.scene) formData.append('scene', params.scene)
  if (params.images && params.images.length > 0) {
    for (const file of params.images) {
      formData.append('images', file)
    }
  }

  // A+ 图专用参数
  if (params.selling_point) formData.append('selling_point', params.selling_point)
  if (params.headline) formData.append('headline', params.headline)
  if (params.body_text) formData.append('body_text', params.body_text)
  if (params.layout) formData.append('layout', params.layout)

  const { data } = await api.post('/api/generate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,  // GPT-Image-2-VIP 4K 需要 90-150s，留 300s 余量
  })
  return data
}

// === 视频模块 ===

// 提交视频生成任务
export async function submitVideo(params: VideoGenerateParams, signal?: AbortSignal): Promise<VideoGenerateResponse> {
  const formData = new FormData()
  formData.append('description', params.description)

  // 商品图（新参数优先）
  if (params.product_images && params.product_images.length > 0) {
    for (const file of params.product_images) {
      formData.append('product_images', file)
    }
  }
  // 模特素材图
  if (params.model_images && params.model_images.length > 0) {
    for (const file of params.model_images) {
      formData.append('model_images', file)
    }
  }
  // 模特图含人脸
  if (params.model_has_face !== undefined) {
    formData.append('model_has_face', String(params.model_has_face))
  }
  // 兼容旧参数：无新参数时用旧 images
  if (!params.product_images?.length && params.images && params.images.length > 0) {
    for (const file of params.images) {
      formData.append('images', file)
    }
  }

  if (params.duration) formData.append('duration', String(params.duration))
  if (params.model_name) formData.append('model_name', params.model_name)
  if (params.style) formData.append('style', params.style)
  if (params.custom_prompt) formData.append('custom_prompt', params.custom_prompt)
  if (params.ratio) formData.append('ratio', params.ratio)
  if (params.generate_audio !== undefined) formData.append('generate_audio', String(params.generate_audio))
  if (params.camera_movement) formData.append('camera_movement', params.camera_movement)
  if (params.product_info) formData.append('product_info', params.product_info)
  if (params.resolution) formData.append('resolution', params.resolution)

  const { data } = await api.post('/api/video/generate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 360000,  // 风格转换 + 大图上传可能较久（最多 6 分钟）
    signal,
  })
  return data
}

// 查询视频任务状态
export async function getVideoStatus(taskId: string): Promise<VideoTaskStatus> {
  const { data } = await api.get(`/api/video/status/${taskId}`)
  return data
}

// 获取视频模型列表
export async function getVideoModels(): Promise<{ models: VideoModelInfo[]; default: string }> {
  const { data } = await api.get('/api/video/models')
  return data
}

// 获取当前用户进行中的视频任务（切页面后恢复用）
export async function getVideoTasks(): Promise<{ tasks: Array<{ id: string; status: string; prompt: string; provider_name: string; created_at: string }> }> {
  const { data } = await api.get('/api/video/tasks')
  return data
}

export default api

// === 模特模块 ===

// 生成模特（支持多张参考图）
export async function generateModel(params: ModelGenerateParams, refImages?: File[]): Promise<ModelGenerateResult> {
  const formData = new FormData()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      formData.append(key, String(value))
    }
  }
  // 参考图（图生图模式，支持 1-3 张）
  if (refImages && refImages.length > 0) {
    for (const file of refImages) {
      formData.append('images', file)
    }
  }
  const { data } = await api.post('/api/model/generate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return data
}

// 保存模特到模特库
export async function saveModel(params: ModelSaveParams): Promise<{ success: boolean; model_id: string }> {
  const { data } = await api.post('/api/model/save', params)
  return data
}

// 获取模特库列表
export async function getModelList(): Promise<ModelListResponse> {
  const { data } = await api.get('/api/model/list')
  return data
}

// 删除模特
export async function deleteModel(modelId: string): Promise<{ success: boolean }> {
  const { data } = await api.delete(`/api/model/${modelId}`)
  return data
}

// === 商品分析模块 ===

// 商品视觉分析
export async function analyzeProduct(image: File, extraPrompt?: string, existingInfo?: string): Promise<AnalyzeResponse> {
  const formData = new FormData()
  formData.append('image', image)
  if (extraPrompt) formData.append('extra_prompt', extraPrompt)
  if (existingInfo) formData.append('existing_info', existingInfo)

  const { data } = await api.post('/api/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return data
}

// 博主人设分析
export async function analyzePersona(image: File): Promise<AnalyzePersonaResponse> {
  const formData = new FormData()
  formData.append('image', image)

  const { data } = await api.post('/api/analyze-persona', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return data
}

// 自由文本查询（图片 + prompt → 纯文本）
export async function analyzeFree(image: File, prompt: string): Promise<{ success: boolean; text: string }> {
  const formData = new FormData()
  formData.append('image', image)
  formData.append('prompt', prompt)

  const { data } = await api.post('/api/analyze-free', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return data
}

// 视频 Prompt 智能扩写（简短动作描述 → 专业视频叙事 prompt）
export async function enhanceVideoPrompt(
  description: string,
  duration: number,
  style?: string,
  image?: File,
): Promise<{ success: boolean; prompt: string }> {
  const formData = new FormData()
  formData.append('description', description)
  formData.append('duration', String(duration))
  if (style) formData.append('style', style)
  if (image) formData.append('image', image)

  const { data } = await api.post('/api/enhance-video-prompt', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
  })
  return data
}

// AI 种草图策划
export async function planShots(
  images: File[],
  productInfo?: string,
  persona?: string,
): Promise<PlanShotsResponse> {
  const formData = new FormData()
  for (const file of images) {
    formData.append('images', file)
  }
  if (productInfo) formData.append('product_info', productInfo)
  if (persona) formData.append('persona', persona)

  const { data } = await api.post('/api/plan-shots', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return data
}

// AI A+ 内容策划
export async function planAplus(
  images: File[],
  productInfo?: string,
): Promise<PlanAplusResponse> {
  const formData = new FormData()
  for (const file of images) {
    formData.append('images', file)
  }
  if (productInfo) formData.append('product_info', productInfo)

  const { data } = await api.post('/api/plan-aplus', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return data
}

// AI 风格推荐
export async function recommendStyles(
  plans: { title: string; scene: string; pose: string; angle: string; selling_point: string; prompt_hint: string }[],
  productInfo?: string,
  persona?: string,
): Promise<RecommendStylesResponse> {
  const formData = new FormData()
  formData.append('plans', JSON.stringify(plans))
  if (productInfo) formData.append('product_info', productInfo)
  if (persona) formData.append('persona', persona)

  const { data } = await api.post('/api/recommend-styles', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return data
}

// 从 catch 的 unknown 错误中提取可读消息
export function getErrorMessage(e: unknown, fallback = '操作失败，请稍后重试'): string {
  if (typeof e === 'object' && e !== null) {
    const resp = (e as { response?: { data?: { detail?: string } } }).response
    if (resp?.data?.detail) return resp.data.detail
    const msg = (e as { message?: string }).message
    if (msg) return msg
  }
  return fallback
}

// === 认证模块 ===

// 用户登录
export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post('/api/auth/login', { username, password })
  return data
}

// 获取当前用户信息
export async function getMe(): Promise<{ success: boolean; user: { id: number; username: string; role: string } }> {
  const { data } = await api.get('/api/auth/me')
  return data
}

// === 管理员用户管理 ===

// 获取用户列表
export async function getUsers(): Promise<{ success: boolean; users: UserItem[] }> {
  const { data } = await api.get('/api/auth/users')
  return data
}

// 创建用户
export async function createUser(username: string, password: string, role: string): Promise<{ success: boolean; message: string }> {
  const { data } = await api.post('/api/auth/users', { username, password, role })
  return data
}

// 删除用户
export async function deleteUser(userId: number): Promise<{ success: boolean; message: string }> {
  const { data } = await api.delete(`/api/auth/users/${userId}`)
  return data
}

// 更新用户
export async function updateUser(userId: number, payload: { password?: string; role?: string }): Promise<{ success: boolean; message: string }> {
  const { data } = await api.put(`/api/auth/users/${userId}`, payload)
  return data
}

// ====== 图片生成历史 ======

// 获取历史列表
export async function listHistory(
  taskType?: string,
  opts?: { includeDeleted?: boolean },
): Promise<{ success: boolean; items: HistoryItem[]; count: number }> {
  const params: Record<string, string> = {}
  if (taskType) params.task_type = taskType
  if (opts?.includeDeleted) params.include_deleted = 'true'
  const { data } = await api.get('/api/history', { params })
  return data
}

// 删除单条历史
export async function deleteHistory(historyId: string): Promise<{ success: boolean; message: string }> {
  const { data } = await api.delete(`/api/history/${historyId}`)
  return data
}

// 清空当前用户全部历史
export async function clearHistory(): Promise<{ success: boolean; message: string; deleted: number }> {
  const { data } = await api.post('/api/history/clear')
  return data
}

// === 视频生成历史 ===

// 获取视频历史列表
export async function listVideoHistory(
  opts?: { includeDeleted?: boolean },
): Promise<{ success: boolean; items: VideoHistoryItem[]; count: number }> {
  const params: Record<string, string> = {}
  if (opts?.includeDeleted) params.include_deleted = 'true'
  const { data } = await api.get('/api/video/history', { params })
  return data
}

// 删除单条视频历史
export async function deleteVideoHistory(taskId: string): Promise<{ success: boolean; message: string }> {
  const { data } = await api.delete(`/api/video/history/${taskId}`)
  return data
}

// 清空当前用户全部视频历史
export async function clearVideoHistory(): Promise<{ success: boolean; message: string; deleted: number }> {
  const { data } = await api.post('/api/video/history/clear')
  return data
}

// API易余额查询（全员可见，15 秒缓存）
export interface BalanceResponse {
  success: boolean
  available: boolean
  message?: string
  quota_usd?: number
  used_usd?: number
  request_count?: number
}

export async function getBalance(opts?: { fresh?: boolean }): Promise<BalanceResponse> {
  const params: Record<string, string> = {}
  if (opts?.fresh) params.fresh = 'true'
  const { data } = await api.get('/api/balance', { params })
  return data
}
