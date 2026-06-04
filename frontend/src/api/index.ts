// 后端 API 封装
import axios from 'axios'
import type { GenerateParams, GenerateResult, ModelsResponse, HealthResponse, VideoGenerateParams, VideoGenerateResponse, VideoTaskStatus, VideoModelInfo, ModelGenerateParams, ModelGenerateResult, ModelSaveParams, ModelListResponse, AnalyzeResponse, AnalyzePersonaResponse, PlanShotsResponse, RecommendStylesResponse, PlanAplusResponse } from '../types'

const api = axios.create({
  baseURL: '',
  timeout: 120000,  // 生图可能需要较长时间
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
  })
  return data
}

// === 视频模块 ===

// 提交视频生成任务
export async function submitVideo(params: VideoGenerateParams): Promise<VideoGenerateResponse> {
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

  const { data } = await api.post('/api/video/generate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,  // 风格转换 + 视频提交可能较久
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
