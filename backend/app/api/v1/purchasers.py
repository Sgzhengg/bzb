"""
采购方 API 接口

端点:
  GET  /api/v1/purchasers             采购方列表
  GET  /api/v1/purchasers/compare      地市对比看板
  GET  /api/v1/purchasers/{id}/profile 采购方画像详情
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.client_relation import Purchaser
from app.services.purchaser_profiler import (
    analyze_purchaser_profile,
    batch_analyze_purchasers,
)

router = APIRouter(prefix="/purchasers", tags=["采购方"])


@router.get("", summary="获取采购方列表")
async def list_purchasers(
    level: Optional[str] = Query(None, description="按层级筛选: 省公司/地市公司"),
    db: AsyncSession = Depends(get_db),
):
    """获取所有采购方的基本信息列表。"""
    query = select(Purchaser)
    if level:
        query = query.where(Purchaser.level == level)
    query = query.order_by(Purchaser.id)

    result = await db.execute(query)
    purchasers = result.scalars().all()

    return {
        "total": len(purchasers),
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "level": p.level,
                "region": p.region,
            }
            for p in purchasers
        ],
    }


@router.get("/compare", summary="地市对比看板")
async def compare_cities(
    db: AsyncSession = Depends(get_db),
):
    """
    获取21个地市的对比数据，包含项目数、SME占比、机会评级等。

    用于地市对比看板页面的数据展示。
    """
    from sqlalchemy import text

    # 查询所有地市分公司的采购方
    city_result = await db.execute(
        select(Purchaser).where(Purchaser.level == "地市公司").order_by(Purchaser.id)
    )
    city_purchasers = city_result.scalars().all()

    # 按采购方聚合历史中标数据
    compare_rows = []
    for p in city_purchasers:
        # 查询该采购方的历史中标记录
        awards_result = await db.execute(
            text("""
                SELECT
                    COUNT(*) AS total_count,
                    COALESCE(SUM(CASE WHEN winner_type = '头部常客' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 0) AS head_ratio,
                    COALESCE(SUM(CASE WHEN winner_type IN ('中小公司', '新进入者') THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 0) AS sme_ratio,
                    COALESCE(AVG(CASE WHEN is_continuous THEN 1.0 ELSE 0.0 END) * 100, 0) AS renewal_rate,
                    COALESCE(SUM(CASE WHEN bid_open_date >= CURRENT_DATE - INTERVAL '1 year' THEN 1 ELSE 0 END), 0) AS recent_count
                FROM historical_awards
                WHERE purchaser_id = :pid
            """),
            {"pid": p.id},
        )
        row = awards_result.fetchone()
        total = row.total_count or 0
        head_ratio = round(float(row.head_ratio or 0), 1)
        sme_ratio = round(float(row.sme_ratio or 0), 1)
        renewal_rate = round(float(row.renewal_rate or 0), 1)
        recent_count = row.recent_count or 0

        # 机会评级计算
        rating, advice = _calc_city_rating(recent_count, sme_ratio, renewal_rate)

        compare_rows.append({
            "purchaser_id": p.id,
            "city": p.region or p.name,
            "purchaser_name": p.name,
            "recent_project_count": recent_count,
            "total_project_count": total,
            "head_supplier_ratio": head_ratio,
            "incumbent_renewal_rate": renewal_rate,
            "sme_win_rate": sme_ratio,
            "opportunity_rating": rating,
            "advice": advice,
        })

    # 按机会评级排序
    compare_rows.sort(key=lambda x: len(x["opportunity_rating"]), reverse=True)

    return {
        "total_cities": len(compare_rows),
        "items": compare_rows,
    }


def _calc_city_rating(recent_count: int, sme_ratio: float, renewal_rate: float):
    """计算城市机会评级和建议。"""
    stars = 2  # 默认2星

    if recent_count >= 10:
        stars += 1
    if sme_ratio >= 25:
        stars += 1
    if sme_ratio >= 15 and renewal_rate < 50:
        stars += 1
    if renewal_rate < 30:
        stars += 1

    stars = min(stars, 5)

    rating = "★" * stars + "☆" * (5 - stars)

    if stars >= 5:
        advice = "🌟 推荐优先切入：项目多、中小公司活跃、在位者不稳固"
    elif stars >= 4:
        advice = "👍 建议重点关注：竞争环境较好，有突围空间"
    elif stars >= 3:
        advice = "👀 可选择性参与：需评估自身优势匹配度"
    elif stars >= 2:
        advice = "⚠️ 谨慎参与：竞争较为激烈，在位者优势明显"
    else:
        advice = "❌ 不建议投入：项目少且头部垄断严重"

    return rating, advice


@router.get("/{purchaser_id}/profile", summary="获取采购方画像")
async def get_purchaser_profile(
    purchaser_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定采购方的竞争格局分析报告。

    返回数据包括：Top10供应商、HHI集中度、在位者地图、
    SME占比、新进入者数量、破圈案例、机会评级。
    """
    # 查询采购方
    purchaser = await db.get(Purchaser, purchaser_id)
    if not purchaser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"采购方ID {purchaser_id} 不存在",
        )

    # 查询该采购方的历史中标记录
    from app.models.client_relation import ClientRelation
    from app.models.announcement import Announcement

    # 尝试从 historical_awards 表查询
    from sqlalchemy import text
    awards_result = await db.execute(
        text("""
            SELECT * FROM historical_awards
            WHERE purchaser_id = :pid
            ORDER BY bid_open_date DESC
        """),
        {"pid": purchaser_id},
    )
    awards_rows = awards_result.fetchall()
    awards = [dict(row._mapping) for row in awards_rows] if awards_rows else []

    # 生成画像
    profile = analyze_purchaser_profile(
        purchaser_name=purchaser.name,
        purchaser_id=purchaser_id,
        awards=awards,
    )

    return profile.to_dict()
