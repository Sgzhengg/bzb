"""
用户偏好 API 接口

端点:
  GET  /api/v1/preferences       获取当前偏好
  PUT  /api/v1/preferences       更新偏好
"""

import json
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user_preference import UserPreference

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preferences", tags=["用户偏好"])


# ============================================================
# 请求/响应模型
# ============================================================

class PreferenceUpdate(BaseModel):
    """偏好更新请求"""
    focus_description: Optional[str] = Field(
        None, description="关注方向描述（自然语言）"
    )
    preferred_categories: Optional[List[str]] = Field(
        None, description="偏好赛道列表"
    )
    min_budget: Optional[float] = Field(
        None, ge=0, description="最低预算（万元）"
    )
    min_score: Optional[float] = Field(
        None, ge=0, le=100, description="最低机会评分"
    )
    llm_enabled: Optional[str] = Field(None, description="LLM 是否启用")
    llm_api_key: Optional[str] = Field(None, description="LLM API Key")
    llm_model: Optional[str] = Field(None, description="LLM 模型")
    llm_base_url: Optional[str] = Field(None, description="LLM API 地址")


# ============================================================
# API 端点
# ============================================================

@router.get("", summary="获取用户偏好")
async def get_preferences(db: AsyncSession = Depends(get_db)):
    """获取当前用户的关注偏好设置。"""
    result = await db.execute(
        select(UserPreference).where(UserPreference.id == 1)
    )
    pref = result.scalar_one_or_none()

    if pref is None:
        # 首次访问，返回默认值
        return {
            "id": 1,
            "focus_description": "",
            "preferred_categories": [],
            "min_budget": 0,
            "min_score": 0,
            "updated_at": "",
        }

    return pref.to_dict()


