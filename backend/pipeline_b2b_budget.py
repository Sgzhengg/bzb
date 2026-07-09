"""
b2b 公告预算抓取管道

流程:
  1. 通过 b2b API 搜索匹配的公告
  2. 打开浏览器让用户手动查看详情页
  3. 从 DOM 提取公告正文
  4. 用 LLM 从正文中提取预算金额
  5. 更新数据库
"""
import asyncio, json, os, sys, logging
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.b2b_proxy import search_announcement, find_best_match
from app.services.llm_budget_extractor import extract_budget_with_llm

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "output"


async def update_db_budget(announcement_id: int, budget_data: dict):
    """将 LLM 提取的预算数据写入数据库"""
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        updates = {"id": announcement_id}
        if budget_data.get("budget_wan") is not None:
            updates["budget"] = budget_data["budget_wan"]
        if budget_data.get("registration_fee") is not None:
            updates["registration_fee"] = budget_data["registration_fee"]
        if budget_data.get("deposit") is not None:
            updates["deposit"] = budget_data["deposit"]
        if budget_data.get("bid_date"):
            updates["bid_date"] = budget_data["bid_date"]

        set_clauses = []
        params = {}
        for key, val in updates.items():
            if key == "id":
                params["id"] = val
            else:
                set_clauses.append(f"{key} = :{key}")
                params[key] = val

        if set_clauses:
            sql = f"UPDATE announcements SET {', '.join(set_clauses)} WHERE id = :id"
            await db.execute(text(sql), params)
            await db.commit()
            logger.info(f"  ✅ 数据库已更新: ID={announcement_id} {set_clauses}")


async def extract_from_page(page) -> str:
    """从当前浏览器页面提取正文"""
    await asyncio.sleep(2)
    # 尝试多个内容容器
    for selector in [
        ".notice-content", ".detail-content", ".bulletin-detail",
        ".el-dialog__body", "article", "main", "#app",
    ]:
        try:
            el = await page.query_selector(selector)
            if el:
                text = await el.inner_text()
                if len(text) > 200:
                    return text
        except:
            pass
    return await page.evaluate("() => document.body.innerText")


async def pipeline():
    print("=" * 60)
    print("  b2b 公告预算抓取管道")
    print("=" * 60)

    # ---- Step 1: API 搜索 ----
    keywords = input("\n🔍 输入搜索关键词 (默认: 中山 客户活动 询比): ").strip()
    if not keywords:
        keywords = "中山 客户活动 询比"

    print(f"搜索: {keywords}")
    items = await search_announcement(keywords, publish_type="PROCUREMENT", page_size=10)

    if not items:
        print("❌ 未找到匹配公告")
        return

    print(f"\n✅ 找到 {len(items)} 条公告:\n")
    for i, item in enumerate(items):
        print(f"  [{i+1}] {item.get('name', '')[:100]}")
        print(f"      日期: {item.get('publishDate', '?')}  截止: {item.get('tenderSaleDeadline', '?')}")

    # ---- Step 2: 浏览器交互提取 ----
    print("\n" + "=" * 60)
    print("📋 请在浏览器中操作:")
    print("   1. 搜索上面列出的公告")
    print("   2. 点击进入详情页")
    print("   3. 详情加载完成后按 Enter")
    print("=" * 60)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, channel="msedge")
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()

        await page.goto(
            "https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2#/searchPage",
            wait_until="networkidle", timeout=60000,
        )
        await asyncio.sleep(2)

        # 填入搜索词
        try:
            search_input = page.locator('.cmcc-input').first
            await search_input.wait_for(state="visible", timeout=10000)
            await search_input.fill(keywords)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)
            print("🔍 已自动搜索，请在浏览器中点击公告进入详情")
        except:
            print("⚠️ 自动搜索失败，请手动搜索")

        # 匹配我们数据库中的公告
        results = []

        while True:
            action = input("\n🔽 详情页加载后按 Enter 提取，q=退出: ").strip().lower()
            if action == "q":
                break

            # 提取内容
            content = await extract_from_page(page)
            print(f"   📄 提取到 {len(content)} 字符")

            if len(content) < 200:
                print("   ⚠️ 内容太少，请确认详情页已加载")
                continue

            # ---- Step 3: LLM 提取 ----
            # 用内容匹配公告
            best_title = ""
            for item in items:
                if any(kw in content for kw in item.get("name", "")[:20].split(" ")):
                    best_title = item.get("name", "")
                    break

            if not best_title:
                best_title = input("   📝 请输入公告标题 (用于匹配): ").strip()

            print(f"   🤖 LLM 分析中...")
            budget_data = await extract_budget_with_llm(best_title, content)

            print(f"   💰 预算: {budget_data.get('budget_wan')} 万")
            print(f"   📝 原文: {budget_data.get('budget_raw', '')[:100]}")
            print(f"   🎯 置信度: {budget_data.get('confidence', 0)}")
            print(f"   📅 投标日期: {budget_data.get('bid_date')}")
            print(f"   💵 报名费: {budget_data.get('registration_fee')} 元")
            print(f"   🔒 保证金: {budget_data.get('deposit')} 元")

            results.append({
                "title": best_title,
                "content": content[:5000],
                "budget_data": budget_data,
            })

            # ---- Step 4: 询问是否入库 ----
            if budget_data.get("confidence", 0) > 0.5:
                save = input("   💾 是否更新数据库? (y/n, 默认y): ").strip().lower()
                if save != "n":
                    # 找到匹配的数据库记录
                    from app.db.session import AsyncSessionLocal
                    from app.models.announcement import Announcement
                    from sqlalchemy import select

                    async with AsyncSessionLocal() as db:
                        result = await db.execute(
                            select(Announcement).where(
                                Announcement.title.contains(best_title[:30])
                            )
                        )
                        ann = result.scalar_one_or_none()
                        if ann:
                            await update_db_budget(ann.id, budget_data)
                        else:
                            ann_id = input("   ⚠️ 未找到匹配数据库记录，请输入 ID: ").strip()
                            if ann_id.isdigit():
                                await update_db_budget(int(ann_id), budget_data)

        await browser.close()

    # ---- Step 5: 保存结果 ----
    if results:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = OUTPUT_DIR / f"b2b_budget_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n✅ 结果已保存: {path}")


if __name__ == "__main__":
    asyncio.run(pipeline())
