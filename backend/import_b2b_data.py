"""导入 b2b.10086.cn 采集的广东移动广告招标数据"""
import asyncio, sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, date
from app.db.session import AsyncSessionLocal
from app.models.announcement import Announcement
from app.models.client_relation import Purchaser
from app.models.base import Base
from sqlalchemy import select

async def import_b2b():
    # 确保表已创建
    from app.db.session import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    with open("output/b2b_candidates.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    items = data["items"]
    print(f"📂 {len(items)} 条")
    ad_items = [i for i in items if i.get("is_ad")]
    print(f"🎯 广告类: {len(ad_items)} 条")
    for i in ad_items:
        print(f"   -> {i['title'][:60]}")
    
    # 确保有默认采购方
    async with AsyncSessionLocal() as s:
        existing = await s.execute(select(Purchaser).where(Purchaser.id == 1))
        if not existing.scalar_one_or_none():
            s.add(Purchaser(id=1, name="中国移动通信集团广东有限公司", level="省公司", region="广州"))
            await s.flush()
    
    # 导入广告类
    imported = 0
    async with AsyncSessionLocal() as s:
        with s.no_autoflush:
            for item in items:
                if not item["is_ad"]:
                    continue
                
                # 解析标题获取信息
                title = item["title"]
                
                # 分类到赛道
                category = "广告类"
                if "活动" in title: category = "活动会展类"
                elif "渠道" in title or "触点" in title: category = "渠道营销类"
                elif "新媒体" in title or "运营" in title: category = "新媒体运营类"
                elif "内容" in title or "制作" in title: category = "内容制作类"
                elif "设计" in title: category = "创意设计类"
                elif "投放" in title or "媒介" in title: category = "媒介投放类"
                elif "品牌" in title or "策略" in title: category = "品牌策略类"
                elif "政企" in title or "传播" in title: category = "政企传播类"
                
                # 解析日期
                pub_date = date.today()
                if item.get("date"):
                    try:
                        pub_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
                    except ValueError:
                        pass
                
                # 检查重复
                try:
                    existing = await s.execute(
                        select(Announcement).where(Announcement.title == title)
                    )
                    if existing.scalar_one_or_none():
                        print(f"  ⏭ 重复: {title[:40]}")
                        continue
                except Exception as e:
                    print(f"  ⚠️ 查询失败: {e}")
                    continue
                
                try:
                    ann = Announcement(
                        title=title[:500],
                        source_url=item.get("url") or f"https://b2b.10086.cn/b2b/main/listVendorNotice.html",
                        announce_date=pub_date,
                        province="广东",
                        city="广州",
                        project_category=category,
                        deadline=pub_date,
                        purchaser_id=1,
                        purchaser_level="省公司",
                        procurement_method=item.get("type", "公开招标"),
                        remark=f"来源: b2b.10086.cn | 单位: {item.get('unit', '')}",
                    )
                    s.add(ann)
                    imported += 1
                    print(f"  ✅ [{category}] {title[:60]}...")
                except Exception as e:
                    print(f"  ❌ 插入失败: {e}")
                    import traceback; traceback.print_exc()
        
        try:
            await s.commit()
        except Exception as e:
            print(f"  ❌ 提交失败: {e}")
            import traceback; traceback.print_exc()
    
    print(f"\n✅ 入库 {imported} 条")
    return imported

count = asyncio.run(import_b2b())
