"""
登录 zhaobiao.cn 后自动抓取公告预算金额

用法:
  python scrape_budget.py

流程:
  1. 打开浏览器 → 检测是否已登录
  2. 如未登录 → 等待用户手动登录（含验证码）
  3. 检测到登录后 → 自动抓取每条公告的预算/报名费/保证金
  4. 更新 SQLite 数据库
"""
import asyncio, os, re, sqlite3, time
from playwright.async_api import async_playwright

PROFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zhaobiao_profile")
os.makedirs(PROFILE, exist_ok=True)

ANNOUNCEMENTS = {
    3: ("韶关", "https://zb.zhaobiao.cn/free_v_1beee0b803bed7fda7b16bb233a09227.html"),
    2: ("中山", "https://zb.zhaobiao.cn/free_v_a3d904fb8979505423646c5aa695d292.html"),
}


def extract_wan(text: str) -> float | None:
    """从文本提取万元数。如 '预算金额：50万元' → 50.0"""
    m = re.search(r"([\d,.]+)\s*(?:万|万元)", text)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"([\d,.]+)\s*元", text)
    if m:
        return float(m.group(1).replace(",", "")) / 10000
    return None


async def check_logged_in(page) -> bool:
    """通过访问详情页检查是否已登录"""
    await page.goto("https://zb.zhaobiao.cn/free_v_1beee0b803bed7fda7b16bb233a09227.html")
    await page.wait_for_timeout(5000)
    body = await page.evaluate("() => document.body.innerText")
    # 如果页面包含"仅对会员开放"说明未登录
    return "仅对会员开放" not in body and len(body) > 500


async def wait_for_login(page):
    """等待用户在浏览器中完成登录"""
    print("\n" + "=" * 55)
    print("🔐 请在浏览器中登录 zhaobiao.cn")
    print("   完成验证码 + 输入账号密码后，系统自动检测")
    print("=" * 55)

    await page.goto("https://www.zhaobiao.cn/")
    await page.wait_for_timeout(3000)

    # 每 5 秒检测一次，最多等 3 分钟
    for i in range(36):
        await page.wait_for_timeout(5000)
        try:
            body = await page.evaluate("() => document.body.innerText")
            if "退出" in body or "会员中心" in body:
                print("✅ 检测到登录成功！")
                await page.context.storage_state(
                    path=os.path.join(PROFILE, "state.json")
                )
                return True
        except:
            pass
        if i % 6 == 5:
            print(f"   ⏳ 等待登录中... ({ (i+1)*5 }秒)")
    return False


async def scrape_page(page, url: str) -> dict:
    """抓取单个公告页面的金额信息"""
    await page.goto(url)
    await page.wait_for_timeout(8000)

    body = await page.evaluate("() => document.body.innerText")

    result = {"budget": None, "fee": None, "deposit": None, "lines": []}

    for line in body.split("\n"):
        s = line.strip()
        if not s or len(s) > 300:
            continue

        if any(kw in s for kw in ["预算", "限价", "报名费", "保证金", "标书"]):
            result["lines"].append(s[:150])

            val = extract_wan(s)
            if val is None:
                continue

            if "报名费" in s or "标书" in s:
                result["fee"] = val * 10000  # 万元→元
            elif "保证金" in s:
                result["deposit"] = val * 10000
            elif ("预算" in s or "限价" in s) and result["budget"] is None:
                result["budget"] = val

    return result


async def main():
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            PROFILE,
            headless=False,
            viewport={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()

        # 1. 检测登录状态
        print("🔍 检测登录状态...")
        logged_in = await check_logged_in(page)
        if not logged_in:
            logged_in = await wait_for_login(page)

        if not logged_in:
            print("❌ 登录超时，请重新运行")
            await ctx.close()
            return

        # 2. 抓取公告详情
        db = sqlite3.connect("biaozhongbao.db")
        cur = db.cursor()

        for ann_id, (name, url) in ANNOUNCEMENTS.items():
            print(f"\n📄 抓取: {name} (ID={ann_id})")
            result = await scrape_page(page, url)

            print(f"   相关行: {len(result['lines'])} 条")
            for line in result["lines"]:
                print(f"   → {line}")

            # 更新数据库
            updates = []
            if result["budget"] is not None:
                updates.append(("budget", result["budget"]))
                print(f"   💰 预算: {result['budget']} 万元")
            if result["fee"] is not None:
                updates.append(("registration_fee", result["fee"]))
                print(f"   📋 报名费: {result['fee']} 元")
            if result["deposit"] is not None:
                updates.append(("deposit", result["deposit"]))
                print(f"   🔒 保证金: {result['deposit']} 元")

            for col, val in updates:
                cur.execute(
                    f"UPDATE announcements SET {col} = ? WHERE id = ?",
                    (val, ann_id),
                )

        db.commit()

        # 3. 输出最终结果
        print("\n" + "=" * 55)
        print("📊 数据库更新结果:")
        cur.execute(
            "SELECT id, budget, registration_fee, deposit, substr(title,1,45) FROM announcements"
        )
        for r in cur.fetchall():
            print(f"  ID={r[0]} | 预算={r[1]}万 | 报名费={r[2]}元 | 保证金={r[3]}元 | {r[4]}")

        db.close()
        await ctx.close()
        print("\n✅ 完成！")


if __name__ == "__main__":
    asyncio.run(main())
