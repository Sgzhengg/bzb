"""按8个赛道搜索 b2b.10086.cn 广东移动广告招标"""
import asyncio, json, os, sys

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
TRACKS = ['品牌策略','创意设计','媒介投放','活动执行','渠道营销','内容制作','政企传播','新媒体运营']

ad_kw = ['广告','品牌','宣传','营销','活动','设计','制作','新媒体','视频','渠道',
         '创意','策划','物料','直播','内容','传播','运营','触点','客户服务']

async def main():
    from playwright.async_api import async_playwright
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_items = []
    seen = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width":1920,"height":1080})
        page = await ctx.new_page()

        for track in TRACKS:
            track_items = []
            for pg in range(1, 4):
                kw_enc = ''.join(f'%{hex(ord(c))[2:].upper().zfill(2)}' for c in track)
                url = f'https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2#/searchPage?value={kw_enc}&noticeType=ALL&current={pg}'
                
                await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                await asyncio.sleep(2)

                items = await page.evaluate('''() => {
                    const rows = document.querySelectorAll("table tr");
                    return [...rows]
                        .filter(r => r.querySelectorAll("td").length >= 3)
                        .map(r => {
                            const c = r.querySelectorAll("td");
                            return {
                                unit: (c[0]?.textContent || "").trim(),
                                type: (c[1]?.textContent || "").trim(),
                                title: (c[2]?.textContent || "").trim(),
                                date: c.length > 3 ? (c[3]?.textContent || "").trim() : ""
                            };
                        });
                }''')

                candidates = [
                    i for i in items
                    if '广东' in i['unit']
                    and any(k in i['type'] for k in ['候选人','结果','中选'])
                ]

                for c in candidates:
                    if c['title'] not in seen:
                        seen.add(c['title'])
                        c['is_ad'] = any(k in c['title'] for k in ad_kw)
                        c['track'] = track
                        track_items.append(c)

            all_items.extend(track_items)
            print(f'{track}: {len(track_items)} items (total {len(all_items)})')

        await browser.close()

    path = os.path.join(OUTPUT_DIR, 'b2b_tracks.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'total': len(all_items), 'items': all_items}, f, ensure_ascii=False, indent=2)

    ad_count = sum(1 for i in all_items if i['is_ad'])
    print(f'\n=== Total: {len(all_items)}, Ad-related: {ad_count} ===')
    for i in [x for x in all_items if x['is_ad']]:
        print(f'  [{i["track"]}] {i["title"][:80]} | {i["date"]}')

    print(f'\nSaved: {path}')

if __name__ == "__main__":
    asyncio.run(main())
