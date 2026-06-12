// 生成请求参数
export interface GenerateParams {
  task_type: 'outfit' | 'seed_grass' | 'product_main' | 'aplus'
  image?: File
  images?: File[]    // 多图参考（种草图等多图模式）
  description: string
  style?: string
  model_name?: string
  aspect_ratio?: string
  custom_prompt?: string
  enable_analysis?: boolean
  count?: number          // 生成数量 1-4
  product_info?: string  // 商品信息文本（用户输入或AI分析）
  persona?: string        // 博主人设描述（种草图专用）
  scene?: string          // 场景描述（种草图专用）
  // A+ 图专用参数
  selling_point?: string
  headline?: string
  body_text?: string
  layout?: string
}

// 生成结果
export interface GenerateResult {
  success: boolean
  images: string[]       // base64 编码的图片
  prompt_used: string
  model_used: string
  cost: number
  currency: string       // 费用币种：¥ 或 $
  image_info?: {
    width: number
    height: number
    format: string
    mode: string
  }
  error?: string
}

// 模型信息
export interface ModelInfo {
  name: string
  display_name: string
  available: boolean
  description: string
  capabilities: string[]      // ['text_to_image', 'image_to_image']
  api_key_hint: string
}

// 模型列表响应
export interface ModelsResponse {
  models: ModelInfo[]
  default: string
  total: number
}

// 健康检查响应
export interface HealthResponse {
  status: string
  env: string
  providers: Record<string, boolean>
  mock_mode: boolean
}

// === 视频模块 ===

// 视频生成请求参数
export interface VideoGenerateParams {
  image?: File
  images?: File[]            // [旧] 多参考图（兼容）
  product_images?: File[]    // 商品图（1-6张）
  model_images?: File[]      // 模特素材图（0-3张，可选）
  model_has_face?: boolean   // 模特图含人脸，默认 true
  description: string
  duration?: number  // 5 / 10
  model_name?: string
  style?: string
  custom_prompt?: string
  ratio?: string     // 16:9 / 9:16 / 1:1
  generate_audio?: boolean
  camera_movement?: string  // 推近/拉远/环绕/平移/跟随
  product_info?: string     // 商品信息文本
  resolution?: string       // 480p / 720p / 1080p
}

// 视频生成提交响应
export interface VideoGenerateResponse {
  success: boolean
  task_id: string
  status: string
}

// 视频任务状态
export interface VideoTaskStatus {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number  // 0-100
  video_url?: string
  model_used: string
  prompt_used: string
  cost: number
  currency: string   // 费用币种：¥ 或 $
  error?: string
}

// 视频模型信息
export interface VideoModelInfo {
  name: string
  display_name: string
  available: boolean
  description: string
  capabilities: string[]
  api_key_hint: string
}

// === 模特模块 ===

// 模特生成请求
export interface ModelGenerateParams {
  gender: string
  ethnicity: string
  age: string
  body_type: string
  hair_desc?: string
  expression?: string
  pose?: string
  clothing?: string
  background: string
  composition: string
  style: string
  custom_desc?: string
  count?: number
  aspect_ratio?: string
  model_name?: string
}

// 模特生成结果
export interface ModelGenerateResult {
  success: boolean
  images: string[]       // base64 数组
  prompt_used: string
  model_used: string
  cost: number
  currency?: string
}

// 模特保存请求
export interface ModelSaveParams {
  name: string
  params: Record<string, string>
  image_data: string     // base64
}

// 模特库条目
export interface ModelItem {
  id: string
  name: string
  params: Record<string, string>
  file: string
  thumbnail: string
  created_at: string
}

// 模特库列表响应
export interface ModelListResponse {
  success: boolean
  models: ModelItem[]
}

// === 商品分析模块 ===

// 商品分析结果
export interface ProductAnalysis {
  category: string
  style: string
  fabric: string
  color: string
  pattern: string
  details: string
  selling_points: string[]
  suitable_scenes: string[]
  target_audience: string
  season: string
  keywords: string[]
  _meta?: {
    model: string
    usage: Record<string, number>
  }
}

// 商品分析响应
export interface AnalyzeResponse {
  success: boolean
  analysis: ProductAnalysis
  image_info?: {
    width: number
    height: number
    format: string
    mode: string
  }
}

// === 博主人设分析模块 ===

// 博主人设分析结果
export interface PersonaAnalysis {
  style: string
  age_range: string
  vibe: string
  suitable_scenes: string[]
  color_preference: string
  description: string
  _meta?: {
    model: string
    usage: Record<string, number>
  }
}

// 人设分析响应
export interface AnalyzePersonaResponse {
  success: boolean
  persona: PersonaAnalysis
  image_info?: {
    width: number
    height: number
    format: string
    mode: string
  }
}

// === AI 策划模块 ===

// 单张策划方案
export interface ShotPlan {
  title: string
  scene: string
  pose: string
  angle: string
  selling_point: string
  prompt_hint: string
}

// 策划响应
export interface PlanShotsResponse {
  success: boolean
  plans: ShotPlan[]
}

// === 风格推荐模块 ===

// 单个风格方向
export interface StyleOption {
  name: string
  description: string
  prompt_modifier: string
}

// 风格推荐响应
export interface RecommendStylesResponse {
  success: boolean
  styles: StyleOption[]
}

// === 独立卡片管理 ===

// 单张生成结果卡片
export interface ResultCard {
  imageBase64: string
  status: 'success' | 'loading' | 'failed'
  promptUsed: string
  error?: string
  /** 内部使用：关联的方案索引（种草图/A+策划重试时记录） */
  _planIdx?: number
}

// === A+ 策划模块 ===

// 单张 A+ 策划方案
export interface AplusPlan {
  type: string          // 图片类型（卖点突出型、场景氛围型等）
  selling_point: string // 核心卖点
  headline: string      // 标题文字（英文）
  body_text: string     // 正文文字（英文）
  layout: string        // 布局类型
  scene: string         // 场景/背景描述
  prompt_hint: string   // 额外 prompt 提示词
}

// A+ 策划响应
export interface PlanAplusResponse {
  success: boolean
  plans: AplusPlan[]
}
