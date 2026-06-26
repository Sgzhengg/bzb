"""
客情管理 — Pydantic 请求/响应模型
"""

from datetime import date, datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ============================================================
# 枚举
# ============================================================

class RatingEnum(str, Enum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ContactMethodEnum(str, Enum):
    MEETING = "面谈"
    PHONE = "电话"
    WECHAT = "微信"
    EMAIL = "邮件"
    DINNER = "饭局"


# ============================================================
# 排序常量
# ============================================================

RATING_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}


# ============================================================
# 请求模型
# ============================================================

class RelationCreate(BaseModel):
    """创建客情记录"""

    purchaser_id: int = Field(..., gt=0, description="采购方ID")
    contact_name: str = Field(..., min_length=1, max_length=100, description="联系人姓名")
    title: Optional[str] = Field(None, max_length=100, description="职位")
    phone: Optional[str] = Field(None, max_length=30, description="电话")
    email: Optional[str] = Field(None, max_length=200, description="邮箱")
    last_contact_date: Optional[date] = Field(None, description="最近接触日期")
    contact_method: Optional[ContactMethodEnum] = Field(None, description="接触方式")
    contact_summary: Optional[str] = Field(None, description="接触内容摘要")
    rating: RatingEnum = Field(default=RatingEnum.C, description="关系评级 S/A/B/C/D")
    next_followup_date: Optional[date] = Field(None, description="下次跟进提醒日期")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.strip():
            return None
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v


class RelationUpdate(BaseModel):
    """更新客情记录（所有字段可选）"""

    purchaser_id: Optional[int] = Field(None, gt=0, description="采购方ID")
    contact_name: Optional[str] = Field(None, min_length=1, max_length=100, description="联系人姓名")
    title: Optional[str] = Field(None, max_length=100, description="职位")
    phone: Optional[str] = Field(None, max_length=30, description="电话")
    email: Optional[str] = Field(None, max_length=200, description="邮箱")
    last_contact_date: Optional[date] = Field(None, description="最近接触日期")
    contact_method: Optional[ContactMethodEnum] = Field(None, description="接触方式")
    contact_summary: Optional[str] = Field(None, description="接触内容摘要")
    rating: Optional[RatingEnum] = Field(None, description="关系评级 S/A/B/C/D")
    next_followup_date: Optional[date] = Field(None, description="下次跟进提醒日期")


# ============================================================
# 响应模型
# ============================================================

class RelationResponse(BaseModel):
    """客情记录响应"""

    id: int
    purchaser_id: int
    contact_name: str
    title: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    last_contact_date: Optional[date] = None
    contact_method: Optional[str] = None
    contact_summary: Optional[str] = None
    rating: str
    next_followup_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RelationListResponse(BaseModel):
    """客情记录列表响应"""

    total: int
    items: List[RelationResponse]


class ReminderResponse(BaseModel):
    """跟进提醒响应"""

    id: int
    purchaser_id: int
    contact_name: str
    rating: str
    next_followup_date: date
    last_contact_date: Optional[date] = None
    title: Optional[str] = None
    phone: Optional[str] = None


class MessageResponse(BaseModel):
    """通用消息响应"""

    message: str
    detail: Optional[str] = None


# ============================================================
# 查询参数模型
# ============================================================

class RelationFilterParams(BaseModel):
    """客情列表筛选参数"""

    purchaser_id: Optional[int] = Field(None, description="按采购方ID筛选")
    rating: Optional[RatingEnum] = Field(None, description="按评级筛选")
    skip: int = Field(0, ge=0, description="跳过记录数")
    limit: int = Field(20, ge=1, le=100, description="返回记录数上限")
