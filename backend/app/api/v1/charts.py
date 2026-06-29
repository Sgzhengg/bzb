"""
图表可视化 API 接口

端点:
  GET  /api/v1/charts/{chart_type}   获取图表 HTML/JSON 数据
  GET  /api/v1/charts/types          列出可用图表类型
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/charts", tags=["图表可视化"])


# ============================================================
# 可用图表类型
# ============================================================

CHART_TYPES = {
    "monthly_trend": {
        "name": "月度中标趋势",
        "description": "近12个月中标金额和数量趋势",
        "format": "html",
    },
    "category_distribution": {
        "name": "项目赛道分布",
        "description": "各赛道项目数量和金额分布",
        "format": "html",
    },
    "city_comparison": {
        "name": "地市对比",
        "description": "21地市项目数量和金额对比",
        "format": "json",
    },
    "budget_vs_award": {
        "name": "预算中标对比",
        "description": "预算与中标金额散点对比",
        "format": "html",
    },
    "purchaser_ranking": {
        "name": "采购方排名",
        "description": "按中标金额/数量排名",
        "format": "json",
    },
    "competition_heatmap": {
        "name": "竞争矩阵",
        "description": "供应商 x 采购方 竞争关系矩阵",
        "format": "json",
    },
}


@router.get("/types", summary="列出可用图表类型")
async def list_chart_types():
    """返回所有可用的图表类型及其描述。"""
    return {"types": CHART_TYPES}


# ============================================================
# JSON 图表数据（供前端 Antd Charts 消费）
# ============================================================

@router.get("/json/{chart_type}", summary="获取 JSON 格式图表数据")
async def get_chart_json(
    chart_type: str,
    months: int = Query(12, ge=1, le=36, description="回溯月数"),
    top_n: int = Query(10, ge=1, le=50, description="Top N"),
    db: AsyncSession = Depends(get_db),
):
    """
    返回 JSON 格式图表数据，供前端 Antd Charts 直接使用。
    """
    try:
        if chart_type == "monthly_trend":
            data = await _get_monthly_trend(db, months)
            return {"type": "line", "data": data}

        elif chart_type == "city_comparison":
            data = await _get_city_comparison(db)
            return {"type": "bar", "data": data}

        elif chart_type == "purchaser_ranking":
            data = await _get_purchaser_ranking(db, top_n)
            return {"type": "bar", "data": data}

        elif chart_type == "competition_heatmap":
            data = await _get_competition_heatmap(db, top_n)
            return {"type": "heatmap", "data": data}

        elif chart_type == "category_distribution":
            data = await _get_category_distribution(db)
            return {"type": "pie", "data": data}

        else:
            raise HTTPException(
                status_code=404,
                detail=f"未知图表类型: {chart_type}。可用: {list(CHART_TYPES.keys())}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成图表失败 [{chart_type}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# HTML 图表（Plotly 交互式）
# ============================================================

@router.get("/html/{chart_type}", summary="获取 Plotly 交互式 HTML 图表")
async def get_chart_html(
    chart_type: str,
    months: int = Query(12, ge=1, le=36),
    top_n: int = Query(10, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """
    返回 Plotly 交互式 HTML 图表，可直接嵌入 iframe。
    """
    try:
        from app.services.chart_service import ChartService
        chart = ChartService()

        if chart_type == "monthly_trend":
            data = await _get_monthly_trend(db, months)
            html = chart.monthly_trend(data, "月度中标趋势")
            return HTMLResponse(content=html)

        elif chart_type == "category_distribution":
            data = await _get_category_distribution(db)
            html = chart.category_distribution(
                data, "项目赛道分布", chart_type="doughnut"
            )
            return HTMLResponse(content=html)

        elif chart_type == "budget_vs_award":
            data = await _get_budget_vs_award(db, top_n)
            html = chart.budget_vs_award_scatter(data, "预算 vs 中标金额")
            return HTMLResponse(content=html)

        else:
            raise HTTPException(
                status_code=404,
                detail=f"HTML 图表类型不支持: {chart_type}。"
                       f"支持的 HTML 类型: monthly_trend, category_distribution, budget_vs_award",
            )

    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Plotly 未安装: {e}。请执行: pip install plotly pandas",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成 HTML 图表失败 [{chart_type}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 数据查询辅助函数
# ============================================================

async def _get_monthly_trend(db: AsyncSession, months: int) -> list:
    """查询月度中标趋势数据。"""
    from datetime import date, timedelta
    start_date = date.today() - timedelta(days=months * 31)

    result = await db.execute(
        text("""
            SELECT
                TO_CHAR(announce_date, 'YYYY-MM') AS month,
                COUNT(*) AS count,
                COALESCE(SUM(budget), 0) AS total_amount
            FROM announcements
            WHERE announce_date >= :start
            GROUP BY month
            ORDER BY month
        """),
        {"start": start_date},
    )
    rows = result.fetchall()
    return [
        {"month": r[0], "count": r[1], "total_amount": round(float(r[2] or 0), 1)}
        for r in rows
    ]


async def _get_city_comparison(db: AsyncSession) -> list:
    """查询地市对比数据。"""
    result = await db.execute(
        text("""
            SELECT
                COALESCE(purchaser_level, '未知') AS city,
                COUNT(*) AS count,
                COALESCE(SUM(budget), 0) AS total_amount
            FROM announcements
            GROUP BY purchaser_level
            ORDER BY count DESC
            LIMIT 21
        """)
    )
    rows = result.fetchall()
    return [
        {"city": r[0], "count": r[1], "total_amount": round(float(r[2] or 0), 1)}
        for r in rows
    ]


async def _get_purchaser_ranking(db: AsyncSession, top_n: int) -> list:
    """查询采购方排名。"""
    result = await db.execute(
        text("""
            SELECT
                COALESCE(purchaser_name, '未知') AS name,
                COUNT(*) AS count,
                COALESCE(SUM(budget), 0) AS total_amount
            FROM announcements
            GROUP BY purchaser_name
            ORDER BY count DESC
            LIMIT :limit
        """),
        {"limit": top_n},
    )
    rows = result.fetchall()
    return [
        {"name": r[0], "count": r[1], "total_amount": round(float(r[2] or 0), 1)}
        for r in rows
    ]


async def _get_category_distribution(db: AsyncSession) -> list:
    """查询项目赛道分布。"""
    result = await db.execute(
        text("""
            SELECT
                COALESCE(project_category, '未分类') AS category,
                COUNT(*) AS count,
                COALESCE(SUM(budget), 0) AS total_amount
            FROM announcements
            GROUP BY project_category
            ORDER BY count DESC
            LIMIT 10
        """)
    )
    rows = result.fetchall()
    return [
        {"category": r[0], "count": r[1], "total_amount": round(float(r[2] or 0), 1)}
        for r in rows
    ]


async def _get_budget_vs_award(db: AsyncSession, top_n: int) -> list:
    """查询预算中标对比数据。"""
    result = await db.execute(
        text("""
            SELECT
                COALESCE(purchaser_name, '未知') AS purchaser,
                AVG(budget) AS avg_budget,
                AVG(budget) * 0.95 AS avg_award,
                COUNT(*) AS count
            FROM announcements
            WHERE budget IS NOT NULL AND budget > 0
            GROUP BY purchaser_name
            ORDER BY count DESC
            LIMIT :limit
        """),
        {"limit": top_n},
    )
    rows = result.fetchall()
    return [
        {
            "purchaser": r[0],
            "avg_budget": round(float(r[1] or 0), 1),
            "avg_award": round(float(r[2] or 0), 1),
            "count": r[3],
        }
        for r in rows
    ]


async def _get_competition_heatmap(db: AsyncSession, top_n: int) -> list:
    """查询竞争矩阵数据。"""
    result = await db.execute(
        text("""
            SELECT
                COALESCE(purchaser_name, '未知') AS purchaser,
                COALESCE(winner_name, '未知') AS winner,
                COUNT(*) AS win_count
            FROM announcements
            WHERE winner_name IS NOT NULL
            GROUP BY purchaser_name, winner_name
            ORDER BY win_count DESC
            LIMIT :limit
        """),
        {"limit": top_n * top_n},
    )
    rows = result.fetchall()
    return [
        {"purchaser": r[0], "winner": r[1], "win_count": r[2]}
        for r in rows
    ]
