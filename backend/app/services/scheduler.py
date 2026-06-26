"""
标中宝 V1 — 定时任务调度器

任务:
  每日 08:00    抓取最新招标公告
  每日 20:00    再次抓取（确保不漏采）
  每 30 分钟    检查新公告 → 触发客情关联提醒
  每周一 09:00  生成上周机会周报
"""

import logging
from datetime import datetime, date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError

logger = logging.getLogger(__name__)

# 全局单例
_scheduler: AsyncIOScheduler | None = None


# ============================================================
# 调度器管理
# ============================================================

def get_scheduler() -> AsyncIOScheduler:
    """获取全局调度器实例（懒初始化）。"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler():
    """启动调度器并注册所有定时任务。"""
    sched = get_scheduler()

    if sched.running:
        logger.info("调度器已在运行中")
        return

    # ── 注册任务 ──
    _register_jobs(sched)

    sched.start()
    logger.info("⏰ 定时任务调度器已启动（4 个任务）")
    _print_jobs(sched)


def stop_scheduler():
    """停止调度器。"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("⏰ 定时任务调度器已停止")


def get_scheduler_status() -> dict:
    """获取调度器运行状态。"""
    sched = get_scheduler()
    jobs = []
    if sched.running:
        for job in sched.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            })

    return {
        "running": sched.running,
        "job_count": len(jobs),
        "jobs": jobs,
    }


def _print_jobs(sched: AsyncIOScheduler):
    """打印所有已注册任务的信息。"""
    for job in sched.get_jobs():
        logger.info(f"  📅 {job.id}: next={job.next_run_time}")


# ============================================================
# 任务注册
# ============================================================

def _register_jobs(sched: AsyncIOScheduler):
    """注册所有定时任务。"""
    from app.core.config import settings

    if settings.CRAWLER_ENABLED:
        # 每日 08:00 抓取
        sched.add_job(
            _job_fetch_announcements,
            CronTrigger(hour=8, minute=0),
            id="fetch_morning",
            name="每日早间抓取",
            replace_existing=True,
        )
        # 每日 20:00 抓取
        sched.add_job(
            _job_fetch_announcements,
            CronTrigger(hour=20, minute=0),
            id="fetch_evening",
            name="每日晚间抓取",
            replace_existing=True,
        )
    else:
        logger.info("爬虫已禁用，跳过抓取任务注册")

    # 每 30 分钟客情关联检查
    sched.add_job(
        _job_check_alerts,
        IntervalTrigger(minutes=30),
        id="alert_check",
        name="客情关联检查（每30分钟）",
        replace_existing=True,
    )

    # 每周一 09:00 周报
    sched.add_job(
        _job_weekly_report,
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="weekly_report",
        name="每周机会周报",
        replace_existing=True,
    )


# ============================================================
# 任务实现
# ============================================================

async def _job_fetch_announcements():
    """定时抓取招标公告（通过 DataCollector 统一调度）。"""
    logger.info("🕷️ [定时任务] 开始抓取最新招标公告...")
    try:
        from data_collector import get_collector

        collector = get_collector()
        # 使用默认适配器（当前: zhaobiao），自动入库
        results = await collector.collect_async(save_to_db=True)

        if results:
            from app.db.session import AsyncSessionLocal
            from app.services.alert_service import batch_process_new_announcements
            async with AsyncSessionLocal() as db:
                alert_stats = await batch_process_new_announcements(db, limit=200)
                logger.info(f"[定时任务] 新增公告 {len(results)} 条, "
                            f"创建提醒 {alert_stats['alerts_created']} 条")
        else:
            logger.info("[定时任务] 未发现新广告类公告")
    except Exception as e:
        logger.error(f"[定时任务] 抓取失败: {e}")


async def _job_check_alerts():
    """定时检查新公告并创建客情关联提醒。"""
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.alert_service import batch_process_new_announcements

        async with AsyncSessionLocal() as db:
            stats = await batch_process_new_announcements(db, limit=100)
            if stats["total_checked"] > 0:
                logger.info(f"[定时任务] 客情检查: 处理{stats['total_checked']}条, "
                            f"创建{stats['alerts_created']}条提醒")
    except Exception as e:
        logger.error(f"[定时任务] 客情检查失败: {e}")


async def _job_weekly_report():
    """生成上周机会周报。"""
    logger.info("📊 [定时任务] 生成上周机会周报...")
    try:
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text

        today = date.today()
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)

        async with AsyncSessionLocal() as db:
            # 上周新公告数量
            count_result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM announcements
                    WHERE announce_date BETWEEN :start AND :end
                """),
                {"start": last_monday, "end": last_sunday},
            )
            new_count = count_result.scalar() or 0

            # 上周中标公告数量
            award_result = await db.execute(
                text("""
                    SELECT COUNT(*), COALESCE(SUM(bid_amount), 0)
                    FROM historical_awards
                    WHERE bid_open_date BETWEEN :start AND :end
                """),
                {"start": last_monday, "end": last_sunday},
            )
            award_row = award_result.fetchone()
            award_count = award_row[0] if award_row else 0
            award_total = float(award_row[1] or 0)

            # 客情新增
            relation_result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM client_relations
                    WHERE created_at::date BETWEEN :start AND :end
                """),
                {"start": last_monday, "end": last_sunday},
            )
            new_relations = relation_result.scalar() or 0

            report = (
                f"📊 标中宝 周报 ({last_monday} ~ {last_sunday})\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  📋 新公告:     {new_count} 条\n"
                f"  🏆 新中标:     {award_count} 条 (总额 {award_total:.0f} 万元)\n"
                f"  👤 新客情:     {new_relations} 条\n"
                f"  🔔 提醒:       请登录系统查看详情"
            )

            logger.info(report)
    except Exception as e:
        logger.error(f"[定时任务] 周报生成失败: {e}")
