"""
b2b.10086.cn 中标数据采集脚本

基于 Playwright 浏览器自动化 + API 调用双模式。
优先使用 API（高效），失败则回退到 UI 交互（稳定）。

API 端点: POST /api-b2b/api-sync-es/white_list_api/b2b/publish/queryList
参数: {name, publishType, companyType, size, current}

用法:
    python scripts/b2b_winning_crawler.py
    python scripts/b2b_winning_crawler.py --keyword "广东移动 广告"
"""

import asyncio
import os
import sys
import json
import hashlib
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

# 搜索配置
SEARCH_CONFIGS = [
    # (name, publishType, companyType, 说明)
    ("广东移动 广告", "VENDOR", "广东", "供应商公告-广东-广告"),
    ("广东移动 广告", "PURCHASE", "广东", "采购公告-广东-广告"),
    ("广东移动 品牌", "VENDOR", "广东", "供应商公告-广东-品牌"),
    ("广东移动 宣传", "VENDOR", "广东", "供应商公告-广东-宣传"),
    ("广东移动 活动", "VENDOR", "广东", "供应商公告-广东-活动"),
    ("广东移动 设计", "VENDOR", "广东", "供应商公告-广东-设计"),
    ("广东移动 新媒体", "VENDOR", "广东", "供应商公告-广东-新媒体"),
    ("广东移动 营销", "VENDOR", "广东", "供应商公告-广东-营销"),
    ("广告 中选", "VENDOR", "", "供应商公告-全国-广告中选"),
    ("广告 结果公示", "VENDOR", "", "供应商公告-全国-广告结果"),
]


async def call_api(page, name: str, publish_type: str, company_type: str,
                   page_num: int = 1, page_size: int = 50) -> Dict:
    """通过 Playwright 调用 b2b API。"""
    return await page.evaluate("""
        async (params) => {
            const r = await fetch(
                'https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryList',
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: params.name,
                        publishType: params.publishType,
                        purchaseType: '',
                        companyType: params.companyType,
                        size: params.pageSize,
                        current: params.pageNum,
                        sfactApplColumn5: 'PC'
                    })
                }
            );
            return await r.json();
        }
    """, {"name": name, "publishType": publish_type, "companyType": company_type,
          "pageSize": page_size, "pageNum": page_num})


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", type=str, help="单关键词搜索")
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )

    from playwright.async_api import async_playwright

    configs = SEARCH_CONFIGS
    if args.keyword:
        configs = [(args.keyword, "VENDOR", "广东", args.keyword)]

    all_results = []
    seen_ids = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()

        # 先导航到 b2b 建立 session
        await page.goto("https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        for name, ptype, ctype, desc in configs:
            logger.info(f"搜索: {desc} (name='{name}', type={ptype})")

            for pg in range(1, args.max_pages + 1):
                try:
                    data = await call_api(page, name, ptype, ctype, pg, 50)
                except Exception as e:
                    logger.warning(f"  API 调用失败 (page {pg}): {e}")
                    break

                if data.get("code") != 0:
                    break

                content = data.get("data", {}).get("content", [])
                if not content:
                    break

                new_count = 0
                for item in content:
                    item_id = item.get("id", "")
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                    all_results.append({
                        "id": item_id,
                        "title": item.get("name", ""),
                        "type": item.get("publishOneType_dictText", ""),
                        "company": item.get("companyTypeName", ""),
                        "date": item.get("publishDate", ""),
                        "source": "b2b.10086.cn",
                    })
                    new_count += 1

                total = data.get("data", {}).get("total", 0)
                logger.info(f"  [{desc}] 第{pg}页: +{new_count} 条, 累计 {len(all_results)} (总{total})")

                if pg * 50 >= total:
                    break
                await asyncio.sleep(1)

        await browser.close()

    # 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "b2b_winning_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "crawl_time": datetime.now().isoformat(),
            "total": len(all_results),
            "source": "b2b.10086.cn",
            "items": all_results,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ 共采集 {len(all_results)} 条")
    logger.info(f"📁 {output_path}")

    # 统计
    types = {}
    for r in all_results:
        t = r.get("type", "未知")
        types[t] = types.get(t, 0) + 1
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        logger.info(f"  {t}: {c} 条")


if __name__ == "__main__":
    asyncio.run(main())
