"""
zhaobiao.cn 登录脚本 - 保存持久化会话

用法:
  python login_zhaobiao.py          # 打开浏览器手动登录，登录后按 Enter 保存
  python login_zhaobiao.py --check  # 检查是否已有有效会话
"""

import asyncio, sys, os

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zhaobiao_profile")


async def login():
    """打开浏览器让用户手动登录，保存会话。"""
    from playwright.async_api import async_playwright

    # 确保 profile 目录存在
    os.makedirs(PROFILE_DIR, exist_ok=True)

    async with async_playwright() as pw:
        # 使用持久化上下文——cookie/localStorage 自动保存到 PROFILE_DIR
        context = await pw.chromium.launch_persistent_context(
            PROFILE_DIR,
            channel="msedge",
            headless=False,  # 需要显示浏览器让用户登录
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        # 打开 zhaobiao.cn 登录页
        await page.goto("https://www.zhaobiao.cn/")
        print("\n" + "=" * 60)
        print("请在浏览器中登录 zhaobiao.cn（招标网）")
        print("登录成功后回到此终端，按 Enter 保存会话...")
        print("=" * 60 + "\n")
        input()

        # 检查登录状态
        logged_in = await page.evaluate("""
            () => document.cookie.includes('login') || 
                 document.querySelector('[title=\"退出\"]') !== null ||
                 document.querySelector('.user-info') !== null
        """)

        if logged_in:
            await context.storage_state(path=os.path.join(PROFILE_DIR, "state.json"))
            print("✅ 登录会话已保存到:", PROFILE_DIR)
        else:
            print("⚠️ 未检测到登录状态，但 cookie 已保存，请测试后确认")

        await context.close()


async def check():
    """检查是否已有有效的登录会话。"""
    if not os.path.exists(os.path.join(PROFILE_DIR, "Default")):
        print("❌ 未找到登录会话，请先运行: python login_zhaobiao.py")
        return False

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=True,
        )
        page = await context.new_page()
        await page.goto("https://zb.zhaobiao.cn/free_v_1beee0b803bed7fda7b16bb233a09227.html")
        await page.wait_for_timeout(3000)

        # 检查是否能看到完整内容（非会员才能看到的部分）
        body_text = await page.evaluate("() => document.body.innerText")
        has_full = "预算" in body_text or "采购预算" in body_text or "最高限价" in body_text

        if has_full:
            print("✅ 会话有效，可查看完整公告内容")
        else:
            print("⚠️ 会话可能已过期或未登录，请重新登录")

        await context.close()
        return has_full


if __name__ == "__main__":
    if "--check" in sys.argv:
        asyncio.run(check())
    else:
        asyncio.run(login())
