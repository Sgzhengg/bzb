"""
招标公告 API 接口

端点:
  GET    /api/v1/announcements         公告列表（排序/筛选/分页 + 机会评分）
  GET    /api/v1/announcements/{id}    公告详情（评分+提醒+在位者）
  POST   /api/v1/announcements/fetch   手动触发采集
  POST   /api/v1/announcements/{id}/favorite  收藏/取消收藏
  GET    /api/v1/announcements/favorites      获取收藏列表
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
    favorites_only: bool = Query(False, description="仅显示收藏"),
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
        conditions.append(
            (Announcement.budget >= budget_min) | (Announcement.budget == None)
        )
    if budget_max is not None:
        conditions.append(
            (Announcement.budget <= budget_max) | (Announcement.budget == None)
        )
    if search:
        conditions.append(Announcement.title.ilike(f"%{search}%"))

    # 自动过滤已过期的公告（投标截止日期 < 今天）
    from datetime import datetime as dt
    today = dt.now()
    conditions.append(Announcement.deadline >= today)

    # 仅显示收藏
    if favorites_only:
        conditions.append(Announcement.is_favorited == True)

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
        # 计算机会评分（使用评分引擎）
        score_data = _compute_announcement_score(ann)

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
            # 收藏
            "is_favorited": getattr(ann, 'is_favorited', False) or False,
            # 评分（来自评分引擎）
            "total_score": score_data.get("total_score"),
            "probability_label": score_data.get("probability_label", ""),
            "detail_scores": score_data.get("detail_scores", {}),
            "recommendation": score_data.get("recommendation", ""),
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

    # 机会评分
    score_data = _compute_announcement_score(ann)

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
        # 评分
        "total_score": score_data.get("total_score"),
        "probability_label": score_data.get("probability_label", ""),
        "detail_scores": score_data.get("detail_scores", {}),
        "recommendation": score_data.get("recommendation", ""),
        # 提醒与在位者
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


# ============================================================
# 收藏/取消收藏
# ============================================================

@router.post("/{announcement_id}/favorite", summary="收藏/取消收藏公告")
async def toggle_favorite(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
):
    """切换公告收藏状态。已收藏则取消，未收藏则收藏。"""
    ann = await db.get(Announcement, announcement_id)
    if not ann:
        raise HTTPException(status_code=404, detail=f"公告 {announcement_id} 不存在")

    current = getattr(ann, 'is_favorited', False) or False
    ann.is_favorited = not current
    await db.commit()

    return {
        "announcement_id": announcement_id,
        "is_favorited": ann.is_favorited,
        "message": "已收藏" if ann.is_favorited else "已取消收藏",
    }


@router.get("/favorites", summary="获取收藏列表")
async def list_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取已收藏的公告列表。"""
    count_q = select(func.count()).select_from(Announcement).where(
        Announcement.is_favorited == True
    )
    total = (await db.execute(count_q)).scalar() or 0

    list_q = (
        select(Announcement)
        .where(Announcement.is_favorited == True)
        .order_by(desc(Announcement.announce_date))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(list_q)
    announcements = result.scalars().all()

    items = []
    for ann in announcements:
        score_data = _compute_announcement_score(ann)
        items.append({
            "id": ann.id,
            "title": ann.title,
            "project_category": ann.project_category,
            "procurement_method": ann.procurement_method,
            "budget": float(ann.budget) if ann.budget else None,
            "announce_date": ann.announce_date.isoformat() if ann.announce_date else None,
            "deadline": ann.deadline.isoformat() if ann.deadline else None,
            "purchaser": ann.purchaser.name if ann.purchaser else "",
            "total_score": score_data.get("total_score"),
            "probability_label": score_data.get("probability_label", ""),
            "is_favorited": True,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ============================================================
# 机会评分辅助函数
# ============================================================

def _compute_announcement_score(ann: Announcement) -> dict:
    """使用评分引擎计算公告的机会评分（简化版，适合列表批量计算）。"""
    try:
        # 1. 采购方式公平性
        method = ann.procurement_method or ""
        fairness_map = {"公开招标": 100, "公开询比": 80, "竞争性谈判": 50, "单一来源": 0}
        fairness = float(fairness_map.get(method.strip(), 60))

        # 2. HHI集中度（无历史数据时默认中性）
        hhi = 60.0

        # 3. 项目类别匹配度（无偏好时中性）
        category = 60.0

        # 4. 预算健康度（基于预算规模）
        budget_val = float(ann.budget) if ann.budget else 0
        if budget_val >= 200:
            budget = 90.0
        elif budget_val >= 100:
            budget = 75.0
        elif budget_val >= 50:
            budget = 60.0
        elif budget_val > 0:
            budget = 45.0
        else:
            budget = 50.0

        # 5. 在位者优势（默认无在位者，最高分）
        incumbent = 100.0

        # 6. 客情关系（默认无客情）
        relation = 50.0

        # 权重加权
        weights = {
            "procurement_fairness": 0.20,
            "hhi_concentration": 0.20,
            "category_match": 0.20,
            "budget_health": 0.15,
            "incumbent_advantage": 0.15,
            "client_relation": 0.10,
        }

        total = (
            fairness * weights["procurement_fairness"]
            + hhi * weights["hhi_concentration"]
            + category * weights["category_match"]
            + budget * weights["budget_health"]
            + incumbent * weights["incumbent_advantage"]
            + relation * weights["client_relation"]
        )

        # 陪跑概率标签
        if total >= 75:
            prob_label = "低"
        elif total >= 50:
            prob_label = "中"
        else:
            prob_label = "高"

        # 推荐建议
        if total >= 75:
            rec = "🌟 高机会：建议优先跟进，竞争环境有利"
        elif total >= 50:
            rec = "👍 中等机会：评估自身优势后决定是否参与"
        else:
            rec = "⚠️ 低机会：竞争激烈或在位者优势明显，谨慎评估"

        return {
            "total_score": round(total, 1),
            "probability_label": prob_label,
            "recommendation": rec,
            "detail_scores": {
                "procurement_fairness": round(fairness, 1),
                "hhi_concentration": round(hhi, 1),
                "category_match": round(category, 1),
                "budget_health": round(budget, 1),
                "incumbent_advantage": round(incumbent, 1),
                "client_relation": round(relation, 1),
            },
        }
    except Exception as e:
        logger.warning(f"评分计算失败: {e}")
        return {
            "total_score": None,
            "probability_label": "",
            "recommendation": "",
            "detail_scores": {},
        }


# ============================================================
# B2B 原文代理（通过 b2b API 获取公告原文）
# ============================================================

@router.get("/{announcement_id}/original", summary="获取 b2b 公告原文")
async def get_original_content(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    通过 b2b.10086.cn API 搜索公告原文。
    返回原文内容和可直接跳转的搜索链接。
    
    注意：b2b.10086.cn 是 SPA 架构，公告详情没有独立 URL。
    此接口通过其后端 API 获取公告内容。
    """
    ann = await db.get(Announcement, announcement_id)
    if not ann:
        raise HTTPException(status_code=404, detail=f"公告 {announcement_id} 不存在")
    
    from app.services.b2b_proxy import (
        search_announcement, find_best_match, 
        format_announcement_detail, build_search_url,
    )
    
    # 用前30字符作为搜索关键词
    keyword = (ann.title or "")[:30]
    
    # 尝试不同的 publishType 搜索
    result = None
    for ptype in ["PROCUREMENT", "VENDOR", "PURCHASE_SERVICE"]:
        items = await search_announcement(keyword, publish_type=ptype, page_size=5)
        match = find_best_match(items, ann.title or "")
        if match:
            result = format_announcement_detail(match)
            result["publish_type_searched"] = ptype
            break
    
    if not result:
        # 返回搜索链接，让用户手动搜索
        return {
            "found": False,
            "announcement_id": announcement_id,
            "title": ann.title,
            "search_url": build_search_url(keyword),
            "message": "未在 b2b.10086.cn 找到匹配的公告原文，请点击搜索链接手动查找",
        }
    
    return {
        "found": True,
        "announcement_id": announcement_id,
        "search_url": build_search_url(keyword),
        **result,
    }


# ============================================================
# 预算抓取（zhaobiao.cn 登录后自动提取）
# ============================================================

@router.post("/scrape-budget/start", summary="启动预算抓取（需手动登录 zhaobiao.cn）")
async def start_budget_scrape():
    """
    启动后台预算抓取任务。
    
    流程：
    1. 打开 zhaobiao.cn 浏览器窗口
    2. 用户手动登录（含验证码）
    3. 系统自动抓取每条公告的预算/报名费/保证金
    4. 更新数据库
    
    前端应轮询 GET /scrape-budget/status 获取进度。
    """
    from app.services.budget_scraper import start_scrape_async, get_state, ScrapeStatus

    state = get_state()
    if state.status in (ScrapeStatus.WAITING_LOGIN, ScrapeStatus.SCRAPING):
        return {"ok": False, "message": "抓取任务已在运行中", "status": state.status}

    # 获取数据库路径
    db_url = getattr(settings, 'DATABASE_URL', '')
    # sqlite+aiosqlite:///./biaozhongbao.db → biaozhongbao.db
    for prefix in ['sqlite+aiosqlite:///', 'sqlite:///']:
        if db_url.startswith(prefix):
            db_url = db_url[len(prefix):]
            break
    if not db_url:
        db_url = "biaozhongbao.db"

    start_scrape_async(db_url)
    return {"ok": True, "message": "抓取任务已启动，请在弹出的浏览器中登录", "status": "waiting_login"}


@router.get("/scrape-budget/status", summary="查询预算抓取进度")
async def get_budget_scrape_status():
    """返回当前抓取任务的状态和结果。"""
    from app.services.budget_scraper import get_state

    state = get_state()
    return {
        "status": state.status,
        "message": state.message,
        "login_elapsed": state.login_elapsed,
        "results": state.results,
    }