@router.put("", summary="更新用户偏好")
async def update_preferences(
    body: PreferenceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新用户偏好设置。

    传入的字段会覆盖，未传入的字段保持原值。
    """
    result = await db.execute(
        select(UserPreference).where(UserPreference.id == 1)
    )
    pref = result.scalar_one_or_none()

    if pref is None:
        # 首次创建
        pref = UserPreference(id=1)
        db.add(pref)

    if body.focus_description is not None:
        pref.focus_description = body.focus_description
    if body.preferred_categories is not None:
        pref.preferred_categories = UserPreference.build_categories(
            body.preferred_categories
        )
    if body.min_budget is not None:
        pref.min_budget = body.min_budget
    if body.min_score is not None:
        pref.min_score = body.min_score
    if body.llm_enabled is not None:
        pref.llm_enabled = body.llm_enabled
    if body.llm_api_key is not None:
        pref.llm_api_key = body.llm_api_key
    if body.llm_model is not None:
        pref.llm_model = body.llm_model
    if body.llm_base_url is not None:
        pref.llm_base_url = body.llm_base_url

    await db.commit()
    await db.refresh(pref)

    logger.info(
        f"偏好已更新: 赛道={pref._parse_categories()}, "
        f"预算≥{pref.min_budget}万, 评分≥{pref.min_score}"
    )

    return pref.to_dict()


@router.delete("", summary="重置用户偏好")
async def reset_preferences(db: AsyncSession = Depends(get_db)):
    """重置偏好为默认值。"""
    result = await db.execute(
        select(UserPreference).where(UserPreference.id == 1)
    )
    pref = result.scalar_one_or_none()

    if pref:
        pref.focus_description = ""
        pref.preferred_categories = "[]"
        pref.min_budget = 0
        pref.min_score = 0
        await db.commit()

    return {"status": "ok", "message": "偏好已重置为默认值"}


# ============================================================
# 辅助函数（供其他模块调用）
# ============================================================

async def get_user_preferences(db: AsyncSession) -> dict:
    """获取用户偏好（供内部模块调用，不依赖 HTTP 请求）。"""
    result = await db.execute(
        select(UserPreference).where(UserPreference.id == 1)
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        return {
            "preferred_categories": [],
            "min_budget": 0,
            "min_score": 0,
        }
    return pref.to_dict()


def parse_focus_keywords(description: str) -> dict:
    """
    从用户关注描述中提取关键词和偏好。

    支持模糊匹配：用户输入"品牌"能匹配"品牌策略类"，
    输入"广告"能匹配所有广告赛道。

    纯规则解析，不依赖 LLM。

    Args:
        description: 用户输入的自然语言描述

    Returns:
        {"keywords": [...], "min_budget": float|None, "categories": [...]}
    """
    import re

    result = {
        "keywords": [],
        "min_budget": None,
        "categories": [],
    }

    if not description:
        return result

    # ── 提取预算数字 ──
    budget_patterns = [
        r"预算\s*(\d+)\s*万",
        r"(\d+)\s*万\s*(?:以上|元|预算|级别)",
        r"不低于\s*(\d+)\s*万",
        r"(\d+)万",
    ]
    for pattern in budget_patterns:
        match = re.search(pattern, description)
        if match:
            try:
                val = float(match.group(1))
                if 1 <= val <= 10000:  # 合理范围
                    result["min_budget"] = val
            except ValueError:
                pass
            break

    # ── 赛道匹配（支持多级关键词：精确 > 短词 > 模糊） ──
    # 三层匹配策略：
    #   L1: 精确匹配（如"品牌策略" → 品牌策略类）
    #   L2: 短词/别名匹配（如"品牌" → 品牌策略类，"广告" → 全部赛道）
    #   L3: 语义模糊匹配（如"营销推广" → 活动执行类/内容制作类）

    category_rules = [
        {
            "category": "品牌策略类",
            "exact": ["品牌策略", "品牌规划", "品牌定位"],
            "short": ["品牌", "策略", "规划", "定位"],
            "fuzzy": ["战略", "咨询", "调研"],
        },
        {
            "category": "创意设计类",
            "exact": ["创意设计", "视觉设计", "VI设计"],
            "short": ["创意", "设计", "视觉", "VI", "海报"],
            "fuzzy": ["美术", "平面", "美工"],
        },
        {
            "category": "媒介投放类",
            "exact": ["媒介投放", "广告投放", "KOL投放"],
            "short": ["投放", "媒介", "KOL", "代理", "采买"],
            "fuzzy": ["流量", "曝光", "媒体"],
        },
        {
            "category": "活动会展类",
            "exact": ["活动执行", "路演活动", "展会活动"],
            "short": ["活动", "路演", "展会", "发布会", "工会", "文体"],
            "fuzzy": ["线下", "促销", "体验"],
        },
        {
            "category": "渠道营销类",
            "exact": ["渠道营销", "网格促销", "门店宣传"],
            "short": ["渠道", "网格", "地推", "门店", "促销"],
            "fuzzy": ["终端", "网点", "摆摊"],
        },
        {
            "category": "内容制作类",
            "exact": ["内容制作", "视频制作", "物料制作"],
            "short": ["制作", "拍摄", "物料", "H5", "脚本", "视频", "短视频"],
            "fuzzy": ["剪辑", "后期", "动画"],
        },
        {
            "category": "政企传播类",
            "exact": ["党群宣传", "党建学习", "集团客户"],
            "short": ["党群", "党建", "宣传", "学习", "政企"],
            "fuzzy": ["企业", "形象", "内部"],
        },
        {
            "category": "新媒体运营类",
            "exact": ["新媒体运营", "公众号运营", "视频号运营"],
            "short": ["新媒体", "公众号", "视频号", "直播", "代运营", "运营"],
            "fuzzy": ["社媒", "社交", "自媒体"],
        },
    ]

    # "广告"是通用词，匹配所有赛道
    ad_keywords = ["广告", "宣传", "招标", "采购"]

    is_general_ad = any(kw in description for kw in ad_keywords)

    for rule in category_rules:
        matched = False

        # L1: 精确匹配
        for kw in rule["exact"]:
            if kw in description:
                matched = True
                result["keywords"].append(kw)
                break

        # L2: 短词匹配
        if not matched:
            for kw in rule["short"]:
                if kw in description:
                    matched = True
                    result["keywords"].append(kw)
                    break

        # L3: 模糊匹配
        if not matched:
            for kw in rule["fuzzy"]:
                if kw in description:
                    matched = True
                    result["keywords"].append(kw)
                    break

        if matched:
            result["categories"].append(rule["category"])

    # 如果用户只写了"广告/宣传/招标/采购"等通用词，匹配所有赛道
    if is_general_ad and not result["categories"]:
        result["categories"] = [r["category"] for r in category_rules]

    # 去重
    result["categories"] = list(dict.fromkeys(result["categories"]))
    result["keywords"] = list(dict.fromkeys(result["keywords"]))

    return result
