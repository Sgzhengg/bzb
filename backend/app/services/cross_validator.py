"""
数据源交叉验证服务 - 防止漏采的关键机制

功能：
1. 多数据源数量对比
2. 同一项目在不同数据源的重复检测
3. 漏采告警
4. 数据一致性检查
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.announcement import Announcement

logger = logging.getLogger(__name__)


class CrossValidator:
    """数据源交叉验证器"""

    # 各数据源的预期每日公告数量（基于历史统计）
    EXPECTED_DAILY_COUNTS = {
        "zhaobiao": 5,      # 中国招标网：约5条/天
        "gd_zbtb": 2,       # 广东监管网：约2条/天
        "gd_ygp": 3,        # 广东公共资源：约3条/天
        "b2b_10086": 1,     # 移动采购网：约1条/天
    }

    # 数据源优先级（用于去重时选择保留哪个）
    SOURCE_PRIORITY = {
        "b2b_10086": 100,   # 官方最权威
        "gd_zbtb": 90,      # 政府平台
        "gd_ygp": 80,       # 公共资源
        "zhaobiao": 70,     # 第三方平台
    }

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def validate_daily_coverage(self, date: datetime.date) -> Dict:
        """
        验证指定日期的数据覆盖情况

        返回：{
            "date": "2026-07-06",
            "total_count": 10,
            "by_source": {...},
            "missing_sources": [...],
            "alerts": [...]
        }
        """
        date_str = date.isoformat()

        # 查询各数据源的公告数量
        by_source = {}
        total_count = 0

        # 通过 source_url 域名识别数据源
        source_domains = {
            "zhaobiao": ["zhaobiao.cn"],
            "gd_zbtb": ["zbtb.gd.gov.cn"],
            "gd_ygp": ["ygp.gdzwfw.gov.cn"],
            "b2b_10086": ["b2b.10086.cn"],
        }

        for source, domains in source_domains.items():
            count = await self._count_by_source_and_date(domains, date)
            by_source[source] = {
                "count": count,
                "expected": self.EXPECTED_DAILY_COUNTS.get(source, 0),
                "coverage": count / max(self.EXPECTED_DAILY_COUNTS.get(source, 1), 1) * 100
            }
            total_count += count

        # 检测遗漏的数据源
        missing_sources = []
        for source, expected in self.EXPECTED_DAILY_COUNTS.items():
            actual = by_source.get(source, {}).get("count", 0)
            if actual == 0 and expected > 0:
                missing_sources.append(source)

        # 生成告警
        alerts = []
        for source in missing_sources:
            alerts.append(f"⚠️ {self._source_name(source)} 今日无数据采集（预期约{self.EXPECTED_DAILY_COUNTS[source]}条）")

        for source, stats in by_source.items():
            if stats["coverage"] < 50 and stats["expected"] > 0:
                alerts.append(f"⚠️ {self._source_name(source)} 采集量偏低（{stats['count']}/{stats['expected']}条，覆盖率{stats['coverage']:.0f}%）")

        return {
            "date": date_str,
            "total_count": total_count,
            "by_source": by_source,
            "missing_sources": missing_sources,
            "alerts": alerts,
        }

    async def detect_duplicates_by_similarity(self, days: int = 7) -> List[Dict]:
        """
        基于标题相似度检测重复公告

        Args:
            days: 检查最近几天的数据

        Returns:
            重复公告列表，每组包含相似的项目
        """
        from difflib import SequenceMatcher

        since_date = datetime.now() - timedelta(days=days)

        # 获取最近的公告
        result = await self.db.execute(
            select(Announcement.id, Announcement.title, Announcement.source_url)
            .where(Announcement.announce_date >= since_date)
            .order_by(Announcement.announce_date.desc())
        )
        announcements = result.all()

        # 检测相似标题
        duplicates = []
        processed = set()

        for i, ann1 in enumerate(announcements):
            if ann1.id in processed:
                continue

            similar_items = [ann1]

            for j, ann2 in enumerate(announcements[i+1:], i+1):
                if ann2.id in processed:
                    continue

                # 计算标题相似度
                similarity = SequenceMatcher(
                    None, ann1.title, ann2.title
                ).ratio()

                # 相似度 > 85% 视为重复
                if similarity > 0.85:
                    similar_items.append(ann2)
                    processed.add(ann2.id)

            # 如果找到重复
            if len(similar_items) > 1:
                # 按数据源优先级排序
                similar_items.sort(
                    key=lambda x: self._get_source_priority(x.source_url),
                    reverse=True
                )

                duplicates.append({
                    "count": len(similar_items),
                    "items": [
                        {
                            "id": item.id,
                            "title": item.title,
                            "url": item.source_url,
                            "priority": self._get_source_priority(item.source_url),
                        }
                        for item in similar_items
                    ],
                    "recommendation": f"保留 {similar_items[0].source_url}，删除其他"
                })

            processed.add(ann1.id)

        return duplicates

    async def compare_sources(self, date: datetime.date) -> Dict:
        """
        比较不同数据源在同一日期的数据差异

        用于发现数据源间的数据不一致
        """
        since_date = datetime.combine(date, datetime.min.time())
        until_date = datetime.combine(date, datetime.max.time())

        # 获取该日期所有公告
        result = await self.db.execute(
            select(Announcement)
            .where(and_(
                Announcement.announce_date == date,
            ))
        )
        announcements = result.scalars().all()

        # 按数据源分组
        by_domain = {
            "zhaobiao": [],
            "gd_zbtb": [],
            "gd_ygp": [],
            "b2b_10086": [],
        }

        source_domains = {
            "zhaobiao": ["zhaobiao.cn"],
            "gd_zbtb": ["zbtb.gd.gov.cn"],
            "gd_ygp": ["ygp.gdzwfw.gov.cn"],
            "b2b_10086": ["b2b.10086.cn"],
        }

        for ann in announcements:
            url = ann.source_url or ""
            for source, domains in source_domains.items():
                if any(domain in url for domain in domains):
                    by_domain[source].append(ann.title)
                    break

        # 检查标题相似度（跨数据源）
        cross_source_similar = []
        for source1, titles1 in by_domain.items():
            for source2, titles2 in by_domain.items():
                if source1 >= source2:  # 避免重复比较
                    continue

                for t1 in titles1:
                    for t2 in titles2:
                        from difflib import SequenceMatcher
                        sim = SequenceMatcher(None, t1, t2).ratio()
                        if sim > 0.9:  # 90%相似度
                            cross_source_similar.append({
                                "source1": source1,
                                "source2": source2,
                                "title1": t1,
                                "title2": t2,
                                "similarity": f"{sim*100:.1f}%"
                            })

        return {
            "date": date.isoformat(),
            "counts_by_source": {k: len(v) for k, v in by_domain.items()},
            "cross_source_similar": cross_source_similar,
        }

    async def validate_weekly_trend(self, weeks: int = 4) -> Dict:
        """
        验证最近几周的采集趋势

        检测是否有异常下降（可能漏采）
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(weeks=weeks)

        # 按周统计
        weekly_stats = []

        for week in range(weeks):
            week_start = start_date + timedelta(weeks=week)
            week_end = week_start + timedelta(days=6)

            result = await self.db.execute(
                select(func.count(Announcement.id))
                .where(and_(
                    Announcement.announce_date >= week_start,
                    Announcement.announce_date <= week_end
                ))
            )
            count = result.scalar() or 0

            weekly_stats.append({
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "count": count,
            })

        # 检测异常下降
        alerts = []
        if len(weekly_stats) >= 2:
            # 与上周比较
            current = weekly_stats[-1]["count"]
            previous = weekly_stats[-2]["count"]

            if previous > 0 and current < previous * 0.5:  # 下降超过50%
                alerts.append(f"⚠️ 本周采集量大幅下降：{current}条 vs 上周{previous}条")

        return {
            "period": f"最近{weeks}周",
            "weekly_stats": weekly_stats,
            "alerts": alerts,
        }

    async def _count_by_source_and_date(
        self, domains: List[str], date: datetime.date
    ) -> int:
        """统计指定数据源在指定日期的公告数量"""
        # 构建条件
        conditions = [
            Announcement.announce_date == date
        ]

        # 添加域名条件
        if domains:
            domain_conditions = []
            for domain in domains:
                domain_conditions.append(Announcement.source_url.like(f"%{domain}%"))
            # OR 条件
            from sqlalchemy import or_
            conditions.append(or_(*domain_conditions))

        result = await self.db.execute(
            select(func.count(Announcement.id))
            .where(and_(*conditions))
        )
        return result.scalar() or 0

    def _get_source_priority(self, url: str) -> int:
        """根据 URL 获取数据源优先级"""
        if not url:
            return 0

        for source, priority in self.SOURCE_PRIORITY.items():
            if source == "b2b_10086" and "b2b.10086.cn" in url:
                return priority
            elif source == "gd_zbtb" and "zbtb.gd.gov.cn" in url:
                return priority
            elif source == "gd_ygp" and "ygp.gdzwfw.gov.cn" in url:
                return priority
            elif source == "zhaobiao" and "zhaobiao.cn" in url:
                return priority
        return 50  # 未知数据源

    def _source_name(self, source: str) -> str:
        """获取数据源中文名称"""
        names = {
            "zhaobiao": "中国招标网",
            "gd_zbtb": "广东监管网",
            "gd_ygp": "广东公共资源",
            "b2b_10086": "移动采购网",
        }
        return names.get(source, source)


# ============================================================
# 定时验证任务
# ============================================================

async def run_daily_validation(db_session: AsyncSession):
    """
    执行每日数据验证任务

    应在调度器中配置，每日23:59执行
    """
    validator = CrossValidator(db_session)

    today = datetime.now().date()
    logger.info(f"开始执行每日数据验证: {today}")

    # 1. 验证今日覆盖情况
    coverage = await validator.validate_daily_coverage(today)
    logger.info(f"今日采集统计: {coverage['total_count']}条公告")
    for alert in coverage["alerts"]:
        logger.warning(alert)

    # 2. 检测最近7天的重复
    duplicates = await validator.detect_duplicates_by_similarity(days=7)
    if duplicates:
        logger.warning(f"发现 {len(duplicates)} 组疑似重复公告")
        for dup in duplicates[:3]:  # 只记录前3组
            logger.warning(f"  重复组: {dup['recommendation']}")

    # 3. 验证周趋势
    weekly = await validator.validate_weekly_trend(weeks=4)
    for alert in weekly["alerts"]:
        logger.warning(alert)

    return {
        "coverage": coverage,
        "duplicates": len(duplicates),
        "weekly": weekly,
    }
