"""登录态中标数据采集 - 使用当前浏览器 session"""
import json, sys, os, asyncio
sys.path.insert(0, 'd:/bzb/backend')
os.chdir('d:/bzb/backend')

async def main():
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        # 连接到已有的浏览器（保持登录态）
        browser = await pw.chromium.connect_over_cdp('http://localhost:9222')
        pages = browser.contexts[0].pages
        page = pages[0] if pages else await browser.contexts[0].new_page()
    else:
        browser = await pw.chromium.launch(headless=False)
        ctx = await browser.new_context()
        page = await ctx.new_page()
        # 登录
        await page.goto('https://user.zhaobiao.cn/login.html', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        await page.click('text=账号登录')
        await page.fill('input[placeholder="用户名"]', 'gxzhtc')
        await page.fill('input[placeholder="密码"]', 'GXzhtc@20260120')
        print('请手动输入验证码后按回车...')
        input()
        await page.click('button:has-text("登录")')
        await page.wait_for_timeout(3000)

    # 搜索中标
    keywords = ['中国移动通信集团广东']
    all_winning = []

    for kw in keywords:
        await page.goto('https://s.zhaobiao.cn/s', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        await page.fill('input[type="text"]', kw)
        await page.keyboard.press('Enter')
        await page.wait_for_timeout(4000)

        # 最近6月
        try:
            await page.click('a:has-text("最近6月")')
            await page.wait_for_timeout(2000)
        except: pass

        for pg in range(1, 4):
            items = await page.evaluate('''() => {
                const rows = document.querySelectorAll('table tr');
                const r = [];
                for (const row of rows) {
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 3) continue;
                    const link = row.querySelector('a[href*="zb.zhaobiao.cn"]');
                    if (!link) continue;
                    const title = (link.textContent || "").trim();
                    if (title.length < 5) continue;
                    r.push({
                        type: (cells[0]?.textContent || "").trim(),
                        title: title,
                        location: (cells[2]?.textContent || "").trim(),
                        date: cells.length>3 ? (cells[3]?.textContent||"").trim() : "",
                        url: link.href
                    });
                }
                return r;
            }''')

            winning = [i for i in items if any(k in (i['type']+i['title']) for k in ['中标','成交','中选','候选','结果'])]
            all_winning.extend(winning)
            print(f'{kw} page {pg}: {len(winning)} winning / {len(items)} total')

            # 翻页
            has_next = await page.evaluate('''() => {
                const next = document.querySelector('a:has-text(">"), a:has-text("下一页"), .next');
                if (next) { next.click(); return true; }
                return false;
            }''')
            if not has_next: break
            await page.wait_for_timeout(2000)

    # 去重
    seen = set()
    unique = []
    for w in all_winning:
        key = w['url']
        if key not in seen:
            seen.add(key)
            unique.append(w)

    with open('output/zhaobiao_winning_loggedin.json', 'w', encoding='utf-8') as f:
        json.dump({'total': len(unique), 'items': unique}, f, ensure_ascii=False, indent=2)

    print(f'\nTotal unique winning: {len(unique)}')
    for w in unique[:10]:
        print(f'  [{w["type"]}] {w["title"][:80]} | {w["location"]}')

asyncio.run(main())
