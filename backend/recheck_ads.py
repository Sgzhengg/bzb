"""
用 keyword_filter.py 的 KEEP_KEYWORDS 重新筛选 b2b 数据和数据库记录
"""
import asyncio, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.services.keyword_filter import filter_advertisement_projects

async def main():
    # 1. 重新筛选 b2b_candidates.json
    with open("output/b2b_candidates.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print("=== b2b.10086.cn 数据用 keyword_filter 重新筛选 ===")
    ad_count = 0
    for item in data["items"]:
        title = item["title"]
        result = filter_advertisement_projects(title)
        if result["is_ad"]:
            ad_count += 1
            print(f"  ✅ [{result.get('category','?')}] {title[:80]} | {item.get('date','')}")
    
    print(f"\n  广告类: {ad_count}/{len(data['items'])} (原来 2 条)\n")
    
    # 2. 重新筛选数据库中的记录
    from app.db.session import AsyncSessionLocal
    from app.models.announcement import Announcement
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Announcement))
        db_items = r.scalars().all()
    
    print(f"=== 数据库 {len(db_items)} 条用 keyword_filter 重新筛选 ===")
    db_ad = 0
    for item in db_items:
        result = filter_advertisement_projects(item.title)
        if result["is_ad"]:
            db_ad += 1
            print(f"  ✅ [{result.get('category','?')}] {item.title[:80]}")
    
    print(f"\n  数据库广告类: {db_ad}/{len(db_items)}")

asyncio.run(main())
