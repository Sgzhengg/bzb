"""
标中宝 - zhaobiao.cn 中标数据采集（登录版）
使用已登录浏览器 session 采集广东移动广告类中标数据

用法:
    python scripts/collect_winning_results.py
    python scripts/collect_winning_results.py --max-pages 5 --save-db
"""
import asyncio, json, os, sys, re, argparse, logging, hashlib
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

# 搜索配置
SEARCH_KEYWORDS = [
    "中国移动通信集团广东",
]

AD_KEYWORDS = ['广告','品牌','宣传','营销','活动','设计','制作','新媒体',
               '视频','渠道','客户服务','触点','运营','传播','创意','文案',
               '策划','物料','拍摄','直播','公众号','视频号','内容',
               '党群','党建','工会','培训','集团客户','展览','论坛','发布会']

WINNING_TYPES = ['中标公告','成交公告','结果公告','中选候选人公示','中标候选人公示']


async def extract_winner(page, url: str) -> Dict:
    """访问详情页提取中标供应商和金额"""
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=12000)
        await asyncio.sleep(1.5)
        return await page.evaluate('''() => {
            const body = document.body?.innerText || '';
            let winner = '', amount = '';
            const wm = body.match(/中标候选[：:\\s]*([^\\n]{2,60})/) || body.match(/供应商名称[：:\\s]*([^\\n]{2,60})/);
            if (wm) winner = wm[1].trim();
            const am = body.match(/中标金额[：:\\s]*([\\d,.]+)\\s*万/) || body.match(/预算金额[：:\\s]*([\\d,.]+)\\s*万/);
            if (am) { let v = parseFloat(am[1].replace(/,/g,'')); amount = Math.round(v*100)/100; }
            return { winner, amount, textLen: body.length };
        }''')
    except Exception as e:
        return {"error": str(e)}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    from playwright.async_api import async_playwright
    import psycopg2

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_results = []
    seen_urls = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()

        # 登录
        logger.info("登录 zhaobiao.cn...")
        await page.goto('https://user.zhaobiao.cn/login.html', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        await page.click('text=账号登录')
        await asyncio.sleep(0.5)
        await page.fill('input[placeholder="用户名"]', 'gxzhtc')
        await page.fill('input[placeholder="密码"]', 'GXzhtc@20260120')
        print("\n请查看浏览器窗口，手动输入验证码后按 Enter 继续...")
        input()
        await page.click('button:has-text("登录")')
        await asyncio.sleep(3)
        
        if 'login' in page.url:
            logger.error("登录失败，请重试")
            return

        logger.info("登录成功！开始采集...")

        for kw in SEARCH_KEYWORDS:
            logger.info(f"\n搜索: {kw}")
            await page.goto('https://s.zhaobiao.cn/s', wait_until='domcontentloaded')
            await asyncio.sleep(2)
            await page.fill('input[type="text"]', kw)
            await page.keyboard.press('Enter')
            await asyncio.sleep(4)

            try:
                await page.click('a:has-text("最近6月")')
                await asyncio.sleep(2)
            except:
                pass

            for pg in range(1, args.max_pages + 1):
                items = await page.evaluate('''() => {
                    const rows = document.querySelectorAll('table tr');
                    return [...rows].filter(r => r.querySelectorAll('td').length>=3 && r.querySelector('a[href*="zb.zhaobiao.cn"]'))
                        .map(r => {
                            const c = r.querySelectorAll('td');
                            const link = r.querySelector('a[href*="zb.zhaobiao.cn"]');
                            return {type:(c[0]?.textContent||'').trim(), title:(link.textContent||'').trim(),
                                    location:(c[2]?.textContent||'').trim(), date:c.length>3?(c[3]?.textContent||'').trim():'', url:link.href};
                        });
                }''')

                winning = [i for i in items if any(t in i['type'] for t in WINNING_TYPES)]
                logger.info(f"  第{pg}页: {len(winning)}条中标 / {len(items)}条")

                for item in winning:
                    if item['url'] in seen_urls:
                        continue
                    seen_urls.add(item['url'])

                    # 访问详情页提取供应商
                    detail = await extract_winner(page, item['url'])
                    item['winner'] = detail.get('winner', '')
                    item['amount'] = detail.get('amount')
                    all_results.append(item)

                    if item['winner']:
                        logger.info(f"    ✅ {item['winner'][:25]} → {item['title'][:40]}")

                    await asyncio.sleep(1)

                # 翻页
                if pg < args.max_pages:
                    try:
                        await page.evaluate("""()=>{const a=document.querySelector('a:has-text(">")'); if(a)a.click();}""")
                        await asyncio.sleep(3)
                    except:
                        break

        await browser.close()

    # 保存结果
    output_path = os.path.join(OUTPUT_DIR, "winning_results_login.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({"crawl_time": datetime.now().isoformat(), "total": len(all_results),
                   "items": all_results}, f, ensure_ascii=False, indent=2)

    # 统计
    ad_items = [i for i in all_results if any(k in i['title'] for k in AD_KEYWORDS)]
    with_winner = [i for i in all_results if i.get('winner')]

    logger.info(f"\n{'='*50}")
    logger.info(f"采集完成！")
    logger.info(f"  中标结果: {len(all_results)} 条")
    logger.info(f"  含供应商: {len(with_winner)} 条")
    logger.info(f"  广告相关: {len(ad_items)} 条")
    logger.info(f"  输出文件: {output_path}")

    for w in sorted(ad_items, key=lambda x: x.get('amount') or 0, reverse=True)[:10]:
        logger.info(f"  [{w['type']}] {w.get('winner','?')[:20]} | {w.get('amount','?')}万 | {w['title'][:50]}")


if __name__ == "__main__":
    asyncio.run(main())
