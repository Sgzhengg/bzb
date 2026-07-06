"""快速采集中标数据"""
import asyncio, sys, os, json
sys.path.insert(0, '.')
os.chdir('d:/bzb/backend')
from scripts.zhaobiao_crawler import ZhaobiaoCrawler

async def run():
    keywords = [
        '中国移动通信集团广东 广告',
        '中国移动通信集团广东 品牌',
        '中国移动通信集团广东 宣传',
        '中国移动通信集团广东 活动',
        '中国移动通信集团广东 新媒体',
        '中国移动通信集团广东 设计',
    ]
    all_items = []

    async with ZhaobiaoCrawler(max_pages=2) as c:
        for kw in keywords:
            items = await c.search(kw)
            for it in items:
                it['search_kw'] = kw
            all_items.extend(items)
            print(f'{kw}: {len(items)} items')

    winning = [it for it in all_items if any(k in str(it.get('title','')) for k in ['中标','成交','结果','中选','候选'])]
    print(f'\nTotal: {len(all_items)}, Winning-related: {len(winning)}')

    for w in winning[:15]:
        print(f'  [{w.get("notice_type","")}] {w.get("title","")[:80]} | {w.get("location","")}')

    with open('output/zhaobiao_winning.json', 'w', encoding='utf-8') as f:
        json.dump({'total': len(all_items), 'winning': len(winning), 'items': [{k: str(v)[:200] for k,v in it.items()} for it in winning]}, f, ensure_ascii=False, indent=2)

asyncio.run(run())
