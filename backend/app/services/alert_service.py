"""
客情-项目自动关联提醒服务

当新招标公告入库时，自动检测采购方是否有客情记录，
如有则生成关联提醒。
"""

import logging
from datetime import date
from typing import List, Dict, Optional, Tuple

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.announcement import Announcement
from app.models.client_relation import ClientRelation, Purchaser
from app.models.project_relation_alert import ProjectRelationAlert

logger = logging.getLogger(__name__)

# 评级排序
RATING_ORDER = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}


# ============================================================
# 格式化提醒内容
# ============================================================

def _format_alert_message(
    contact_name: str,
    purchaser_name: str,
    title: str,
    last_contact_date: Optional[date],
    rating: str,
) -> str:
    """格式化提醒消息文本。"""
    parts = [f"您有客户【{contact_name}】在【{purchaser_name}】"]

    if title:
        parts.append(f"，职位【{title}】")

    if last_contact_date:
        parts.append(f"，最近联系于【{last_contact_date}】")

    parts.append(f"。\n建议先联系对方了解项目背景。关系评级：【{rating}】")

    return "".join(parts)


# ============================================================
# 核心：检测并创建提醒
# ============================================================

async def check_and_create_alerts(
    announcement_id: int,
    db: AsyncSession,
) -> Dict:
    """
    检测一条公告的采购方是否有客情记录，并自动创建提醒。

    Args:
        announcement_id: 招标公告ID
        db: 数据库会话

    Returns:
        {
            "created": True/False,
            "count": 创建的提醒数量,
            "message": "说明信息",
            "alerts": [创建的提醒ID列表]
        }

    Raises:
        ValueError: 公告不存在
    """
    # ── 1. 查询公告 ──
    ann = await db.get(Announcement, announcement_id)
    if not ann:
        raise ValueError(f"公告ID {announcement_id} 不存在")

    purchaser_id = ann.purchaser_id

    # ── 2. 查询该采购方的所有客情记录 ──
    result = await db.execute(
        select(ClientRelation)
        .where(ClientRelation.purchaser_id == purchaser_id)
        .options(selectinload(ClientRelation.purchaser))
    )
    relations = result.scalars().all()

    if not relations:
        logger.info(f"公告#{announcement_id}: 采购方{purchaser_id}无客情记录，跳过")
        return {
            "created": False,
            "count": 0,
            "message": f"采购方ID {purchaser_id} 无客情记录",
            "alerts": [],
        }

    # ── 3. 按评级排序，只取最高评级 ──
    relations_sorted = sorted(
        relations,
        key=lambda r: RATING_ORDER.get(r.rating, 0),
        reverse=True,
    )
    best_relation = relations_sorted[0]

    # ── 4. 获取采购方名称 ──
    purchaser = best_relation.purchaser
    purchaser_name = purchaser.name if purchaser else f"采购方{purchaser_id}"

    # ── 5. 生成提醒内容 ──
    alert_reason = _format_alert_message(
        contact_name=best_relation.contact_name,
        purchaser_name=purchaser_name,
        title=best_relation.title or "",
        last_contact_date=best_relation.last_contact_date,
        rating=best_relation.rating,
    )

    # ── 6. 创建提醒（利用唯一约束，重复创建自动忽略） ──
    created_ids = []

    for rel in relations_sorted:
        # 检查是否已存在
        existing = await db.execute(
            select(ProjectRelationAlert).where(
                and_(
                    ProjectRelationAlert.announcement_id == announcement_id,
                    ProjectRelationAlert.relation_id == rel.id,
                )
            )
        )
        if existing.scalar_one_or_none():
            logger.debug(f"公告#{announcement_id} 与客情#{rel.id} 的提醒已存在，跳过")
            continue

        if rel == best_relation:
            reason = alert_reason
        else:
            # 非最高评级：简化提醒
            reason = (
                f"您还有客户【{rel.contact_name}】在【{purchaser_name}】，"
                f"评级【{rel.rating}】。如有需要也可联系。"
            )

        alert = ProjectRelationAlert(
            announcement_id=announcement_id,
            relation_id=rel.id,
            alert_reason=reason,
            is_read=False,
        )
        db.add(alert)
        created_ids.append(rel.id)

    if created_ids:
        await db.commit()
        logger.info(
            f"公告#{announcement_id}: 创建{len(created_ids)}条提醒 "
            f"(最高评级: {best_relation.rating}, 联系人: {best_relation.contact_name})"
        )

    return {
        "created": len(created_ids) > 0,
        "count": len(created_ids),
        "message": (
            f"为公告#{announcement_id}创建了{len(created_ids)}条提醒，"
            f"最高评级联系人: {best_relation.contact_name}({best_relation.rating})"
        ),
        "alerts": created_ids,
    }


