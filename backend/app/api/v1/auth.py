"""
认证 API — 登录、登出、用户信息
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_user
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserInfo,
    ChangePasswordRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """使用用户名和密码登录，返回 JWT access token。"""
    result = await db.execute(
        select(User).where(User.username == req.username)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(req.password, user.password_hash, user.password_salt):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    token = create_access_token(user.id, user.username)
    logger.info(f"用户登录: {user.username}")

    return TokenResponse(
        access_token=token,
        id=user.id,
        username=user.username,
        display_name=user.display_name or user.username,
        is_admin=user.is_admin,
    )


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(require_user)):
    """获取当前登录用户的信息。"""
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name or current_user.username,
        email=current_user.email or "",
        is_admin=current_user.is_admin,
    )


@router.post("/change-password", summary="修改密码")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户的密码。"""
    if not verify_password(req.old_password, current_user.password_hash, current_user.password_salt):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码不正确",
        )

    new_hash, new_salt = hash_password(req.new_password)
    current_user.password_hash = new_hash
    current_user.password_salt = new_salt
    await db.commit()

    return {"message": "密码修改成功"}


@router.post("/logout", summary="退出登录")
async def logout():
    """退出登录（JWT 无状态，客户端丢弃 token 即可）。"""
    return {"message": "已退出登录"}
