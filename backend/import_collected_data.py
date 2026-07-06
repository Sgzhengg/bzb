"""
将采集到的广东移动广告类招标公告导入数据库
"""
import asyncio, sys, os, json, logging
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def import_to_db():
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select, text

    # 手动采集到的 2 条广东移动广告类项目（来源可验证）
    items = [
        {
            "title": "中国移动通信集团广东有限公司中山分公司2026年至2028年集团客户活动公开询比采购项目",
            "industry": "中国移动通信集团广东有限公司中山分公司",
            "province": "广东",
            "city": "中山",
            "project_category": "活动策划执行",
            "procurement_method": "公开询比",
            "budget": None,
            "source_url": "https://zb.zhaobiao.cn/free_v_a3d904fb8979505423646c5aa695d292.html",
            "announce_date": "2026-07-01",
            "deadline": "2026-07-15T17:00:00",
            "purchaser_id": 2,  # 中山分公司
            "purchaser_level": "地市公司",
            "remark": "集团客户活动策划执行",
        },
        {
            "title": "中国移动通信集团广东有限公司韶关分公司2026年至2028年集团合作伙伴智慧展示体验参观学习公开询比项目",
            "industry": "中国移动通信集团广东有限公司韶关分公司",
            "province": "广东",
            "city": "韶关",
            "project_category": "活动策划执行",
            "procurement_method": "公开询比",
            "budget": None,
            "source_url": "https://zb.zhaobiao.cn/free_v_1beee0b803bed7fda7b16bb233a09227.html",
            "announce_date": "2026-07-02",
            "deadline": "2026-07-16T17:00:00",
            "purchaser_id": 22,  # 韶关分公司
            "purchaser_level": "地市公司",
            "remark": "智慧展示体验参观学习",
        },
    ]

    async with AsyncSessionLocal() as db:
        # 检查采购方是否存在，不存在则创建
        purchasers_needed = [
            (2, "中国移动通信集团广东有限公司中山分公司", "地市公司", "中山"),
            (22, "中国移动通信集团广东有限公司韶关分公司", "地市公司", "韶关"),
        ]
        from app.models.client_relation import Purchaser

        for pid, pname, plevel, pregion in purchasers_needed:
            existing = await db.get(Purchaser, pid)
            if not existing:
                db.add(Purchaser(id=pid, name=pname, level=plevel, region=pregion))
                logger.info(f"创建采购方: {pname}")
        await db.commit()

        # 导入公告
        from app.models.announcement import Announcement
        inserted = 0

        for item in items:
            # 检查是否已存在（按标题去重）
            result = await db.execute(
                select(Announcement).where(Announcement.title == item["title"])
            )
            if result.scalar_one_or_none():
                logger.info(f"跳过(已存在): {item['title'][:50]}...")
                continue

            ann = Announcement(
                title=item["title"],
                industry=item.get("industry", ""),
                province=item.get("province", ""),
                city=item.get("city", ""),
                project_category=item["project_category"],
                procurement_method=item["procurement_method"],
                budget=item.get("budget"),
                source_url=item.get("source_url", ""),
                announce_date=date.fromisoformat(item["announce_date"])
                if item.get("announce_date") else date.today(),
                deadline=datetime.fromisoformat(item["deadline"])
                if item.get("deadline") else datetime.now(),
                purchaser_id=item.get("purchaser_id", 1),
                purchaser_level=item.get("purchaser_level", ""),
                remark=item.get("remark", ""),
            )
            db.add(ann)
            inserted += 1
            logger.info(f"✅ 导入: {item['title'][:60]}...")

        await db.commit()
        logger.info(f"=== 导入完成: {inserted} 条 ===")

        # 中标结果样例已移除（原云浮数据无法验证来源）
        logger.info("=== 导入完成 ===")


if __name__ == "__main__":
    asyncio.run(import_to_db())