# ============================================================
# 批量处理
# ============================================================

async def batch_process_new_announcements(
    db: AsyncSession,
    limit: int = 100,
) -> Dict:
    """
    批量处理尚未生成提醒的公告（定时任务入口）。

    查找所有 announcements 中还没有对应 project_relation_alerts 记录的公告，
    逐一调用 check_and_create_alerts。

    Args:
        db: 数据库会话
        limit: 单次处理上限

    Returns:
        {
            "total_checked": 检查的公告数,
            "alerts_created": 创建的提醒总数,
            "skipped": 跳过的数量（已有提醒或无客情）,
            "errors": 处理失败的数量
        }
    """
    # 查找还没有提醒的公告
    subquery = (
        select(ProjectRelationAlert.announcement_id).distinct()
    ).subquery()

    result = await db.execute(
        select(Announcement.id)
        .where(Announcement.id.not_in(select(subquery.c.announcement_id)))
        .order_by(Announcement.created_at.desc())
        .limit(limit)
    )
    unprocessed_ids = [row[0] for row in result.fetchall()]

    if not unprocessed_ids:
        return {
            "total_checked": 0,
            "alerts_created": 0,
            "skipped": 0,
            "errors": 0,
        }

    logger.info(f"批量处理: {len(unprocessed_ids)} 条未处理公告")

    stats = {"total_checked": len(unprocessed_ids), "alerts_created": 0, "skipped": 0, "errors": 0}

    for aid in unprocessed_ids:
        try:
            result = await check_and_create_alerts(aid, db)
            if result["created"]:
                stats["alerts_created"] += result["count"]
            else:
                stats["skipped"] += 1
        except Exception as e:
            logger.error(f"批量处理公告#{aid} 失败: {e}")
            stats["errors"] += 1

    return stats


# ============================================================
# 查询提醒
# ============================================================

async def get_alerts_for_announcement(
    announcement_id: int,
    db: AsyncSession,
    unread_only: bool = False,
) -> List[Dict]:
    """
    获取某条公告的关联提醒列表。

    Args:
        announcement_id: 公告ID
        db: 数据库会话
        unread_only: 是否只查询未读提醒

    Returns:
        提醒列表（含客情详情）
    """
    conditions = [ProjectRelationAlert.announcement_id == announcement_id]
    if unread_only:
        conditions.append(ProjectRelationAlert.is_read == False)

    result = await db.execute(
        select(ProjectRelationAlert)
        .where(and_(*conditions))
        .options(
            selectinload(ProjectRelationAlert.relation).selectinload(ClientRelation.purchaser)
        )
        .order_by(ProjectRelationAlert.created_at.desc())
    )
    alerts = result.scalars().all()

    return [
        {
            "id": a.id,
            "announcement_id": a.announcement_id,
            "relation_id": a.relation_id,
            "alert_reason": a.alert_reason,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat() if a.created_at else None,
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


async def mark_alert_read(
    alert_id: int,
    db: AsyncSession,
) -> bool:
    """标记一条提醒为已读。"""
    alert = await db.get(ProjectRelationAlert, alert_id)
    if not alert:
        return False
    alert.is_read = True
    await db.commit()
    return True


async def mark_all_read_for_announcement(
    announcement_id: int,
    db: AsyncSession,
) -> int:
    """将某条公告的所有提醒标记为已读，返回更新条数。"""
    result = await db.execute(
        select(ProjectRelationAlert).where(
            and_(
                ProjectRelationAlert.announcement_id == announcement_id,
                ProjectRelationAlert.is_read == False,
            )
        )
    )
    alerts = result.scalars().all()
    for a in alerts:
        a.is_read = True
    await db.commit()
    return len(alerts)


async def get_unread_count(
    db: AsyncSession,
) -> int:
    """获取未读提醒总数。"""
    result = await db.execute(
        select(ProjectRelationAlert).where(ProjectRelationAlert.is_read == False)
    )
    return len(result.scalars().all())
