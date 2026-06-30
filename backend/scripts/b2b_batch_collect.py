"""b2b.10086.cn 全量中标数据采集 - 无头浏览器版"""
import asyncio, json, os, sys
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

async def main():
    from playwright.async_api import async_playwright
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_candidates = []
    seen = set()
    ad_kw = ['广告','品牌','宣传','营销','活动','设计','制作','新媒体','视频','渠道',
             '客户服务','触点','运营','传播','创意','策划','物料','拍摄','直播','内容',
             '党群','工会','培训','集团客户','展览','论坛','发布会']
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width":1920,"height":1080})
        page = await ctx.new_page()
        
        for pg in range(1, 41):
            url = f'https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2#/searchPage?value=%E5%B9%BF%E4%B8%9C&noticeType=ALL&current={pg}'
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(3)
            
            items = await page.evaluate('''() => {
                const rows = document.querySelectorAll('table tr');
                return [...rows].filter(r => r.querySelectorAll("td").length>=3)
                    .map(r => {const c=r.querySelectorAll("td");
                               return {unit:(c[0]?.textContent||"").trim(),type:(c[1]?.textContent||"").trim(),
                                       title:(c[2]?.textContent||"").trim(),date:c.length>3?(c[3]?.textContent||"").trim():""};});
            }''')
            
            candidates = [i for i in items if (i['type'].find('候选人')>=0 or i['type'].find('结果公示')>=0 or i['type'].find('中选结果')>=0) and '广东' in i['unit']]
            
            new = 0
            for c in candidates:
                if c['title'] not in seen:
                    seen.add(c['title'])
                    c['is_ad'] = any(k in c['title'] for k in ad_kw)
                    all_candidates.append(c)
                    new += 1
            
            print(f'Page {pg}: +{new} candidates, total {len(all_candidates)}')
            if pg > 5 and new == 0: break
        
        await browser.close()
    
    # Stats
    ad_count = sum(1 for c in all_candidates if c['is_ad'])
    print(f'\n=== Results ===')
    print(f'Total candidates/results: {len(all_candidates)}')
    print(f'Advertising-related: {ad_count}')
    
    # Save
    path = os.path.join(OUTPUT_DIR, 'b2b_candidates.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'time': str(datetime.now()), 'total': len(all_candidates), 'ad_count': ad_count, 'items': all_candidates}, f, ensure_ascii=False, indent=2)
    
    print(f'\nAdvertising-related candidates:')
    for c in [c for c in all_candidates if c['is_ad']]:
        print(f'  [{c["type"]}] {c["title"][:80]} | {c["date"]}')
    
    print(f'Saved to: {path}')

asyncio.run(main())
