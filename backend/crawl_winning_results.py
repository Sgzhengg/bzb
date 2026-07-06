"""
用项目爬虫系统采集广东移动广告类中标结果
使用 ZhaobiaoCrawler + 中标相关关键词 + 改进的过滤器
"""
import asyncio, sys, os, json, logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 中标结果专用关键词
WINNING_KEYWORDS = [
    "中国移动通信集团广东 中选",
    "中国移动通信集团广东 中标",
    "中国移动通信集团广东 结果",
    "广东移动 中选候选人",
    "广东移动 中标候选人",
    "广东移动 成交结果",
    "中国移动广东 中选",
    "中国移动广东 中标",
]


async def main():
    from scripts.zhaobiao_crawler import ZhaobiaoCrawler
    from app.services.keyword_filter import filter_advertisement_projects

    all_results = []
    ad_results = []

    async with ZhaobiaoCrawler(max_pages=3) as crawler:
        for kw in WINNING_KEYWORDS:
            logger.info(f"=== 搜索: {kw} ===")
            try:
                items = await crawler.search(kw)
                logger.info(f"  列表: {len(items)} 条广东移动相关(中标类)")

                for item in items[:8]:
                    try:
                        detail = await crawler.fetch_detail(item)
                        if not detail:
                            continue

                        title = detail.title or ""
                        filter_result = filter_advertisement_projects(title, "")

                        result = {
                            "title": title,
                            "source_url": detail.detail_url or "",
                            "purchaser": getattr(detail, "purchaser", "") or "",
                            "publish_date": getattr(detail, "publish_date", "") or "",
                            "notice_type": getattr(detail, "notice_type", "") or "",
                            "location": getattr(detail, "location", "") or "",
                            "search_kw": kw,
                            "is_ad": filter_result.get("is_ad", False),
                            "category": filter_result.get("category", ""),
                            "matched_keywords": filter_result.get("matched_keywords", []),
                        }
                        all_results.append(result)

                        if filter_result.get("is_ad"):
                            ad_results.append(result)
                            logger.info(f"  ✅ [广告] {title[:80]}")
                            logger.info(f"     赛道: {filter_result.get('category','')} | 匹配: {filter_result.get('matched_keywords',[])}")
                        else:
                            logger.info(f"  ⏭️ [跳过] {title[:80]}")

                    except Exception as e:
                        logger.warning(f"  ERR: {str(e)[:80]}")

            except Exception as e:
                logger.error(f"搜索失败: {e}")

    # 保存结果
    output = {
        "crawl_time": datetime.now().isoformat(),
        "source": "zhaobiao.cn (Playwright + keyword_filter)",
        "total_raw": len(all_results),
        "total_ad": len(ad_results),
        "keywords": WINNING_KEYWORDS,
        "items": all_results,
        "ad_items": ad_results,
    }

    output_path = os.path.join(OUTPUT_DIR, "july_2026_winning_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"=== 采集完成: 原始 {len(all_results)} 条, 广告类 {len(ad_results)} 条 ===")
    logger.info(f"结果保存至: {output_path}")

    print("\n" + "=" * 70)
    print(f"✅ 广东移动广告类中标结果 ({len(ad_results)} 条):")
    print("=" * 70)
    for r in ad_results:
        print(f"  [{r.get('category','')}] {r['title'][:90]}")
        print(f"    日期: {r.get('publish_date','')} | 类型: {r.get('notice_type','')}")
        print(f"    URL: {r['source_url']}")
        print()

    return ad_results


if __name__ == "__main__":
    asyncio.run(main())
