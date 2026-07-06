"""手动登录 zhaobiao.cn 后自动抓取公告详情"""
import asyncio, os, json
from playwright.async_api import async_playwright

PROFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zhaobiao_profile")
os.makedirs(PROFILE, exist_ok=True)

URLS = {
    "韶关": "https://zb.zhaobiao.cn/free_v_1beee0b803bed7fda7b16bb233a09227.html",
    "中山": "https://zb.zhaobiao.cn/free_v_a3d904fb8979505423646c5aa695d292.html",
}


async def main():
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            PROFILE, headless=False, viewport={"width": 1280, "height": 900}
        )
        page = await ctx.new_page()
        await page.goto("https://www.zhaobiao.cn/")
        await page.wait_for_timeout(3000)

        body = await page.evaluate("() => document.body.innerText")
        if "exit" not in body.lower() and "logout" not in body.lower():
            print("=" * 50)
            print("Please login to zhaobiao.cn in the browser")
            print("Account: gxzhtc")
            print("Password: GXzhtc@20260120")
            print("After login, press Enter in terminal...")
            print("=" * 50)
            input()

        await ctx.storage_state(path=os.path.join(PROFILE, "state.json"))
        print("Session saved\n")

        for name, url in URLS.items():
            print(f"--- {name} ---")
            await page.goto(url)
            await page.wait_for_timeout(8000)

            body = await page.evaluate("() => document.body.innerText")
            for line in body.split("\n"):
                line = line.strip()
                for kw in ["budget", "fee", "deposit", "price"]:
                    if kw in line.lower() and len(line) > 10:
                        print(f"  [{kw}] {line[:150]}")

            # Also search for Chinese budget keywords
            for line in body.split("\n"):
                line = line.strip()
                for kw in ["预算", "限价", "报名费", "保证金"]:
                    if kw in line and len(line) > 10:
                        print(f"  [{kw}] {line[:150]}")

            print(f"  Content length: {len(body)} chars")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
