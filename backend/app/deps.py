# FastAPI 依赖注入 - JWT 鉴权 + 角色校验
import logging

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth import decode_token
from app.database import get_db

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """从 JWT token 提取当前用户信息"""
    # health/login 等公开路径跳过
    if request.url.path in ("/api/health", "/api/auth/login"):
        return {"id": 0, "username": "anonymous", "role": "anonymous"}

    if not credentials:
        raise HTTPException(401, "未登录，请先登录")

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "登录已过期，请重新登录")

    user_id = int(payload["sub"])
    username = payload["username"]
    role = payload["role"]

    return {
        "id": user_id,
        "username": username,
        "role": role,
    }


async def require_admin(current_user=Depends(get_current_user)) -> dict:
    """要求管理员角色"""
    if current_user["role"] != "admin":
        raise HTTPException(403, "需要管理员权限")
    return current_user
