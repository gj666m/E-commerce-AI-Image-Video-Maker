# JWT 鉴权工具 + 密码哈希
import os
import logging
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
import bcrypt

logger = logging.getLogger(__name__)

# JWT 密钥（从环境变量读取，默认随机生成）
_JWT_SECRET = os.environ.get("JWT_SECRET", "ai-zw-jwt-secret-change-in-production")
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
    return jwt.encode(payload, _JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解码 JWT token，失败返回 None"""
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
