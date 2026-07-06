"""
按8个偏好赛道采集广东移动广告招标数据
赛道: 品牌策略/创意设计/媒介投放/活动会展/渠道营销/内容制作/政企传播/新媒体运营
"""
import asyncio, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.zhaobiao_crawler import ZhaobiaoCrawler

# 8个偏好赛道 + 对应搜索关键词
TRACK_KEYWORDS = {
    "品牌策略类": ["中国移动通信集团广东 品牌策略", "广东移动 品牌策略"],
    "创意设计类": ["中国移动通信集团广东 创意设计", "广东移动 设计服务"],
    "媒介投放类": ["中国移动通信集团广东 媒介投放", "广东移动 广告投放"],
    "活动会展类": ["中国移动通信集团广东 活动执行", "广东移动 活动策划"],
    "渠道营销类": ["中国移动通信集团广东 渠道营销", "广东移动 营销服务"],
    "内容制作类": ["中国移动通信集团广东 内容制作", "广东移动 视频制作"],
    "政企传播类": ["中国移动通信集团广东 宣传", "广东移动 政企传播"],
    "新媒体运营类": ["中国移动通信集团广东 新媒体", "广东移动 新媒体运营"],
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def _save_to_db(items: list):
    """将采集结果保存到数据库 announcements 表。"""
    from datetime import datetime, date as datetype
    from app.db.session import AsyncSessionLocal
    from app.models.announcement import Announcement
    from sqlalchemy import select

    inserted = 0
    async with AsyncSessionLocal() as db:
        for item in items:
            title = item.get("title", "")
            # 按标题去重
            existing = await db.execute(select(Announcement).where(Announcement.title == title))
            if existing.scalar_one_or_none():
                continue

            # 解析日期
            pub_date_str = item.get("publish_date", "")
            deadline_str = item.get("deadline", "")
            try:
                announce_date = datetype.fromisoformat(pub_date_str[:10]) if pub_date_str else datetype.today()
            except:
                announce_date = datetype.today()
            try:
                deadline = datetime.fromisoformat(deadline_str) if deadline_str else datetime.now()
            except:
                deadline = datetime.now()

            purchaser_name = item.get("purchaser", "")
            purchaser_level = "地市公司" if "分公司" in purchaser_name else "省公司"

            ann = Announcement(
                title=title,
                industry=purchaser_name,
                province="广东",
                city=item.get("location", ""),
                project_category=item.get("project_category", ""),
                procurement_method=item.get("notice_type", "公开询比"),
                budget=float(item.get("budget", 0) or 0),
                source_url=item.get("source_url", ""),
                announce_date=announce_date,
                deadline=deadline,
                bid_date=announce_date,  # 暂用公告日期
                purchaser_level=purchaser_level,
                remark=item.get("notice_type", ""),
            )
            db.add(ann)
            inserted += 1

        await db.commit()
    print(f"   💾 数据库: 新增 {inserted} 条")



async def main():
    all_results = []
    
    from app.services.keyword_filter import filter_advertisement_projects

    async with ZhaobiaoCrawler(max_pages=3) as crawler:
        for category, keywords in TRACK_KEYWORDS.items():
            print(f"\n{'='*60}")
            print(f"🎯 赛道: {category}")
            
            for kw in keywords:
                print(f"   🔍 搜索: {kw}")
                try:
                    items = await crawler.search(kw)
                    print(f"   📋 列表: {len(items)} 条广东移动相关")
                    
                    # 抓取详情 + 二次过滤
                    for item in items:
                        detail = await crawler.fetch_detail(item)
                        if detail:
                            # 使用 keyword_filter 做二次精准过滤
                            filter_result = filter_advertisement_projects(
                                detail.title or "",
                                getattr(detail, 'raw_text', '') or ""
                            )
                            if filter_result.get("is_ad"):
                                detail.project_category = filter_result.get("category") or category
                                all_results.append(detail)
                                print(f"   ✅ {detail.title[:50]}...")
                            else:
                                print(f"   ⏭️ 跳过(非广告): {detail.title[:50]}...")
                except Exception as e:
                    print(f"   ❌ {kw}: {e}")
    
    # 保存
    output = []
    for r in all_results:
        output.append({
            "title": r.title,
            "source_url": r.detail_url or r.source_url or "",
            "notice_type": r.notice_type,
            "publish_date": r.publish_date,
            "location": r.location,
            "purchaser": r.purchaser,
            "project_category": r.project_category,
            "budget": r.budget,
            "deadline": r.deadline,
        })
    
    outpath = os.path.join(OUTPUT_DIR, "gd_mobile_tracks.json")
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump({"total": len(output), "items": output}, f, ensure_ascii=False, indent=2)

    # 同时保存到数据库
    await _save_to_db(output)

    print(f"\n{'='*60}")
    print(f"🎉 完成！共 {len(output)} 条 (已保存JSON + 数据库)")
    print(f"💾 JSON: {outpath}")
    
    # 按赛道统计
    from collections import Counter
    track_counts = Counter(r["project_category"] for r in output)
    for track, count in track_counts.most_common():
        print(f"   {track}: {count} 条")


if __name__ == "__main__":
    asyncio.run(main())
