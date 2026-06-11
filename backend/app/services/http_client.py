# 全局 httpx 连接池 - 所有 Provider 共享，减少连接开销
import httpx

# 全局共享客户端（惰性创建）
_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """获取全局共享 httpx 客户端

    默认超时 120s，各 Provider 可通过 per-request timeout 覆盖。
    连接池限制：最多 100 连接，单 Host 最多 20 连接。
    """
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=120,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    return _client


async def close_http_client():
    """关闭全局客户端（应用关闭时调用）"""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
    _client = None
