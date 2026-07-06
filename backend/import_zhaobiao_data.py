"""
将爬取的 zhaobiao.cn 数据导入数据库
筛选条件：广东 + 移动/广告 相关
"""
import asyncio
import json
import re
import sys
import os
from datetime import datetime, date

# 添加 backend 到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine, AsyncSessionLocal
from app.models.announcement import Announcement
from app.models.client_relation import Purchaser
from app.models.base import Base
from sqlalchemy import select


JSON_FILE = os.path.join(os.path.dirname(__file__), "..", "output", "zhaobiao_gd_mobile_ads.json")

# 必须包含的关键词（广东移动相关）
MUST_KEYWORDS = ["广东", "移动", "广告"]
# 排除关键词（明确不相关）
EXCLUDE_KEYWORDS = ["加油站", "成品油", "油田", "闲置房屋", "摊位", "商场", "产权交易"]


def is_relevant(item: dict) -> bool:
    """判断是否属于广东移动广告类招标"""
    title = item.get("title", "")
    raw = item.get("raw_text", "")

    # 必须包含"广东"和"移动"
    if "广东" not in title and "广东" not in raw:
        return False

    # 排除无关
    for kw in EXCLUDE_KEYWORDS:
        if kw in title or kw in raw:
            return False

    # 类型过滤：优先招标公告/中标公告
    if "产权交易" in raw and "广东" not in raw.split("\t")[2] if "\t" in raw else True:
        return False

    return True


def parse_raw_text(raw: str) -> dict:
    """解析raw_text字段"""
    parts = raw.split("\t")
    result = {}
    
    if len(parts) >= 4:
        result["procurement_method"] = parts[0].strip()
        result["province"] = parts[-2].strip() if len(parts) >= 3 else ""
        result["publish_date"] = parts[-1].strip() if len(parts) >= 4 else ""
    
    return result


async def import_data():
    # 确保表已创建
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 读取 JSON
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📂 读取 {len(data)} 条原始数据")
    
    # 筛选
    relevant = [item for item in data if is_relevant(item)]
    print(f"🔍 筛选后 {len(relevant)} 条相关数据")
    
    # 导入
    imported = 0
    async with AsyncSessionLocal() as session:
        # 确保有默认采购方
        existing_purchaser = await session.execute(
            select(Purchaser).where(Purchaser.id == 1)
        )
        if not existing_purchaser.scalar_one_or_none():
            default_purchaser = Purchaser(
                id=1,
                name="中国移动通信集团广东有限公司",
                level="省公司",
                region="广州",
            )
            session.add(default_purchaser)
            await session.flush()
        
        with session.no_autoflush:
            for item in relevant:
                parsed = parse_raw_text(item.get("raw_text", ""))
                
                # 解析日期
                pub_date = parsed.get("publish_date", "")
                if pub_date:
                    try:
                        pub_date = datetime.strptime(pub_date, "%Y-%m-%d").date()
                    except ValueError:
                        pub_date = date.today()
                else:
                    pub_date = date.today()
                
                # 检查是否已存在
                existing = await session.execute(
                    select(Announcement).where(Announcement.source_url == item.get("source_url"))
                )
                if existing.scalar_one_or_none():
                    continue
                
                announcement = Announcement(
                    title=item.get("title", "")[:500],
                    source_url=item.get("source_url", ""),
                    announce_date=pub_date,
                    province=parsed.get("province", ""),
                    procurement_method=parsed.get("procurement_method", ""),
                    project_category="广告类",
                    deadline=pub_date,
                    purchaser_id=1,
                    purchaser_level="省公司",
                    remark=item.get("raw_text", "")[:1000],
                )
                session.add(announcement)
                imported += 1
                
                # 每50条flush一次
                if imported % 50 == 0:
                    await session.flush()
        
        await session.commit()
    
    print(f"✅ 成功导入 {imported} 条到数据库")
    return imported


if __name__ == "__main__":
    count = asyncio.run(import_data())
    print(f"\n总计导入: {count} 条")
