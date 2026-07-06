"""
历史中标结果 API 接口

端点:
  GET  /api/v1/awards              中标结果列表（筛选/分页）
  GET  /api/v1/awards/{id}         单条详情
  GET  /api/v1/awards/stats        中标统计概览
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.historical_award import HistoricalAward

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/awards", tags=["中标结果"])


@router.get("", summary="获取中标结果列表")
async def list_awards(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    project_category: Optional[str] = Query(None, description="项目类别筛选"),
    winner_type: Optional[str] = Query(None, description="中标方类型"),
    purchaser_id: Optional[int] = Query(None, description="采购方ID"),
    search: Optional[str] = Query(None, description="项目名称/中标方搜索"),
    db: AsyncSession = Depends(get_db),
):
    """获取历史中标结果列表，支持筛选和分页。"""
    conditions = []

    if project_category:
        conditions.append(HistoricalAward.project_category == project_category)
    if winner_type:
        conditions.append(HistoricalAward.winner_type == winner_type)
    if purchaser_id:
        conditions.append(HistoricalAward.purchaser_id == purchaser_id)
    if search:
        conditions.append(
            HistoricalAward.project_name.ilike(f"%{search}%")
            | HistoricalAward.winner_name.ilike(f"%{search}%")
        )

    # 总数
    count_q = select(func.count()).select_from(HistoricalAward)
    if conditions:
        count_q = count_q.where(and_(*conditions))
    total = (await db.execute(count_q)).scalar() or 0

    # 列表
    list_q = (
        select(HistoricalAward)
        .order_by(desc(HistoricalAward.bid_open_date))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if conditions:
        list_q = list_q.where(and_(*conditions))

    result = await db.execute(list_q)
    awards = result.scalars().all()

    items = [
        {
            "id": a.id,
            "project_name": a.project_name,
            "purchaser_id": a.purchaser_id,
            "purchaser_name": a.purchaser.name if a.purchaser else "",
            "winner_name": a.winner_name,
            "winner_type": a.winner_type,
            "bid_amount": float(a.bid_amount) if a.bid_amount else None,
            "budget_amount": float(a.budget_amount) if a.budget_amount else None,
            "discount_rate": float(a.discount_rate) if a.discount_rate else None,
            "project_category": a.project_category,
            "bid_open_date": a.bid_open_date.isoformat() if a.bid_open_date else None,
            "contract_start": a.contract_start.isoformat() if a.contract_start else None,
            "contract_end": a.contract_end.isoformat() if a.contract_end else None,
            "is_continuous": a.is_continuous,
            "continuous_count": a.continuous_count,
            "source_url": a.source_url or "",
        }
        for a in awards
    ]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/stats", summary="中标统计概览")
async def award_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取中标结果统计数据。"""
    # 总数
    total_q = select(func.count()).select_from(HistoricalAward)
    total = (await db.execute(total_q)).scalar() or 0

    # 总金额
    amount_q = select(func.sum(HistoricalAward.bid_amount)).select_from(HistoricalAward)
    total_amount = (await db.execute(amount_q)).scalar() or 0

    # 按中标方类型统计
    type_q = (
        select(
            HistoricalAward.winner_type,
            func.count().label("count"),
        )
        .group_by(HistoricalAward.winner_type)
        .order_by(desc("count"))
    )
    type_result = await db.execute(type_q)
    type_stats = [
        {"type": row.winner_type, "count": row.count}
        for row in type_result.fetchall()
    ]

    # 按项目类别统计
    cat_q = (
        select(
            HistoricalAward.project_category,
            func.count().label("count"),
        )
        .group_by(HistoricalAward.project_category)
        .order_by(desc("count"))
    )
    cat_result = await db.execute(cat_q)
    cat_stats = [
        {"category": row.project_category, "count": row.count}
        for row in cat_result.fetchall()
    ]

    return {
        "total": total,
        "total_amount": round(float(total_amount), 1),
        "winner_types": type_stats,
        "categories": cat_stats,
    }


@router.get("/{award_id}", summary="获取中标结果详情")
async def get_award_detail(
    award_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单条中标结果的详细信息。"""
    award = await db.get(HistoricalAward, award_id)
    if not award:
        raise HTTPException(status_code=404, detail=f"中标记录 {award_id} 不存在")

    return award.to_dict()
