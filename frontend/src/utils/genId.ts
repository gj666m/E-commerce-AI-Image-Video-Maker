/**
 * 生成唯一 id（兼容非 secure context）
 *
 * crypto.randomUUID() 仅在 secure context（HTTPS 或 localhost）下可用。
 * 服务器通过 HTTP 部署时（如 http://127.0.0.1:6068）该方法不存在，
 * 会导致 Vue setup 抛异常、整个页面白屏。
 *
 * 本函数优先用原生 crypto.randomUUID()，否则降级到时间戳 + 随机数组合。
 */

export function genId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  // 降级：时间戳(36) + 随机后缀，碰撞概率足够低（同毫秒并发 < 1/10^12）
  return Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10)
}
