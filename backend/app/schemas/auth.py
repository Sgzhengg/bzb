"""
认证相关 Pydantic Schema
"""
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=4, max_length=100, description="密码")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    id: int
    username: str
    display_name: str = ""
    is_admin: bool = False


class UserInfo(BaseModel):
    """当前用户信息"""
    id: int
    username: str
    display_name: str
    email: str = ""
    is_admin: bool = False

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=4, max_length=100)
