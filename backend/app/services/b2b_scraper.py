"""
b2b.10086.cn 公告正文刮削器（精简版）

流程：httpx API 确认公告存在 → 打开 Edge → 用户手动搜索点击 → 自动提取正文
"""
import asyncio
import logging
import re
from typing import Optional, Dict, Any

from playwright.sync_api import sync_playwright

import httpx
from app.services.b2b_proxy import _get_ssl_context

logger = logging.getLogger(__name__)

B2B_MAIN = "https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2"


def _extract_keyword(title: str) -> str:
    """从标题提取搜索关键词"""
    cities = ["广州","深圳","东莞","佛山","中山","珠海","江门","惠州","汕头","湛江","茂名","肇庆","梅州","汕尾","河源","阳江","清远","韶关","潮州","揭阳","云浮"]
    city = next((c for c in cities if c in title), "")
    yr_match = re.search(r"\d{4}年.*?\d{4}年(.+?)(?:公开|采购|询价|招标|项目|$)", title)
    core = yr_match.group(1).strip() if yr_match else ""
    kw = f"{city} {core}".strip() if city and core else (city or core or title[:30])
    return kw[:50]


def _check_b2b_api(keyword: str) -> Optional[str]:
    """用 httpx 调 b2b queryList 确认公告存在（绕过 SSL 问题）"""
    try:
        resp = httpx.post(
            "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryList",
            json={"name": keyword, "publishType": "PROCUREMENT", "size": 3, "current": 1, "sfactApplColumn5": "PC"},
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            verify=_get_ssl_context(),
            timeout=15,
        )
        if resp.status_code == 200:
            items = resp.json().get("data", {}).get("content", [])
            if items:
                return items[0].get("name", "")[:80]
    except Exception as e:
        logger.warning(f"b2b API 检查失败: {e}")
    return None


def _extract_content(page) -> str:
    """从详情页 DOM 提取正文"""
    for sel in [".bidding-detail", ".notice-content", ".detail-content", ".bulletin-detail", "article", "main", "#app"]:
        try:
            el = page.query_selector(sel)
            if el and len(el.inner_text()) > 300:
                return el.inner_text()
        except Exception:
            continue
    return page.evaluate("() => document.body.innerText")


def _scrape_sync(keyword: str, timeout: int = 180) -> Optional[Dict[str, Any]]:
    """核心刮削逻辑（同步，在 asyncio.to_thread 中运行）"""

    # Step 0: API 检查
    match_name = _check_b2b_api(keyword)
    if match_name:
        logger.info(f"✅ b2b API 确认: {match_name}")
    else:
        logger.warning(f"⚠️ b2b API 未找到: {keyword}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, channel="msedge")
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()

        try:
            # 打开搜索页
            page.goto(B2B_MAIN + "#/searchPage", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)

            # 填入搜索词
            try:
                inp = page.locator('.cmcc-input').first
                inp.wait_for(state="visible", timeout=5000)
                inp.fill(keyword[:30])
            except Exception:
                pass

            print(f"\n{'='*60}")
            print(f"  🔍 请在 Edge 中搜索并点击公告标题")
            print(f"  📝 搜索词: {keyword[:40]}")
            if match_name:
                print(f"  ✅ API 已确认: {match_name}")
            print(f"  ⏰ 等待 {timeout} 秒")
            print(f"{'='*60}\n")

            # 等待详情页（检测文本大幅增长）
            init_len = len(page.evaluate("() => document.body.innerText"))

            for _ in range(timeout):
                page.wait_for_timeout(1000)
                try:
                    cur_len = len(page.evaluate("() => document.body.innerText"))
                    cur_url = page.url
                except Exception:
                    continue

                if cur_len > init_len + 2000 or "biddingProcurementBulletinDetail" in cur_url:
                    page.wait_for_timeout(3000)
                    content = _extract_content(page)
                    if content and len(content) > 500:
                        print(f"\n✅ 提取 {len(content)} 字符\n")
                        return {"content": content, "url": cur_url, "title": page.title()}

            logger.warning("超时")
            return None
        finally:
            browser.close()


async def scrape_with_user_click(keyword: str, timeout: int = 180) -> Optional[Dict[str, Any]]:
    """半自动抓取入口"""
    return await asyncio.to_thread(_scrape_sync, keyword, timeout)
