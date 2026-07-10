"""
今日概览 API

端点:
  GET /api/v1/overview/today   今日概览统计
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
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
