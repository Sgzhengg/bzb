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
    """注册所有定时任务（V2 多省份扩展）。"""
    from app.core.config import settings

    if settings.CRAWLER_ENABLED:
        sched.add_job(_job_fetch_announcements, CronTrigger(hour=8, minute=0),
            id="fetch_morning", name="每日早间抓取", replace_existing=True)
        sched.add_job(_job_fetch_announcements, CronTrigger(hour=20, minute=0),
            id="fetch_evening", name="每日晚间抓取", replace_existing=True)
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

    # 每日 06:00 历史中标结果采集
    sched.add_job(
        _job_collect_winning_results,
        CronTrigger(hour=6, minute=0),
        id="collect_winning",
        name="每日中标结果采集",
        replace_existing=True,
    )

    # 每日 23:59 数据验证（检查漏采）
    sched.add_job(
        _job_daily_validation,
        CronTrigger(hour=23, minute=59),
        id="daily_validation",
        name="每日数据验证",
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


async def _job_fetch_normal_provinces():
    """
    低频采集普通省份（每天一次，凌晨执行）。
    仅采集省公司级别，不深入各地市。
    """
    logger.info("🕷️ [定时任务] 开始普通省份低频采集...")
    try:
        from config.provinces import NORMAL_PROVINCES
        from app.services.crawler.config import get_search_keywords_for_province

        total_new = 0

        for idx, province_config in enumerate(NORMAL_PROVINCES):
            province_name = province_config.name
            keywords = get_search_keywords_for_province(province_name, include_ad_topics=True)

            logger.info(f"  📍 [{idx+1}/{len(NORMAL_PROVINCES)}] 低频采集: {province_name}")

            try:
                from data_collector import get_collector
                collector = get_collector()
                results = await collector.collect_async(save_to_db=True)

                if results:
                    total_new += len(results)
                    logger.info(f"     ✅ {province_name}: 新增 {len(results)} 条")
            except Exception as e:
                logger.warning(f"     ⚠️ {province_name}: {e}")

            if idx < len(NORMAL_PROVINCES) - 1:
                import asyncio as _asyncio
                await _asyncio.sleep(60)

        logger.info(f"[定时任务] 普通省份采集完成: 共新增 {total_new} 条")

    except Exception as e:
        logger.error(f"[定时任务] 普通省份采集失败: {e}")


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


async def _job_collect_winning_results():
    """每日采集历史中标结果。"""
    logger.info("🏆 [定时任务] 开始采集历史中标结果...")
    try:
        from app.services.historical_crawler.collector import HistoricalAwardCollector

        collector = HistoricalAwardCollector()
        results = await collector.collect(max_pages=3)

        if results:
            logger.info(f"[定时任务] 中标结果采集: 新增 {len(results)} 条记录")
        else:
            logger.info("[定时任务] 中标结果采集: 无新数据")
    except Exception as e:
        logger.error(f"[定时任务] 中标结果采集失败: {e}")


async def _job_daily_validation():
    """每日数据验证任务（检查漏采、重复、趋势）"""
    logger.info("🔍 [定时任务] 开始每日数据验证...")
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.cross_validator import run_daily_validation

        async with AsyncSessionLocal() as db:
            validation_result = await run_daily_validation(db)

            # 记录验证结果
            coverage = validation_result["coverage"]
            logger.info(f"[数据验证] 日期: {coverage['date']}, 总采集: {coverage['total_count']}条")

            for source, stats in coverage["by_source"].items():
                logger.info(
                    f"[数据验证] {source}: {stats['count']}/{stats['expected']}条 "
                    f"({stats['coverage']:.0f}%)"
                )

            for alert in coverage["alerts"]:
                logger.warning(f"[数据验证告警] {alert}")

            if validation_result["duplicates"] > 0:
                logger.warning(f"[数据验证] 发现 {validation_result['duplicates']} 组疑似重复公告")

    except Exception as e:
        logger.error(f"[定时任务] 数据验证失败: {e}")


# ============================================================
# 爬虫监控告警
# ============================================================

class CrawlerMonitor:
    """爬虫运行状态监控。"""

    def __init__(self):
        self.stats = {
            "total_runs": 0,
            "success_runs": 0,
            "failure_runs": 0,
            "consecutive_failures": 0,
            "last_run_time": None,
            "last_error": None,
        }

    def record_success(self, count: int = 0):
        self.stats["total_runs"] += 1
        self.stats["success_runs"] += 1
        self.stats["consecutive_failures"] = 0
        self.stats["last_run_time"] = datetime.now().isoformat()

    def record_failure(self, error: str = ""):
        self.stats["total_runs"] += 1
        self.stats["failure_runs"] += 1
        self.stats["consecutive_failures"] += 1
        self.stats["last_error"] = error
        self.stats["last_run_time"] = datetime.now().isoformat()

        if self.stats["consecutive_failures"] >= 3:
            logger.critical(
                f"🚨 爬虫连续失败 {self.stats['consecutive_failures']} 次！"
                f"最后错误: {error}"
            )

    def get_health(self) -> dict:
        return {
            "healthy": self.stats["consecutive_failures"] < 3,
            **self.stats,
        }


crawler_monitor = CrawlerMonitor()

