// Prompt 本地拼装工具（续15 工坊要素卡片模式）
// 与后端 ENHANCE_IMAGE_PROMPT_SYSTEM 质量底线保持一致；改动需 e2e 验证
import type { PromptElements } from '../types'
import type { VideoShot } from '../api'

// 质量底线尾巴（与后端 gemini_provider.py ENHANCE_IMAGE_PROMPT_SYSTEM line 157 一致）
export const QUALITY_TAIL =
  'photorealistic, sharp focus, natural skin texture, no deformed hands, no extra fingers, no text artifacts, high detail'

// 字段顺序与后端 ENHANCE_STRUCTURED_FIELD_ORDER 对齐
// 顺序影响 Seedream 出图风格，改动需 e2e 验证
const FIELD_ORDER: Array<{ key: keyof PromptElements; label: string }> = [
  { key: 'subject', label: '主体' },
  { key: 'clothing', label: '服装' },
  { key: 'scene', label: '场景' },
  { key: 'lighting', label: '光影' },
  { key: 'lens', label: '镜头' },
  { key: 'rhythm', label: '节奏' },
  { key: 'composition', label: '构图' },
  { key: 'style_keywords', label: '风格' },
]

// 比例 → 英文描述后缀
const RATIO_DESC: Record<string, string> = {
  '1:1': '1:1 square composition',
  '3:4': 'vertical 3:4 portrait composition',
  '4:3': 'horizontal 4:3 composition',
  '4:5': 'vertical 4:5 portrait composition',
  '9:16': 'vertical 9:16 composition',
  '16:9': 'horizontal 16:9 cinematic composition',
}

// 用 label 顺序导出（供 ElementCardsGrid 渲染）
export const ELEMENT_FIELDS = FIELD_ORDER.slice()

/**
 * 把 8 要素本地拼装为完整 prompt（图片类用）。
 * 规则：按 FIELD_ORDER 顺序拼接非空字段 + 质量底线尾巴 + 比例后缀。
 * 注：与 AI 拼装结果可能有差异，AI 拼装是「自然连贯散文」，本地拼装是「机械拼接」。
 * 用户改字段后用本地拼装覆盖 form.prompt，AI 拼装结果仅作起点。
 */
export function assembleImagePrompt(elements: PromptElements, aspectRatio?: string): string {
  const parts: string[] = []
  for (const { key } of FIELD_ORDER) {
    const v = (elements[key] || '').trim()
    if (v) parts.push(v)
  }
  parts.push(QUALITY_TAIL)
  if (aspectRatio) {
    const desc = RATIO_DESC[aspectRatio]
    if (desc) parts.push(desc)
  }
  return parts.join(', ')
}

/**
 * 把分镜表本地拼装为预览 prompt（video_shots 类用）。
 * 注：仅预览展示用，真实提交走后端 prompt_engine.build_shot_video_prompt 权威拼装。
 */
export function assembleShotsPreview(shots: VideoShot[]): string {
  if (!shots || shots.length === 0) return ''
  return shots
    .map(
      (s, i) =>
        `【分镜 ${i + 1} / ${s.start_time}-${s.end_time}s · ${s.purpose}】${s.action}。镜头：${s.camera}。焦点：${s.focus}。服装强调：${s.garment_focus}。风格：${s.visual_style}。`,
    )
    .join('\n')
}
