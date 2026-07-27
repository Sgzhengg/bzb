"""
安全模块 — JWT 认证与密码哈希
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import jwt

from app.core.config import settings


# JWT 配置
JWT_SECRET_KEY: str = getattr(settings, "JWT_SECRET_KEY", None) or os.environ.get(
    "BZB_JWT_SECRET_KEY",
    secrets.token_urlsafe(32),
)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    使用 PBKDF2-SHA256 哈希密码。
    返回 (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return dk.hex(), salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """验证密码。"""
    computed, _ = hash_password(password, salt)
    return hmac.compare_digest(computed, hashed)


def create_access_token(
    user_id: int,
    username: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """创建 JWT access token。"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + expires_delta,
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """解码并验证 JWT token。"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None
