"""
从中标公告详情页提取中标结果数据

用法:
    python scripts/extract_winning_results.py
    python scripts/extract_winning_results.py --limit 50
"""

import os
import sys
import re
import json
import hashlib
import asyncio
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


async def fetch_detail_winning_info(page, url: str) -> Optional[Dict]:
    """从详情页提取中标供应商信息。"""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(1)
    except Exception:
        return None

    return await page.evaluate("""() => {
        const body = document.body?.innerText || '';
        const result = { winner_name: '', winner_type: '', bid_amount: null, raw_text: body.substring(0, 2000) };

        // 提取中标供应商
        const winnerPatterns = [
            /中标(?:供应商|人|单位)[：:]\\s*([^\\n]{2,40})/,
            /成交(?:供应商|人)[：:]\\s*([^\\n]{2,40})/,
            /中选(?:供应商|人)[：:]\\s*([^\\n]{2,40})/,
            /第一(?:中标|成交|中选)候选(?:人)?[：:]\\s*([^\\n]{2,40})/,
            /(?:中标|成交|中选)(?:供应商|单位|人)名称[：:]\\s*([^\\n]{2,40})/,
            /供应商名称[：:]\\s*([^\\n]{2,40})/,
        ];
        for (const p of winnerPatterns) {
            const m = body.match(p);
            if (m) { result.winner_name = m[1].trim(); break; }
        }

        // 提取中标金额
        const amountPatterns = [
            /中标(?:金额|价|价格)[：:]\\s*(\\d[\\d,.]*)\\s*万/,
            /成交(?:金额|价)[：:]\\s*(\\d[\\d,.]*)\\s*万/,
            /中标金额[：:]\\s*(\\d[\\d,.]*)\\s*元/,
        ];
        for (const p of amountPatterns) {
            const m = body.match(p);
            if (m) {
                let val = parseFloat(m[1].replace(/,/g, ''));
                if (p.source.includes('元') && !p.source.includes('万元')) val /= 10000;
                result.bid_amount = Math.round(val * 100) / 100;
                break;
            }
        }

        // 判断供应商类型
        const name = result.winner_name;
        const headPlayers = ['省广', '因赛', '华扬联众', '蓝色光标', '电通', '奥美', '阳狮', '群邑', '宏盟', '引力传媒', '天下秀', '浙文互联', '分众', '新潮'];
        if (name && headPlayers.some(h => name.includes(h))) {
            result.winner_type = '头部常客';
        } else if (name) {
            result.winner_type = '中小公司';
        }

        return result;
    }""")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200, help="最多处理条数")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # 从数据库读取有 zhaobiao.cn URL 的公告
    import psycopg2
    conn = psycopg2.connect(host="localhost", user="postgres", password="postgres", dbname="biaozhongbao")
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, source_url FROM announcements 
        WHERE source_url LIKE '%zb.zhaobiao.cn%'
        AND (title LIKE '%中标%' OR title LIKE '%成交%' OR title LIKE '%结果%' OR title LIKE '%中选%')
        ORDER BY id
    """)
    items = cur.fetchall()
    cur.close()
    conn.close()

    logger.info(f"找到 {len(items)} 条中标相关公告")
    items = items[:args.limit]

    from playwright.async_api import async_playwright

    results = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()

        for i, (aid, title, url) in enumerate(items):
            if not url:
                continue
            info = await fetch_detail_winning_info(page, url)
            if info and info.get("winner_name"):
                results.append({
                    "announcement_id": aid,
                    "title": title,
                    "source_url": url,
                    "winner_name": info["winner_name"],
                    "winner_type": info.get("winner_type", ""),
                    "bid_amount": info.get("bid_amount"),
                })
                logger.info(f"[{i+1}/{len(items)}] {title[:40]}... → {info['winner_name']} ({info.get('bid_amount','?')}万)")

            if (i + 1) % 5 == 0:
                await asyncio.sleep(1)

        await browser.close()

    # 保存结果
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "winning_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "extract_time": datetime.now().isoformat(),
            "total": len(results),
            "items": results,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ 提取完成！{len(results)}/{len(items)} 条有中标信息")
    logger.info(f"📁 结果: {output_path}")

    # 分类统计
    types = {}
    for r in results:
        t = r.get("winner_type", "未知")
        types[t] = types.get(t, 0) + 1
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        logger.info(f"  {t}: {c} 条")


if __name__ == "__main__":
    asyncio.run(main())
