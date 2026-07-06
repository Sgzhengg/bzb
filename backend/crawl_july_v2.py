"""
精准爬取 2026年7月 广东移动广告类招标+中标公告
使用 ZhaobiaoCrawler + 项目关键词过滤器
"""
import asyncio, sys, os, json, logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

KEYWORDS = [
    "中国移动通信集团广东 广告",
    "中国移动通信集团广东 品牌",
    "中国移动通信集团广东 宣传",
    "中国移动通信集团广东 营销",
    "广东移动 新媒体",
    "广东移动 广告设计",
    "广东移动 宣传物料",
    "广东移动 视频制作",
]


async def main():
    from scripts.zhaobiao_crawler import ZhaobiaoCrawler
    from app.services.keyword_filter import filter_advertisement_projects

    all_results = []

    async with ZhaobiaoCrawler(max_pages=3) as crawler:
        for kw in KEYWORDS:
            logger.info(f"=== 搜索: {kw} ===")
            try:
                items = await crawler.search(kw)
                logger.info(f"  列表: {len(items)} 条")

                for item in items[:8]:
                    try:
                        detail = await crawler.fetch_detail(item)
                        if detail:
                            result = {
                                "title": detail.title or "",
                                "source_url": detail.detail_url or item.get("url", ""),
                                "purchase_unit": getattr(detail, "purchaser", "") or "",
                                "publish_date": getattr(detail, "publish_date", "") or "",
                                "notice_type": getattr(detail, "notice_type", "") or "",
                                "location": getattr(detail, "location", "") or "",
                                "search_kw": kw,
                            }
                            all_results.append(result)
                            logger.info(f"  OK: {detail.title[:80]}")
                    except Exception as e:
                        logger.warning(f"  ERR: {str(e)[:80]}")
            except Exception as e:
                logger.error(f"搜索失败: {e}")

    # 使用项目关键词过滤器二次过滤
    ad_results = []
    for r in all_results:
        try:
            filtered = filter_advertisement_projects([r])
            if filtered:
                ad_results.append(r)
        except:
            pass

    output = {
        "crawl_time": datetime.now().isoformat(),
        "source": "zhaobiao.cn (Playwright)",
        "total_raw": len(all_results),
        "total_ad": len(ad_results),
        "items": all_results,
        "ad_items": ad_results,
    }

    output_path = os.path.join(OUTPUT_DIR, "july_2026_final.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"=== 完成: 原始 {len(all_results)} 条, 广告类 {len(ad_results)} 条 ===")
    logger.info(f"结果保存至: {output_path}")

    print("\n=== 广东移动广告类招标/中标公告 ===")
    for r in ad_results:
        print(f"  [{r['search_kw']}] {r['title'][:80]}")
        print(f"    日期: {r.get('publish_date','')} | URL: {r['source_url']}")

    return ad_results


if __name__ == "__main__":
    asyncio.run(main())
