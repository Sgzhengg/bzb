"""历史中标数据全量采集（登录版）"""
import asyncio, json, os, sys, re, hashlib, logging
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.keyword_filter import filter_advertisement_projects

logger = logging.getLogger(__name__)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

AD_KEYWORDS = ['广告','品牌','宣传','营销','活动','设计','制作','新媒体','视频',
               '渠道','客户服务','触点','运营','传播','创意','文案','策划','物料',
               '拍摄','直播','公众号','视频号','内容','党群','党建','工会','培训',
               '集团客户','展览','论坛','发布会']


async def extract_winner(page, url):
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=10000)
        await asyncio.sleep(1.5)
        return await page.evaluate('''() => {
            const b = document.body?.innerText||'';
            if(b.includes("已删除")) return {winner:'',amount:null,deleted:true};
            let w=''; const pm=[/中标候选[：:\\s]*([^\\n]{2,60})/,/供应商名称[：:\\s]*([^\\n]{2,60})/,/第一中选候选人[：:\\s]*([^\\n]{2,60})/];
            for(const p of pm){const m=b.match(p);if(m){w=m[1].trim();break;}}
            const am=b.match(/中标金额[：:\\s]*([\\d,.]+)\\s*万/);
            return {winner:w,amount:am?parseFloat(am[1].replace(/,/g,'')):null};
        }''')
    except:
        return {"winner":"","amount":None}


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    from playwright.async_api import async_playwright
    import psycopg2

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        ctx = await browser.new_context(viewport={"width":1920,"height":1080})
        page = await ctx.new_page()

        # 登录
        logger.info("登录 zhaobiao.cn...")
        await page.goto('https://user.zhaobiao.cn/login.html', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        await page.click('text=账号登录')
        await asyncio.sleep(0.5)
        await page.fill('input[placeholder="用户名"]', 'gxzhtc')
        await page.fill('input[placeholder="密码"]', 'GXzhtc@20260120')
        print("\n>>> 请查看浏览器窗口，输入验证码后按 Enter <<<")
        input()
        await page.click('button:has-text("登录")')
        await asyncio.sleep(4)

        if 'login' in page.url:
            logger.error("❌ 登录失败")
            return

        logger.info("✅ 登录成功！开始采集...\n")

        # 搜索配置
        search_queries = [
            ("中国移动通信集团广东", "全部"),
        ]

        all_results = []
        seen_urls = set()

        for keyword, desc in search_queries:
            logger.info(f"🔍 搜索: {keyword}")

            # 用主搜索页面
            await page.goto('https://s.zhaobiao.cn/s', wait_until='domcontentloaded')
            await asyncio.sleep(2)
            await page.fill('input[type="text"]', keyword)
            await page.keyboard.press('Enter')
            await asyncio.sleep(4)

            # 扩展到最近6月
            try:
                await page.click('a:has-text("最近6月")')
                await asyncio.sleep(2)
            except:
                pass

            for pg in range(1, 4):
                items = await page.evaluate('''() => {
                    const rows = document.querySelectorAll('table tr');
                    return [...rows].filter(r=>r.querySelectorAll('td').length>=3&&r.querySelector('a[href*="zb.zhaobiao.cn"]'))
                        .map(r=>{const c=r.querySelectorAll('td');const l=r.querySelector('a[href*="zb.zhaobiao.cn"]');
                                 return{type:(c[0]?.textContent||'').trim(),title:(l.textContent||'').trim(),
                                        location:(c[2]?.textContent||'').trim(),date:c.length>3?(c[3]?.textContent||'').trim():'',url:l.href};});
                }''')

                winning = [i for i in items if any(t in i['type'] for t in ['中标公告','成交公告','中选候选人','结果公告'])]
                logger.info(f"  第{pg}页: {len(winning)}中标/{len(items)}总")

                for item in winning:
                    if item['url'] in seen_urls:
                        continue
                    seen_urls.add(item['url'])

                    # 检查是否广告相关
                    filter_result = filter_advertisement_projects(item['title'], '')
                    is_ad = filter_result['is_ad']
                    if not is_ad:
                        # 宽松检查
                        is_ad = any(k in item['title'] for k in AD_KEYWORDS)
                    item['is_ad'] = is_ad
                    item['category'] = filter_result.get('category','')

                    # 访问详情页
                    detail = await extract_winner(page, item['url'])
                    item['winner'] = detail.get('winner','')
                    item['amount'] = detail.get('amount')
                    item['deleted'] = detail.get('deleted', False)

                    all_results.append(item)
                    if item['winner']:
                        logger.info(f"    ✅ {item['winner'][:30]} | {item['title'][:50]}")
                    elif item.get('deleted'):
                        logger.debug(f"    ❌ 已删除: {item['title'][:50]}")

                    await asyncio.sleep(1)

                if pg >= 3:
                    break
                try:
                    await page.evaluate("""()=>{const a=document.querySelector('a:has-text(">")');if(a)a.click();}""")
                    await asyncio.sleep(3)
                except:
                    break

        await browser.close()

    # 保存
    output_path = os.path.join(OUTPUT_DIR, "winning_full.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({"crawl_time": datetime.now().isoformat(), "total": len(all_results), "items": all_results},
                  f, ensure_ascii=False, indent=2)

    # 统计
    ad_items = [i for i in all_results if i.get('is_ad')]
    with_winner = [i for i in all_results if i.get('winner')]
    deleted = [i for i in all_results if i.get('deleted')]

    logger.info(f"\n{'='*50}")
    logger.info(f"📊 采集完成:")
    logger.info(f"  总中标:   {len(all_results)} 条")
    logger.info(f"  有供应商: {len(with_winner)} 条")
    logger.info(f"  广告相关: {len(ad_items)} 条")
    logger.info(f"  已删除:   {len(deleted)} 条")
    logger.info(f"  输出:     {output_path}")

    # 入库
    logger.info(f"\n💾 写入数据库...")
    conn = psycopg2.connect(host='localhost', user='postgres', password='postgres', dbname='biaozhongbao')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS winning_results (
        id SERIAL PRIMARY KEY, title TEXT, winner_name VARCHAR(200), winner_type VARCHAR(50),
        bid_amount NUMERIC(12,2), purchaser VARCHAR(200), project_category VARCHAR(50),
        source_url VARCHAR(1000), publish_date DATE, is_ad BOOLEAN, created_at TIMESTAMP DEFAULT NOW())''')

    inserted = 0
    for item in with_winner:
        cur.execute('SELECT id FROM winning_results WHERE source_url=%s', (item['url'],))
        if cur.fetchone(): continue
        cur.execute('''INSERT INTO winning_results (title, winner_name, bid_amount, purchaser,
                      project_category, source_url, publish_date, is_ad)
                      VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                   (item['title'][:300], item['winner'][:200], item.get('amount'),
                    '广东移动', item.get('category',''), item['url'], item.get('date'), item.get('is_ad',False)))
        inserted += 1
    conn.commit()

    cur.execute('SELECT COUNT(*), COUNT(DISTINCT winner_name) FROM winning_results')
    t, s = cur.fetchone()
    logger.info(f"  入库: {inserted} 条, 总计 {t} 条, {s} 家供应商")

    cur.execute('SELECT winner_name, COUNT(*) c FROM winning_results GROUP BY winner_name ORDER BY c DESC LIMIT 10')
    for row in cur.fetchall():
        logger.info(f"    {row[0][:35]}: {row[1]} 次中标")

    cur.close(); conn.close()
    logger.info(f"\n✅ 全部完成！")


if __name__ == "__main__":
    asyncio.run(main())
