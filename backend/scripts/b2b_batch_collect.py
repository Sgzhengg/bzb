"""b2b.10086.cn 全量中标数据采集 - 无头浏览器版"""
import asyncio, json, os, sys
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

async def main():
    from playwright.async_api import async_playwright
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_candidates = []
    seen = set()
    ad_kw = ['品牌','策略','定位','规划','创意','设计','视觉','VI','海报','画册',
             '投放','媒介','代理','KOL','活动','路演','展会','发布会','文体','工会',
             '运动会','比赛','竞赛','评选','表彰','庆典','开放日','展览','展厅','展馆',
             '促销','网格','地推','门店','渠道','制作','拍摄','物料','H5','脚本',
             '视频','短视频','宣传','学习','集团客户','政企','新闻','采访','舆情',
             '培训','研修','参访','客户服务','客户关怀','客户体验','论坛','峰会',
             '研讨会','沙龙','座谈会','交流会','推介会','公众号','视频号','直播',
             '代运营','新媒体','运营','广告','营销','推广','传播','策划']
    
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
                               const link = c[2]?.querySelector("a");
                               return {unit:(c[0]?.textContent||"").trim(),type:(c[1]?.textContent||"").trim(),
                                       title:(c[2]?.textContent||"").trim(),date:c.length>3?(c[3]?.textContent||"").trim():"",
                                       url: link ? link.href : ""};});
            }''')
            
            candidates = [i for i in items if (i['type'].find('候选人')>=0 or i['type'].find('结果公示')>=0 or i['type'].find('中选结果')>=0) and '广东' in i['unit']]
            
            new = 0
            for c in candidates:
                if c['title'] not in seen:
                    seen.add(c['title'])
                    c['is_ad'] = any(k in c['title'] for k in ad_kw)
                    # 构造搜索URL：用标题关键词搜索
                    from urllib.parse import quote
                    search_term = c['title'][:30]  # 取前30字作为搜索词
                    c['url'] = f"https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2#/searchPage?value={quote(search_term)}&noticeType=ALL&current=1"
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
