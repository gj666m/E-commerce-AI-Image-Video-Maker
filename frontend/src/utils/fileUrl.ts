// 续10 安全 Review P0-R2：替代裸 /video-files /model-files /gen-files 静态路径
// 后端改为 /api/file/{kind}/{path}?token=xxx 鉴权访问，<img>/<video>/fetch 统一走此工具。

const TOKEN_KEY = 'ai-zw-token'

function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

/**
 * 把旧的 /video-files/... /model-files/... /gen-files/... 路径
 * 转换为新的鉴权路径 /api/file/{kind}/{path}?token=xxx
 * 已是 /api/file/... 但缺 token 的也补上（如 asset-thumbs）。
 * 其他 URL（data:, http://）原样返回。
 */
export function fileUrl(rawUrl: string | null | undefined): string {
  if (!rawUrl) return ''
  // 旧前缀 → 转 /api/file/{kind}/...
  const prefixes = ['/video-files/', '/model-files/', '/gen-files/'] as const
  for (const p of prefixes) {
    if (rawUrl.startsWith(p)) {
      const kind = p.slice(1, -1) // 去掉首尾的 /
      const inner = rawUrl.slice(p.length)
      const token = getToken()
      return `/api/file/${kind}/${inner}?token=${encodeURIComponent(token)}`
    }
  }
  // 已是 /api/file/... 但没带 token，补上（asset-thumbs 等新 kind 后端直返此格式）
  if (rawUrl.startsWith('/api/file/') && !rawUrl.includes('token=')) {
    const token = getToken()
    const sep = rawUrl.includes('?') ? '&' : '?'
    return `${rawUrl}${sep}token=${encodeURIComponent(token)}`
  }
  return rawUrl
}
