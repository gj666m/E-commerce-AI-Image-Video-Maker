// 智能创意 prompt 统一封装：按 task_type 路由到图片接口或视频接口
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { enhanceImagePrompt, enhanceVideoPrompt, getErrorMessage } from '../api'
import type { PromptTaskType } from '../types'

export interface EnhanceParams {
  taskType: PromptTaskType
  userText?: string         // 用户已填的简短方向（可空）
  aspectRatio?: string      // 比例（图片类用）
  image?: File | null       // 单图参考（图片类用，可选）
  // 视频类参数
  duration?: number         // 视频时长（秒）
  style?: string            // 视频风格
  videoImage?: File | null  // 视频参考图（可选）
}

/**
 * 智能创意按钮统一入口。
 * - taskType 为 video / video_shots → 调 /api/enhance-video-prompt（中文视频 prompt）
 * - 其他图片类 → 调 /api/enhance-prompt（英文图片 prompt）
 * 返回 { loading, enhance }；enhance 返回 prompt 字符串，失败弹错并返回空串。
 */
export function useEnhancePrompt() {
  const loading = ref(false)

  async function enhance(params: EnhanceParams): Promise<string> {
    loading.value = true
    try {
      if (params.taskType === 'video' || params.taskType === 'video_shots') {
        const desc = (params.userText || '').trim()
        if (!desc) {
          ElMessage.warning('请先简单描述视频方向，再点智能创意')
          return ''
        }
        const resp = await enhanceVideoPrompt(
          desc,
          params.duration ?? 5,
          params.style,
          params.videoImage ?? undefined,
        )
        return resp.prompt
      }

      // 图片类
      const resp = await enhanceImagePrompt(
        params.userText || '',
        params.taskType,
        params.aspectRatio,
        params.image ?? undefined,
      )
      return resp.text
    } catch (e) {
      ElMessage.error(getErrorMessage(e, '智能创意失败，请稍后重试'))
      return ''
    } finally {
      loading.value = false
    }
  }

  return { loading, enhance }
}
