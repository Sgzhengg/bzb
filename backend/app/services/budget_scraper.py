"""
zhaobiao.cn 自动登录 + 预算抓取服务
用于前端 UI 集成：用户点击按钮 → 打开浏览器 → 手动登录 → 系统自动抓取
"""
import asyncio, os, re, logging, threading, time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_DIR = os.path.join(BASE_DIR, "zhaobiao_profile")

# 需要抓取的公告
TARGET_ANNOUNCEMENTS = {
    3: ("韶关", "https://zb.zhaobiao.cn/free_v_1beee0b803bed7fda7b16bb233a09227.html"),
    2: ("中山", "https://zb.zhaobiao.cn/free_v_a3d904fb8979505423646c5aa695d292.html"),
}


class ScrapeStatus(str, Enum):
    IDLE = "idle"
    WAITING_LOGIN = "waiting_login"
    SCRAPING = "scraping"
    DONE = "done"
    FAILED = "failed"


@dataclass
class ScrapeState:
    status: ScrapeStatus = ScrapeStatus.IDLE
    message: str = ""
    results: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    login_elapsed: int = 0


# 全局状态（单例）
_state = ScrapeState()
_lock = threading.Lock()


def get_state() -> ScrapeState:
    with _lock:
        return ScrapeState(
            status=_state.status,
            message=_state.message,
            results=dict(_state.results),
            login_elapsed=_state.login_elapsed,
        )


def _extract_wan(text: str) -> Optional[float]:
    m = re.search(r"([\d,.]+)\s*(?:万|万元)", text)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"([\d,.]+)\s*元", text)
    if m:
        return float(m.group(1).replace(",", "")) / 10000
    return None


async def _check_logged_in(page) -> bool:
    try:
        await page.goto(
            "https://zb.zhaobiao.cn/free_v_1beee0b803bed7fda7b16bb233a09227.html",
            wait_until="domcontentloaded",
        )
        await page.wait_for_timeout(5000)
        body = await page.evaluate("() => document.body.innerText")
        return "仅对会员开放" not in body and len(body) > 500
    except Exception as e:
        logger.warning(f"Login check error: {e}")
        return False


async def run_scrape(db_url: str):
    """主抓取流程——在后台线程的 asyncio 事件循环中运行"""
    global _state

    try:
        from playwright.async_api import async_playwright

        os.makedirs(PROFILE_DIR, exist_ok=True)

        with _lock:
            _state.status = ScrapeStatus.WAITING_LOGIN
            _state.message = "正在启动浏览器..."
            _state.results = {}

        async with async_playwright() as pw:
            ctx = await pw.chromium.launch_persistent_context(
                PROFILE_DIR,
                channel="msedge",  # 使用 Edge 浏览器
                headless=False,
                viewport={"width": 1280, "height": 900},
            )
            page = await ctx.new_page()

            # ── 1. 检查/等待登录 ──
            logged_in = await _check_logged_in(page)

            if not logged_in:
                with _lock:
                    _state.message = "请在浏览器中登录 zhaobiao.cn（含验证码）"

                await page.goto("https://www.zhaobiao.cn/")
                await page.wait_for_timeout(3000)

                # 等待登录，最多 3 分钟
                for i in range(36):
                    await page.wait_for_timeout(5000)
                    try:
                        body = await page.evaluate("() => document.body.innerText")
                        if "退出" in body or "会员中心" in body:
                            logged_in = True
                            break
                    except:
                        pass
                    with _lock:
                        _state.login_elapsed = (i + 1) * 5
                        _state.message = f"等待登录中... {_state.login_elapsed}秒"

            if not logged_in:
                with _lock:
                    _state.status = ScrapeStatus.FAILED
                    _state.message = "登录超时（3分钟），请重试"
                await ctx.close()
                return

            # 保存会话
            await ctx.storage_state(path=os.path.join(PROFILE_DIR, "state.json"))

            # ── 2. 抓取公告 ──
            with _lock:
                _state.status = ScrapeStatus.SCRAPING
                _state.message = "正在抓取公告详情..."

            import sqlite3
            db = sqlite3.connect(db_url)
            cur = db.cursor()

            for ann_id, (name, url) in TARGET_ANNOUNCEMENTS.items():
                with _lock:
                    _state.message = f"正在抓取: {name}..."

                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(8000)

                body = await page.evaluate("() => document.body.innerText")

                budget = None
                fee = None
                deposit = None
                found_lines = []

                for line in body.split("\n"):
                    s = line.strip()
                    if not s or len(s) > 300:
                        continue
                    if any(kw in s for kw in ["预算", "限价", "报名费", "保证金"]):
                        found_lines.append(s[:150])
                        val = _extract_wan(s)
                        if val is None:
                            continue
                        if "报名费" in s:
                            fee = val * 10000
                        elif "保证金" in s:
                            deposit = val * 10000
                        elif ("预算" in s or "限价" in s) and budget is None:
                            budget = val

                # 更新 DB
                if budget is not None:
                    cur.execute("UPDATE announcements SET budget = ? WHERE id = ?", (budget, ann_id))
                if fee is not None:
                    cur.execute("UPDATE announcements SET registration_fee = ? WHERE id = ?", (fee, ann_id))
                if deposit is not None:
                    cur.execute("UPDATE announcements SET deposit = ? WHERE id = ?", (deposit, ann_id))

                with _lock:
                    _state.results[ann_id] = {
                        "name": name,
                        "budget": budget,
                        "fee": fee,
                        "deposit": deposit,
                        "lines_found": len(found_lines),
                    }

            db.commit()
            db.close()
            await ctx.close()

            with _lock:
                _state.status = ScrapeStatus.DONE
                _state.message = "抓取完成"

    except Exception as e:
        logger.error(f"Scrape failed: {e}", exc_info=True)
        with _lock:
            _state.status = ScrapeStatus.FAILED
            _state.message = f"抓取出错: {str(e)[:100]}"


def start_scrape_async(db_url: str):
    """在后台线程中启动抓取任务"""
    global _state
    with _lock:
        if _state.status in (ScrapeStatus.WAITING_LOGIN, ScrapeStatus.SCRAPING):
            return  # 已在运行
        _state = ScrapeState()

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_scrape(db_url))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
