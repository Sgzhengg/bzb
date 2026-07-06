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


async def main():
    all_results = []
    
    async with ZhaobiaoCrawler(max_pages=3) as crawler:
        for category, keywords in TRACK_KEYWORDS.items():
            print(f"\n{'='*60}")
            print(f"🎯 赛道: {category}")
            
            for kw in keywords:
                print(f"   🔍 搜索: {kw}")
                try:
                    items = await crawler.search(kw)
                    print(f"   📋 列表: {len(items)} 条广东移动相关")
                    
                    # 抓取详情
                    for item in items:
                        detail = await crawler.fetch_detail(item)
                        if detail:
                            detail.project_category = category
                            all_results.append(detail)
                            print(f"   ✅ {detail.title[:50]}...")
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
    
    print(f"\n{'='*60}")
    print(f"🎉 完成！共 {len(output)} 条")
    print(f"💾 保存到: {outpath}")
    
    # 按赛道统计
    from collections import Counter
    track_counts = Counter(r["project_category"] for r in output)
    for track, count in track_counts.most_common():
        print(f"   {track}: {count} 条")


if __name__ == "__main__":
    asyncio.run(main())
