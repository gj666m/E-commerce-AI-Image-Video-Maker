# API易余额查询接口 - 全员可见，5 分钟缓存
import asyncio
import logging
import time

from fastapi import APIRouter, Depends

from app.config import settings
from app.deps import get_current_user
from app.services.http_client import get_http_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/balance", tags=["balance"])

# API易用户自助接口（注意：Auth 用直接 token，不是 Bearer）
_APIYI_USER_SELF = "https://api.apiyi.com/api/user/self"
_QUOTA_TO_USD = 500000  # 1 USD = 500000 quota
_CACHE_TTL = 300  # 5 分钟

# 模块级缓存
_cache_lock = asyncio.Lock()
_cache: dict | None = None  # {"data": {...}, "fetched_at": ts}


async def _fetch_balance() -> dict:
    """调 API易 /api/user/self 获取 quota/used_quota，换算为 USD"""
    token = settings.apiyi_balance_token
    if not token:
        return {"available": False, "message": "未配置 API易 余额令牌"}

    client = get_http_client()
    try:
        resp = await client.get(
            _APIYI_USER_SELF,
            headers={
                "Authorization": token,  # 直接 token，不是 Bearer
                "Accept": "application/json",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning(f"API易余额查询失败 status={resp.status_code} body={resp.text[:200]}")
            return {"available": False, "message": f"API易返回 {resp.status_code}"}

        data = resp.json()
        # API易返回形如 {"success": true, "data": {...}} 或直接对象
        payload = data.get("data", data) if isinstance(data, dict) else {}
        quota = float(payload.get("quota", 0) or 0)
        used_quota = float(payload.get("used_quota", 0) or 0)
        request_count = int(payload.get("request_count", 0) or 0)

        return {
            "available": True,
            "quota_usd": round(quota / _QUOTA_TO_USD, 2),
            "used_usd": round(used_quota / _QUOTA_TO_USD, 2),
            "request_count": request_count,
        }
    except Exception as e:
        logger.warning(f"API易余额查询异常: {e}")
        return {"available": False, "message": f"查询失败: {e}"}


@router.get("")
async def get_balance(current_user=Depends(get_current_user)):
    """获取 API易 剩余额度（全员可见，5 分钟缓存）"""
    global _cache
    now = time.time()

    async with _cache_lock:
        if _cache and now - _cache["fetched_at"] < _CACHE_TTL:
            return {"success": True, **_cache["data"]}

        data = await _fetch_balance()
        _cache = {"data": data, "fetched_at": now}

    return {"success": True, **data}
