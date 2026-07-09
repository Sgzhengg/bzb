"""
b2b.10086.cn 公告正文下载器

用法:
  python download_b2b_content.py

流程:
  1. 打开浏览器 → 导航到 b2b 搜索页
  2. 自动填入搜索关键词
  3. 等待用户手动点击公告进入详情
  4. 提取详情页正文内容
  5. 保存到 output/ 目录
"""
import asyncio, json, os, re, sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUTPUT_DIR = Path(__file__).parent.parent / "output"
SEARCH_KEYWORD = "中山 客户活动 询比"  # 默认搜索词


async def extract_detail_content(page) -> dict:
    """从 b2b 详情页提取所有文本内容"""
    # 等待详情内容加载
    await asyncio.sleep(3)

    # 尝试获取公告正文容器
    content_selectors = [
        ".notice-content",
        ".detail-content",
        ".bulletin-detail",
        ".el-dialog__body",
        "article",
        ".content",
        "#app main",
    ]

    full_text = ""

    for selector in content_selectors:
        try:
            el = await page.query_selector(selector)
            if el:
                text = await el.inner_text()
                if len(text) > 200:
                    full_text = text
                    break
        except:
            pass

    # 备用：取整个 body
    if not full_text or len(full_text) < 200:
        full_text = await page.evaluate("() => document.body.innerText")

    # 尝试也获取 HTML（用于保留格式）
    html = ""
    for selector in content_selectors[:3]:
        try:
            el = await page.query_selector(selector)
            if el:
                html = await el.inner_html()
                if len(html) > 200:
                    break
        except:
            pass

    # 提取页面标题
    title = await page.title()

    return {
        "url": page.url,
        "title": title,
        "text": full_text,
        "html": html,
        "extracted_at": datetime.now().isoformat(),
    }


async def main():
    print("=" * 60)
    print("  b2b.10086.cn 公告正文下载器")
    print("=" * 60)

    async with async_playwright() as pw:
        # 非 headless 模式，方便用户操作
        browser = await pw.chromium.launch(headless=False, channel="msedge")
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = await ctx.new_page()

        # 导航到搜索页
        print(f"\n📡 打开 b2b 搜索页...")
        await page.goto(
            "https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2#/searchPage",
            wait_until="networkidle", timeout=60000,
        )
        await asyncio.sleep(2)

        # 填入搜索词
        try:
            search_input = page.locator('.cmcc-input').first
            await search_input.wait_for(state="visible", timeout=10000)
            await search_input.fill(SEARCH_KEYWORD)
            print(f"🔍 已填入搜索词: {SEARCH_KEYWORD}")
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"⚠️ 自动搜索失败: {e}")
            print("   请手动在浏览器中搜索")

        results = []
        page_num = 0

        print("\n" + "=" * 60)
        print("📋 操作说明:")
        print("   1. 在浏览器中点击公告标题进入详情页")
        print("   2. 详情页加载完成后，回到终端按 Enter 保存正文")
        print("   3. 按 'n' 继续下一个，按 'q' 退出")
        print("=" * 60 + "\n")

        while True:
            action = input("🔽 在详情页加载完成后按 Enter 保存，n=下一个，q=退出: ").strip().lower()

            if action == "q":
                break

            # 提取当前页面内容
            content = await extract_detail_content(page)
            text_len = len(content["text"])
            print(f"   📄 提取到 {text_len} 字符")

            if text_len > 200:
                # 预览前 500 字符
                print(f"   预览: {content['text'][:300]}...")
                results.append(content)

                # 搜索预算相关信息
                lines = content["text"].split("\n")
                budget_lines = [
                    l.strip() for l in lines
                    if any(k in l for k in [
                        "预算", "限价", "不含税", "含税", "总价",
                        "金额", "万元", "报价", "最高限价", "采购预算",
                    ])
                ]
                if budget_lines:
                    print(f"   💰 发现 {len(budget_lines)} 条预算相关信息:")
                    for bl in budget_lines[:10]:
                        print(f"      >> {bl[:150]}")
            else:
                print("   ⚠️ 内容太少，可能未正确加载详情页")

        # 保存结果
        if results:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            output_path = OUTPUT_DIR / f"b2b_contents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 已保存 {len(results)} 条公告正文到: {output_path}")
        else:
            print("\n⚠️ 未提取到任何内容")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
