# JWT 鉴权工具 + 密码哈希
import os
import logging
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from jose import jwt, JWTError
import bcrypt

logger = logging.getLogger(__name__)

# JWT 密钥校验：生产强制配置随机密钥，禁止使用默认值/弱密钥
_JWT_SECRET_DEFAULT = "ai-zw-jwt-secret-change-in-production"


@lru_cache(maxsize=1)
def _resolve_jwt_secret() -> str:
    """懒加载读取并校验 JWT_SECRET（首次调用时执行，避开 import 顺序问题）"""
    secret = os.environ.get("JWT_SECRET", "").strip()
    if not secret:
        # 开发兜底：未配置时生成临时随机密钥并告警（不中断本地开发）
        secret = secrets.token_urlsafe(48)
        logger.warning(
            "⚠️ JWT_SECRET 未配置，已生成临时密钥（重启后所有 token 失效）。"
            "生产环境必须在 .env 设置长度≥32 的固定随机密钥！"
        )
    elif secret == _JWT_SECRET_DEFAULT:
        raise RuntimeError(
            "JWT_SECRET 不能使用默认值！请在 .env 设置长度≥32 的随机密钥"
        )
    elif len(secret) < 32:
        raise RuntimeError(
            f"JWT_SECRET 长度需≥32（当前 {len(secret)}）。请设置足够长的随机密钥。"
        )
    return secret


JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    """密码哈希"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """校验密码"""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int, username: str, role: str) -> str:
    """生成 JWT token"""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, _resolve_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解码 JWT token，失败返回 None"""
    try:
        return jwt.decode(token, _resolve_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
