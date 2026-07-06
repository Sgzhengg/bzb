"""
用细分赛道关键词搜索 b2b.10086.cn 广东移动广告招标
不使用"广告"关键词，而是用赛道细分词
"""
import asyncio, json, os, sys
from datetime import datetime
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.services.keyword_filter import filter_advertisement_projects

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# 赛道细分搜索词（非"广告"）
SEARCH_TERMS = [
    "品牌策略", "创意设计", "平面设计", "视觉设计",
    "媒介投放", "媒体代理", "线下广告", "广告投放",
    "活动策划", "活动执行", "路演", "发布会", "展会",
    "渠道运营", "门店宣传", "网格营销", "触点运营",
    "视频制作", "宣传片", "物料制作", "内容制作",
    "新媒体运营", "公众号运营", "直播运营", "短视频",
    "客户服务活动", "集团客户", "客户关怀", "客户体验",
    "党群宣传", "党建活动", "工会活动", "企业宣传",
]

async def main():
    from playwright.async_api import async_playwright
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_items = []
    seen_titles = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()

        for term in SEARCH_TERMS:
            term_items = []
            for pg in range(1, 6):
                encoded = quote(term)
                url = (f'https://b2b.10086.cn/b2b/main/listVendorNotice.html'
                       f'?noticeType=2#/searchPage?value={encoded}&noticeType=ALL&current={pg}')

                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    await asyncio.sleep(2)
                except Exception:
                    continue

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
                    and any(k in i['type'] for k in ['候选人', '结果', '中选', '成交', '中标'])
                ]

                new = 0
                for c in candidates:
                    if c['title'] not in seen_titles:
                        seen_titles.add(c['title'])
                        result = filter_advertisement_projects(c['title'])
                        c['is_ad'] = result['is_ad']
                        c['category'] = result.get('category', '')
                        term_items.append(c)
                        new += 1

                if new > 0:
                    print(f'  page {pg}: +{new}')

            all_items.extend(term_items)
            ad_in_term = sum(1 for x in term_items if x['is_ad'])
            if ad_in_term > 0:
                print(f'{term}: {len(term_items)} total, {ad_in_term} ad')
            elif len(term_items) > 0:
                print(f'{term}: {len(term_items)} items (0 ad)')

        await browser.close()

    # 去重 + 保存
    unique = []
    seen = set()
    for item in all_items:
        if item['title'] not in seen:
            seen.add(item['title'])
            unique.append(item)

    path = os.path.join(OUTPUT_DIR, 'b2b_track_search.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'time': str(datetime.now()), 'total': len(unique), 'items': unique},
                  f, ensure_ascii=False, indent=2)

    ad_count = sum(1 for i in unique if i['is_ad'])
    print(f'\n{"="*50}')
    print(f'Total unique: {len(unique)}, Ad-related: {ad_count}')
    print(f'{"="*50}')
    for i in [x for x in unique if x['is_ad']]:
        print(f'  [{i["category"]}] {i["title"][:80]} | {i["date"]}')

    print(f'\nSaved: {path}')

if __name__ == "__main__":
    asyncio.run(main())
