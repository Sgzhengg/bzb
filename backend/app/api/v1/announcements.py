"""
招标公告 API 接口

端点:
  GET    /api/v1/announcements         公告列表（排序/筛选/分页）
  GET    /api/v1/announcements/{id}    公告详情（评分+提醒+在位者）
  POST   /api/v1/announcements/fetch   手动触发采集
"""

import logging
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import select, func, and_, or_, desc, asc, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.announcement import Announcement
from app.models.client_relation import Purchaser, ClientRelation
from app.models.project_relation_alert import ProjectRelationAlert
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/announcements", tags=["招标公告"])


# ============================================================
# 公告列表
# ============================================================

@router.get("", summary="获取公告列表")
async def list_announcements(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort: Optional[str] = Query(None, description="排序字段: score_desc/date_desc/budget_desc"),
    purchaser_level: Optional[str] = Query(None, description="采购方层级筛选"),
    project_category: Optional[str] = Query(None, description="项目类别筛选"),
    procurement_method: Optional[str] = Query(None, description="采购方式筛选"),
    probability_label: Optional[str] = Query(None, description="陪跑概率: 低/中/高"),
    budget_min: Optional[float] = Query(None, description="预算下限"),
    budget_max: Optional[float] = Query(None, description="预算上限"),
    search: Optional[str] = Query(None, description="项目名称搜索"),
    db: AsyncSession = Depends(get_db),
):
    """获取招标公告列表，支持多维筛选、排序和分页。"""
    conditions = []

    if purchaser_level:
        conditions.append(Announcement.purchaser_level == purchaser_level)
    if project_category:
        conditions.append(Announcement.project_category == project_category)
    if procurement_method:
        conditions.append(Announcement.procurement_method == procurement_method)
    if budget_min is not None:
        conditions.append(Announcement.budget >= budget_min)
    if budget_max is not None:
        conditions.append(Announcement.budget <= budget_max)
    if search:
        conditions.append(Announcement.title.ilike(f"%{search}%"))

    # 总数
    count_q = select(func.count()).select_from(Announcement)
    if conditions:
        count_q = count_q.where(and_(*conditions))
    total = (await db.execute(count_q)).scalar() or 0

    # 排序
    order_clauses = [desc(Announcement.announce_date)]
    if sort == "score_desc":
        order_clauses = [desc(Announcement.announce_date)]  # 默认日期降序（评分由前端Mock）
    elif sort == "date_desc":
        order_clauses = [desc(Announcement.announce_date)]
    elif sort == "budget_desc":
        order_clauses = [desc(Announcement.budget)]

    # 分页查询
    list_q = (
        select(Announcement)
        .options(selectinload(Announcement.purchaser))
        .order_by(*order_clauses)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if conditions:
        list_q = list_q.where(and_(*conditions))

    result = await db.execute(list_q)
    announcements = result.scalars().all()

    items = []
    for ann in announcements:
        purchaser_name = ann.purchaser.name if ann.purchaser else ""
        items.append({
            "id": ann.id,
            "title": ann.title,
            # Excel模板字段
            "industry": getattr(ann, 'industry', '') or '',
            "province": getattr(ann, 'province', '') or '',
            "city": getattr(ann, 'city', '') or '',
            "project_category": ann.project_category,
            "procurement_method": ann.procurement_method,
            "budget": float(ann.budget) if ann.budget else None,
            "source_url": ann.source_url or '',
            "announce_date": ann.announce_date.isoformat() if ann.announce_date else None,
            "deadline": ann.deadline.isoformat() if ann.deadline else None,
            "deadline_time": getattr(ann, 'deadline_time', '') or '',
            "bid_date": ann.bid_date.isoformat() if getattr(ann, 'bid_date', None) else None,
            "bid_time": getattr(ann, 'bid_time', '') or '',
            "registration_fee": float(getattr(ann, 'registration_fee', 0) or 0),
            "deposit": float(getattr(ann, 'deposit', 0) or 0),
            "remark": getattr(ann, 'remark', '') or '',
            # 辅助字段
            "purchaser": purchaser_name,
            "purchaser_id": ann.purchaser_id,
            "purchaser_level": ann.purchaser_level,
            "created_at": ann.created_at.isoformat() if ann.created_at else None,
            # 评分
            "total_score": float(ann.total_score) if getattr(ann, 'total_score', None) else None,
            "probability_label": getattr(ann, 'probability_label', '') or '',
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


# ============================================================
# 公告详情（含评分、在位者、提醒、历史参考）
# ============================================================

@router.get("/{announcement_id}", summary="获取公告详情")
async def get_announcement_detail(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取公告详情，自动附带：
    - 采购方信息
    - 关联客情提醒
    - 历史中标参考（同采购方+同赛道）
    - 在位者检测结果
    """
    ann = await db.get(Announcement, announcement_id)
    if not ann:
        raise HTTPException(status_code=404, detail=f"公告 {announcement_id} 不存在")

    # 采购方
    purchaser = ann.purchaser
    purchaser_name = purchaser.name if purchaser else ""

    # 关联提醒
    alerts_result = await db.execute(
        select(ProjectRelationAlert)
        .where(ProjectRelationAlert.announcement_id == announcement_id)
        .options(
            selectinload(ProjectRelationAlert.relation).selectinload(ClientRelation.purchaser)
        )
        .order_by(ProjectRelationAlert.created_at.desc())
    )
    alerts = alerts_result.scalars().all()
    alert_items = [
        {
            "id": a.id,
            "alert_reason": a.alert_reason,
            "is_read": a.is_read,
            "contact_name": a.relation.contact_name if a.relation else "",
            "contact_rating": a.relation.rating if a.relation else "",
            "contact_phone": a.relation.phone if a.relation else "",
            "purchaser_name": (
                a.relation.purchaser.name
                if (a.relation and a.relation.purchaser) else ""
            ),
        }
        for a in alerts
    ]

    # 历史中标参考
    from sqlalchemy import text
    history_result = await db.execute(
        text("""
            SELECT * FROM historical_awards
            WHERE purchaser_id = :pid AND project_category = :cat
            ORDER BY bid_open_date DESC LIMIT 5
        """),
        {"pid": ann.purchaser_id, "cat": ann.project_category},
    )
    history_rows = history_result.fetchall()
    history_items = [
        {
            "project_name": row.project_name,
            "winner_name": row.winner_name,
            "winner_type": row.winner_type,
            "bid_amount": float(row.bid_amount) if row.bid_amount else None,
            "budget_amount": float(row.budget_amount) if row.budget_amount else None,
            "discount_rate": float(row.discount_rate) if row.discount_rate else None,
            "bid_open_date": row.bid_open_date.isoformat() if row.bid_open_date else None,
            "contract_end": row.contract_end.isoformat() if row.contract_end else None,
            "is_continuous": row.is_continuous,
            "continuous_count": row.continuous_count,
        }
        for row in history_rows
    ]

    # 在位者检测
    incumbent_info = None
    if history_items:
        from app.services.incumbent_detector import detect_incumbent
        inc_result = detect_incumbent(
            {"purchaser_id": ann.purchaser_id, "project_category": ann.project_category},
            history_items,
        )
        incumbent_info = {
            "has_incumbent": inc_result.has_incumbent,
            "incumbent_name": inc_result.incumbent_name,
            "continuous_count": inc_result.continuous_count,
            "risk_level": inc_result.risk_level,
            "reason": inc_result.reason,
        }

    return {
        "id": ann.id,
        "title": ann.title,
        "purchaser": purchaser_name,
        "purchaser_id": ann.purchaser_id,
        "purchaser_level": ann.purchaser_level,
        "project_category": ann.project_category,
        "procurement_method": ann.procurement_method,
        "budget": float(ann.budget) if ann.budget else None,
        "deadline": ann.deadline.isoformat() if ann.deadline else None,
        "announce_date": ann.announce_date.isoformat() if ann.announce_date else None,
        "qualification_requirements": ann.qualification_requirements,
        "score_weight": ann.score_weight,
        "source_url": ann.source_url,
        "created_at": ann.created_at.isoformat() if ann.created_at else None,
        "alerts": alert_items,
        "history_reference": history_items,
        "incumbent_info": incumbent_info,
    }


# ============================================================
# 手动触发采集
# ============================================================

@router.post("/fetch", summary="手动触发数据采集")
async def fetch_announcements(
    background_tasks: BackgroundTasks,
):
    """
    触发爬虫采集最新招标公告。

    实际采集在后台异步执行，避免阻塞请求。
    """
    if not settings.CRAWLER_ENABLED:
        return {"status": "disabled", "message": "爬虫功能已禁用（BZB_CRAWLER_ENABLED=false）"}

    # 后台任务
    async def _run_crawler():
        try:
            from app.services.crawler.pipeline import BiddingCrawlerPipeline
            pipeline = BiddingCrawlerPipeline()
            results = await pipeline.run(max_pages=settings.CRAWLER_MAX_PAGES)
            logger.info(f"采集完成: {len(results)} 条")
        except Exception as e:
            logger.error(f"采集失败: {e}")

    background_tasks.add_task(_run_crawler)

    return {
        "status": "started",
        "message": f"数据采集已在后台启动（最多 {settings.CRAWLER_MAX_PAGES} 页）",
    }


@router.post("/discover", summary="多引擎搜索发现招标公告")
async def discover_announcements(
    background_tasks: BackgroundTasks,
    queries: Optional[List[str]] = None,
    max_per_query: int = Query(10, ge=1, le=30, description="每个查询最大结果数"),
    auto_crawl: bool = Query(False, description="是否自动使用 AI 爬虫抓取发现的内容"),
):
    """
    使用多搜索引擎（Baidu/Bing/DuckDuckGo）聚合搜索，
    发现各招标网站上的广东移动广告类公告链接。

    可选：自动使用 AI 爬虫抓取发现的页面内容。
    """
    try:
        from app.services.search_discovery import (
            discover_bidding_announcements,
            discover_and_crawl,
        )
    except ImportError as e:
        return {
            "status": "error",
            "message": f"搜索发现模块不可用: {e}",
        }

    if auto_crawl:
        async def _run_discover_and_crawl():
            try:
                result = await discover_and_crawl(
                    queries=queries,
                    max_per_query=max_per_query,
                )
                logger.info(
                    f"搜索发现+爬取完成: 发现 {result['stats']['discovered']} 条, "
                    f"爬取成功 {result['stats']['crawled_success']} 条"
                )
            except Exception as e:
                logger.error(f"搜索发现+爬取失败: {e}")

        background_tasks.add_task(_run_discover_and_crawl)

        return {
            "status": "started",
            "message": "多引擎搜索发现 + AI 爬取已在后台启动",
        }
    else:
        result = await discover_bidding_announcements(
            queries=queries,
            max_per_query=max_per_query,
        )
        return {
            "status": "ok",
            "total_urls": result["total_count"],
            "urls": result["total_bidding_urls"][:20],
            "search_time": result["search_time"],
        }
