"""
b2b.10086.cn 公告正文刮削器 - 优化版手动辅助模式

基于全面测试验证的最可靠方案：
- 优化的关键词提取算法
- 改进的用户引导流程
- 可靠的详情页检测机制
- 完整的调试信息
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
QUERY_API = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryList"


def _extract_smart_keyword(title: str) -> str:
    """智能提取搜索关键词 - 优化版"""

    # 1. 移除常见的前缀公司名
    prefixes_to_remove = [
        "中国移动通信集团广东有限公司",
        "中国移动广东公司",
        "中国移动通信集团",
        "中国移动",
    ]

    cleaned = title
    for prefix in prefixes_to_remove:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break

    # 2. 提取地名 + 项目关键词
    cities = ["广州","深圳","东莞","佛山","中山","珠海","江门","惠州","汕头","湛江","茂名","肇庆","梅州","汕尾","河源","阳江","清远","韶关","潮州","揭阳","云浮"]
    city = next((c for c in cities if c in cleaned), "")

    # 3. 提取项目核心词（年份后面的内容）
    year_match = re.search(r'\d{4}年.*?\d{4}年(.+?)(?:公开|采购|询价|招标|项目|$)', cleaned)
    if year_match:
        core = year_match.group(1).strip()
        # 移除采购方式后缀
        core = re.sub(r'(公开招标|公开询比|竞争性谈判|单一来源|询价).*$', '', core)
        if len(core) >= 4:
            # 地市 + 项目核心词
            if city:
                return f"{city} {core[:15]}"
            return core[:20]

    # 4. 提取括号内的关键词
    bracket_match = re.search(r'[（(]([^）)]+)[）)]', cleaned)
    if bracket_match:
        kw = bracket_match.group(1).strip()
        if len(kw) >= 3 and kw not in ['二次', '重新招标']:
            if city:
                return f"{city} {kw}"
            return kw

    # 5. 提取地市 + 前15字符核心词
    if city:
        remaining = cleaned.replace(city, "").strip()
        core_part = remaining[:15] if len(remaining) > 15 else remaining
        return f"{city} {core_part}"

    # 6. 最终回退：使用前20字符
    return cleaned[:20]


def _check_b2b_api(keyword: str) -> Optional[str]:
    """用 httpx 调 b2b queryList API 确认公告存在（绕过 SSL 问题）"""
    try:
        resp = httpx.post(
            QUERY_API,
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


def _scrape_sync(keyword: str, api_confirmed_name: Optional[str], timeout: int) -> Optional[Dict[str, Any]]:
    """核心刮削逻辑（同步，在 asyncio.to_thread 中运行）"""

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=100, channel="msedge")
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()

        try:
            # 1. 打开搜索页
            page.goto(B2B_MAIN + "#/searchPage", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)

            # 2. 填入优化的搜索关键词
            try:
                inp = page.locator('.cmcc-input').first
                inp.wait_for(state="visible", timeout=5000)
                inp.fill(keyword[:30])
            except Exception:
                pass

            # 3. 显示用户引导
            print(f"\n{'='*70}")
            print(f"  b2b Search Assistant Started")
            print(f"  Search Keyword: {keyword[:40]}")
            if api_confirmed_name:
                print(f"  API Confirmed Target: {api_confirmed_name[:60]}")
            else:
                print(f"  API: No exact match found, please search manually")

            print(f"\n  Operation Steps:")
            print(f"     1. Confirm search keyword in browser")
            print(f"     2. Click search button")
            print(f"     3. Find target announcement in results")
            print(f"     4. Click announcement title to enter detail page")
            print(f"\n  Wait Time: {timeout} seconds")
            print(f"{'='*70}\n")

            # 4. 等待用户点击详情（多重检测）
            initial_len = len(page.evaluate("() => document.body.innerText"))
            initial_url = page.url

            for i in range(timeout):
                page.wait_for_timeout(1000)
                try:
                    current_len = len(page.evaluate("() => document.body.innerText"))
                    current_url = page.url

                    # 检测标准 1: URL 变化（进入详情页）
                    url_changed = current_url != initial_url and ("detail" in current_url.lower() or "bulletin" in current_url.lower())

                    # 检测标准 2: 文本长度显著增长（详情页通常更长）
                    text_grown = current_len > initial_len + 2000

                    # 检测标准 3: 包含预算相关关键词
                    try:
                        page_text = page.evaluate("() => document.body.innerText")
                        has_keywords = any(kw in page_text for kw in ["预算", "万元", "元", "保证金", "标书费"])
                    except:
                        has_keywords = False

                    if url_changed or (text_grown and has_keywords):
                        page.wait_for_timeout(3000)  # 等详情完全加载
                        content = _extract_content(page)

                        if content and len(content) > 1000:  # 详情页通常 > 1000 字符
                            print(f"\nSUCCESS: Detail page detected (second {i+1}), extracted {len(content)} characters\n")
                            return {
                                "content": content,
                                "url": current_url,
                                "title": page.title(),
                                "method": "manual_assisted_optimized"
                            }

                except Exception:
                    continue

                # 每 10 秒提醒一次
                if (i + 1) % 10 == 0:
                    print(f"  Waiting... ({i+1}/{timeout} seconds)")

            logger.warning(f"超时（{timeout}秒）未检测到详情页")
            return None

        finally:
            browser.close()


async def scrape_with_optimized_guidance(keyword: str, timeout: int = 180) -> Optional[Dict[str, Any]]:
    """
    优化的手动辅助抓取入口

    Args:
        keyword: 搜索关键词（如果为空，将从数据库公告标题自动提取）
        timeout: 超时时间（秒）
    """
    # 1. 如果没有提供关键词，返回 None（由调用方处理）
    if not keyword:
        return None

    # 2. 用 API 预先确认目标存在
    api_confirmed_name = _check_b2b_api(keyword)

    # 3. 执行刮削
    return await asyncio.to_thread(_scrape_sync, keyword, api_confirmed_name, timeout)


async def scrape_from_announcement_title(title: str, timeout: int = 180) -> Optional[Dict[str, Any]]:
    """
    从公告标题自动提取关键词并刮削

    Args:
        title: 公告标题
        timeout: 超时时间（秒）
    """
    # 1. 智能提取搜索关键词
    keyword = _extract_smart_keyword(title)
    logger.info(f"从标题 '{title[:50]}...' 提取关键词: {keyword}")

    # 2. 执行刮削
    return await scrape_with_optimized_guidance(keyword, timeout)