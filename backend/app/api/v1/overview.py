"""
今日概览 API

端点:
  GET /api/v1/overview/today             今日概览统计
  GET /api/v1/overview/province-stats    各省份统计（V2 新增）
  GET /api/v1/overview/city-stats        重点城市排名（V2 新增）
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.announcement import Announcement

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/overview", tags=["概览"])


@router.get("/today", summary="今日概览")
async def today_overview(db: AsyncSession = Depends(get_db)):
    """返回今日新增数和有预算项目数。"""
    today = date.today()

    # 今日新增
    new_q = select(func.count()).select_from(Announcement).where(
        Announcement.announce_date == today
    )
    new_today = (await db.execute(new_q)).scalar() or 0

    # 有预算的项目（预算>0）
    budget_q = select(func.count()).select_from(Announcement).where(
        Announcement.budget > 0
    )
    high_opp = (await db.execute(budget_q)).scalar() or 0

    return {
        "new_today": new_today,
        "high_opp": high_opp,
    }


@router.get("/province-stats", summary="各省份统计")
async def province_stats(
    limit: int = Query(10, ge=1, le=34, description="返回前N个省份"),
    db: AsyncSession = Depends(get_db),
):
    """
    各省份招标公告数量与预算总额统计（V2 多省扩展）。

    按公告数量降序排列，返回前 N 个省份。
    """
    q = (
        select(
            Announcement.province,
            func.count(Announcement.id).label("count"),
            func.coalesce(func.sum(Announcement.budget), 0).label("total_budget"),
        )
        .where(Announcement.province != "")
        .group_by(Announcement.province)
        .order_by(func.count(Announcement.id).desc())
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()

    return {
        "provinces": [
            {
                "province": row.province,
                "count": row.count,
                "total_budget": float(row.total_budget),
            }
            for row in rows
        ]
    }


@router.get("/city-stats", summary="重点城市排名")
async def city_stats(
    limit: int = Query(20, ge=1, le=100, description="返回前N个城市"),
    province: str = Query(None, description="筛选特定省份"),
    db: AsyncSession = Depends(get_db),
):
    """
    城市级别招标公告数量排名（V2 多省扩展）。

    可选项：按省份筛选，只看特定省份内城市排名。
    """
    conditions = [Announcement.city != ""]
    if province:
        conditions.append(Announcement.province == province)

    q = (
        select(
            Announcement.province,
            Announcement.city,
            func.count(Announcement.id).label("count"),
            func.coalesce(func.sum(Announcement.budget), 0).label("total_budget"),
        )
        .where(and_(*conditions))
        .group_by(Announcement.province, Announcement.city)
        .order_by(func.count(Announcement.id).desc())
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()

    return {
        "cities": [
            {
                "province": row.province,
                "city": row.city,
                "count": row.count,
                "total_budget": float(row.total_budget),
            }
            for row in rows
        ]
    }
