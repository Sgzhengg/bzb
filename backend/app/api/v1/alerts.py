"""
客情-项目关联提醒 API 接口

端点:
  POST   /api/v1/alerts/check/{announcement_id}   手动触发检测
  POST   /api/v1/alerts/batch                     批量处理新公告（定时任务入口）
  GET    /api/v1/alerts/announcement/{id}          获取公告的提醒列表
  GET    /api/v1/alerts/unread-count               未读提醒数量
  PUT    /api/v1/alerts/{id}/read                  标记单条已读
  PUT    /api/v1/alerts/announcement/{id}/read     标记公告全部已读
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.alert_service import (
    check_and_create_alerts,
    batch_process_new_announcements,
    get_alerts_for_announcement,
    mark_alert_read,
    mark_all_read_for_announcement,
    get_unread_count,
)

router = APIRouter(prefix="/alerts", tags=["客情-项目关联提醒"])


# ============================================================
# 1. POST /api/v1/alerts/check/{announcement_id}
# ============================================================

@router.post(
    "/check/{announcement_id}",
    summary="检测并创建关联提醒",
)
async def trigger_alert_check(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    手动触发：检测指定公告的采购方是否有客情记录，自动生成提醒。

    同样可用于新公告入库时的回调调用。
    """
    try:
        result = await check_and_create_alerts(announcement_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检测失败: {str(e)}",
        )


# ============================================================
# 2. POST /api/v1/alerts/batch — 批量处理（定时任务入口）
# ============================================================

@router.post(
    "/batch",
    summary="批量处理新公告（定时任务入口）",
)
async def trigger_batch_process(
    limit: int = Query(100, ge=1, le=500, description="单次处理上限"),
    db: AsyncSession = Depends(get_db),
):
    """
    批量处理尚未生成提醒的新公告。

    可用于定时任务（如 cron / APScheduler）定期调用。
    """
    stats = await batch_process_new_announcements(db, limit=limit)
    return {"status": "ok", **stats}


# ============================================================
# 3. GET /api/v1/alerts/announcement/{announcement_id}
# ============================================================

@router.get(
    "/announcement/{announcement_id}",
    summary="获取公告的关联提醒",
)
async def list_alerts_for_announcement(
    announcement_id: int,
    unread_only: bool = Query(False, description="仅显示未读"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定公告的所有客情关联提醒，含联系人详情。

    前端可在项目详情页调用此接口展示提醒卡片。
    """
    alerts = await get_alerts_for_announcement(
        announcement_id, db, unread_only=unread_only
    )
    return {"announcement_id": announcement_id, "total": len(alerts), "items": alerts}


# ============================================================
# 4. GET /api/v1/alerts/unread-count
# ============================================================

@router.get(
    "/unread-count",
    summary="获取未读提醒数量",
)
async def get_unread_alert_count(
    db: AsyncSession = Depends(get_db),
):
    """获取系统中全部未读提醒的数量（用于导航栏红点提示）。"""
    count = await get_unread_count(db)
    return {"unread_count": count}


# ============================================================
# 5. PUT /api/v1/alerts/{alert_id}/read
# ============================================================

@router.put(
    "/{alert_id}/read",
    summary="标记单条提醒已读",
)
async def mark_single_read(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    """将指定提醒标记为已读。"""
    success = await mark_alert_read(alert_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"提醒 {alert_id} 不存在",
        )
    return {"message": "已标记为已读", "alert_id": alert_id}


# ============================================================
# 6. PUT /api/v1/alerts/announcement/{announcement_id}/read
# ============================================================

@router.put(
    "/announcement/{announcement_id}/read",
    summary="标记公告全部提醒已读",
)
async def mark_announcement_all_read(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
):
    """将指定公告的所有未读提醒批量标记为已读。"""
    count = await mark_all_read_for_announcement(announcement_id, db)
    return {
        "message": f"已标记 {count} 条提醒为已读",
        "announcement_id": announcement_id,
        "updated_count": count,
    }
