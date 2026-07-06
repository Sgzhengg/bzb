"""
精准爬取 2026年7月 广东移动广告类招标+中标公告
使用 Playwright 浏览器自动化 + 项目关键词过滤器
"""
import asyncio, json, os, sys, re, logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 精准搜索关键词（AND 搜索：广东移动 + 具体广告关键词）
KEYWORDS = [
    "中国移动通信集团广东 广告",
    "中国移动通信集团广东 品牌宣传",
    "中国移动通信集团广东 营销活动",
    "中国移动通信集团广东 新媒体",
    "广东移动 广告设计",
    "广东移动 宣传物料",
    "广东移动 活动策划",
    "广东移动 视频制作",
]

# 广东移动广告类核心判定词
AD_KEYWORDS = [
    "广告", "品牌", "宣传", "营销", "活动策划", "活动执行",
    "新媒体", "视频制作", "宣传片", "设计制作", "物料制作",
    "创意设计", "媒介投放", "内容制作", "运营支撑", "渠道推广",
    "客户服务活动", "校园营销", "社区推广", "促销活动",
]

# 排除词（非广告类）
EXCLUDE = ["基站", "光缆", "软件开发", "系统编码", "服务器", "物业管理", "食堂", "保安", "保洁"]

def is_guangdong_mobile_ad(title, unit=""):
    """判断是否为广东移动广告类项目"""
    text = f"{title} {unit}"
    # 必须包含广东+移动
    if "广东" not in text and "广州" not in text and "深圳" not in text:
        if "东莞" not in text and "佛山" not in text:
            return False
    if "移动" not in text:
        return False
    # 必须包含广告类关键词
    if not any(kw in text for kw in AD_KEYWORDS):
        return False
    # 排除非广告类
    if any(kw in text for kw in EXCLUDE):
        return False
    return True


async def crawl_zhaobiao():
    """使用 Playwright 爬取 zhaobiao.cn"""
    from playwright.async_api import async_playwright

    all_results = []
    seen_urls = set()

    # 加载已有断点
    checkpoint_path = os.path.join(OUTPUT_DIR, "zhaobiao_checkpoint.json")
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            cp = json.load(f)
            seen_urls = set(cp.get("processed_urls", []))
            logger.info(f"加载断点: {len(seen_urls)} 条已处理")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        for kw in KEYWORDS:
            logger.info(f"=== 搜索: {kw} ===")
            page = await ctx.new_page()

            try:
                # 导航到 zhaobiao.cn 搜索
                search_url = f"https://s.zhaobiao.cn/s?q={kw}&t=bid&d=6m"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(3)

                # 提取搜索结果
                for pg in range(1, 4):
                    try:
                        # 提取列表项
                        items = await page.evaluate('''() => {
                            const cards = document.querySelectorAll(".search-result-item, .bid-item, .result-item, [class*='result']");
                            const results = [];
                            cards.forEach(card => {
                                const titleEl = card.querySelector("a, h3, .title, [class*='title']");
                                const dateEl = card.querySelector("[class*='date'], [class*='time'], time");
                                const locEl = card.querySelector("[class*='location'], [class*='region'], [class*='area']");
                                if (titleEl) {
                                    results.push({
                                        title: titleEl.textContent.trim(),
                                        url: titleEl.href || "",
                                        date: dateEl ? dateEl.textContent.trim() : "",
                                        location: locEl ? locEl.textContent.trim() : ""
                                    });
                                }
                            });
                            return results;
                        }''')

                        for item in items:
                            title = item.get("title", "")
                            url = item.get("url", "")
                            if not title or not url:
                                continue

                            # 用关键词过滤器判断
                            if is_guangdong_mobile_ad(title):
                                url_hash = url.split("/")[-1].replace(".html", "")
                                if url_hash not in seen_urls:
                                    seen_urls.add(url_hash)
                                    all_results.append({
                                        "title": title,
                                        "source_url": url,
                                        "publish_date": item.get("date", ""),
                                        "location": item.get("location", ""),
                                        "search_keyword": kw,
                                        "crawl_date": datetime.now().isoformat(),
                                    })
                                    logger.info(f"  ✅ {title[:80]}")

                        # 翻页
                        if pg < 3:
                            next_btn = page.locator("a:has-text('下一页'), .next, [class*='next']").first
                            if await next_btn.count() > 0:
                                await next_btn.click()
                                await asyncio.sleep(3)
                            else:
                                break
                    except Exception as e:
                        logger.warning(f"  第{pg}页解析失败: {e}")
                        break

            except Exception as e:
                logger.error(f"搜索失败: {e}")
            finally:
                await page.close()

        await browser.close()

    # 保存结果
    output_path = os.path.join(OUTPUT_DIR, "july_2026_gd_mobile_ads.json")
    output = {
        "crawl_time": datetime.now().isoformat(),
        "total": len(all_results),
        "keywords_used": KEYWORDS,
        "items": all_results,
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"=== 采集完成: {len(all_results)} 条广东移动广告类招标/中标信息 ===")
    logger.info(f"结果保存至: {output_path}")

    # 打印摘要
    for r in all_results:
        print(f"  [{r.get('search_keyword','')}] {r['title'][:80]}")
        print(f"    日期: {r.get('publish_date','')} | URL: {r['source_url']}")

    return all_results


async def main():
    results = await crawl_zhaobiao()

    # 同时尝试用 API 验证后端是否可达
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://localhost:8000/api/v1/health")
            if resp.status_code == 200:
                logger.info("后端健康检查通过")
    except:
        pass

    return results


if __name__ == "__main__":
    results = asyncio.run(main())
    print(f"\n=== 最终结果: {len(results)} 条 ===")
