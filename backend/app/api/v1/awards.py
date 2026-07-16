"""
历史中标结果 API 接口

端点:
  GET    /api/v1/awards              中标结果列表（筛选/分页）
  GET    /api/v1/awards/{id}         单条详情
  DELETE /api/v1/awards/{id}         删除单条记录
  GET    /api/v1/awards/stats        中标统计概览
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
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

    # 去重中标方数
    from sqlalchemy import distinct
    winner_count_q = select(func.count(distinct(HistoricalAward.winner_name))).select_from(HistoricalAward)
    winner_count = (await db.execute(winner_count_q)).scalar() or 0

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
        "winner_count": winner_count,
        "categories": cat_stats,
    }


@router.get("/export", summary="导出中标结果为Excel")
async def export_awards(
    db: AsyncSession = Depends(get_db),
):
    """将所有中标结果导出为 Excel 文件。"""
    from io import BytesIO
    from datetime import date
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    from fastapi.responses import StreamingResponse
    from urllib.parse import quote

    result = await db.execute(
        select(HistoricalAward).order_by(desc(HistoricalAward.bid_open_date))
    )
    awards = result.scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "中标结果"

    header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    data_font = Font(name="微软雅黑", size=10)
    data_align = Alignment(vertical="center")
    data_align_center = Alignment(horizontal="center", vertical="center")
    link_font = Font(name="微软雅黑", size=10, color="0563C1", underline="single")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    even_fill = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")

    headers = ["序号", "项目名称", "中标方", "中标份额(%)", "项目类别", "公示日期", "公告链接"]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    ws.freeze_panes = "A2"

    for row_idx, award in enumerate(awards, 2):
        row_data = [
            row_idx - 1,
            award.project_name or "",
            award.winner_name or "",
            float(award.discount_rate) if award.discount_rate else "",
            award.project_category or "",
            award.bid_open_date.strftime("%Y-%m-%d") if award.bid_open_date else "",
            award.source_url or "",
        ]
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = data_font
            cell.border = thin_border
            if col_idx in (1, 4, 5, 6):
                cell.alignment = data_align_center
            elif col_idx == 7 and value:
                cell.value = "打开链接"
                cell.hyperlink = value
                cell.font = link_font
                cell.alignment = data_align_center
            elif col_idx == 2:
                cell.alignment = Alignment(vertical="center", wrap_text=True)
            if row_idx % 2 == 0:
                cell.fill = even_fill

    col_widths = [6, 55, 20, 14, 14, 13, 14]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 28
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(awards) + 1}"

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"中标结果_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


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


@router.post("/fetch", summary="手动触发中标结果采集")
async def fetch_awards(
    background_tasks: BackgroundTasks,
    province: Optional[str] = Query(None, description="目标省份，空为全国"),
):
    """后台触发中标结果数据采集。"""
    import asyncio as _asyncio

    async def _run():
        logger.info(f"🕷️ 中标结果采集开始 (省份={province or '全国'})...")
        try:
            from crawl_winning_results import main
            await main()
            logger.info("✅ 中标结果采集完成")
        except Exception as e:
            logger.error(f"❌ 中标结果采集失败: {e}")

    background_tasks.add_task(_run)
    return {"message": "中标结果采集已在后台启动，预计1-3分钟完成"}


@router.delete("/{award_id}", summary="删除中标结果")
async def delete_award(
    award_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除单条中标结果记录。"""
    award = await db.get(HistoricalAward, award_id)
    if not award:
        raise HTTPException(status_code=404, detail=f"中标记录 {award_id} 不存在")

    await db.delete(award)
    await db.commit()
    logger.info(f"已删除中标记录: id={award_id}, project={award.project_name}, winner={award.winner_name}")

    return {"ok": True, "message": f"已删除中标记录 {award_id}"}
