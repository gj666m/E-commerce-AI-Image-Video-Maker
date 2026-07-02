// 续10 安全 Review P0-R2：替代裸 /video-files /model-files /gen-files 静态路径
// 后端改为 /api/file/{kind}/{path}?token=xxx 鉴权访问，<img>/<video>/fetch 统一走此工具。

const TOKEN_KEY = 'access_token'

function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

/**
 * 把旧的 /video-files/... /model-files/... /gen-files/... 路径
 * 转换为新的鉴权路径 /api/file/{kind}/{path}?token=xxx
 * 其他 URL（data:, http://, /api/...）原样返回。
 */
export function fileUrl(rawUrl: string | null | undefined): string {
  if (!rawUrl) return ''
  const prefixes = ['/video-files/', '/model-files/', '/gen-files/'] as const
  for (const p of prefixes) {
    if (rawUrl.startsWith(p)) {
      const kind = p.slice(1, -1) // 去掉首尾的 /
      const inner = rawUrl.slice(p.length)
      const token = getToken()
      return `/api/file/${kind}/${inner}?token=${encodeURIComponent(token)}`
    }
  }
  return rawUrl
}
