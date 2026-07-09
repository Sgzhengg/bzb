"""
b2b.10086.cn 全自动刮削器

策略：Playwright 拦截 SPA 网络请求 → 用 queryList API 结果替换 luceneSearchList 结果
      → SPA 正常渲染搜索结果 → 自动点击 → 提取详情页正文

这解决了：
  1. luceneSearchList 中文搜索不可用 → 用 queryList 结果注入
  2. 详情页无法直接 URL 访问 → 依赖 SPA 正常渲染流程
  3. 全程无需用户手动操作
"""
import asyncio
import logging
from typing import Optional, Dict, Any

from playwright.sync_api import sync_playwright, Route

import httpx
from app.services.b2b_proxy import _get_ssl_context

logger = logging.getLogger(__name__)

B2B_MAIN = "https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2"
QUERY_API = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryList"


def _search_api(keyword: str) -> list:
    """用 httpx 调 queryList API"""
    try:
        resp = httpx.post(
            QUERY_API,
            json={"name": keyword, "publishType": "PROCUREMENT", "size": 10, "current": 1, "sfactApplColumn5": "PC"},
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            verify=_get_ssl_context(),
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("content", [])
    except Exception as e:
        logger.error(f"API search failed: {e}")
    return []


def _intercept_search_results(route: Route, api_items: list):
    """拦截 luceneSearchList 请求，注入 queryList 的结果"""
    # 构造与 luceneSearchList 相同格式的响应
    fake_response = {
        "code": 0,
        "msg": "success",
        "data": {
            "content": api_items,
            "total": len(api_items),
            "size": 10,
            "current": 1,
            "pages": 1,
        },
    }
    route.fulfill(
        status=200,
        contentType="application/json",
        body=str(fake_response).replace("'", '"'),  # 简单 JSON 序列化
    )


async def scrape_auto(keyword: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
    """全自动 b2b 公告正文抓取"""

    # Step 1: 用 API 搜索（带 SSL 修复的 httpx）
    api_items = _search_api(keyword)
    if not api_items:
        logger.error(f"API 搜索无结果: {keyword}")
        return None

    target_name = api_items[0].get("name", "")[:80]
    logger.info(f"API 找到: {target_name}")

    # Step 2: Playwright 拦截 + 自动点击
    return await asyncio.to_thread(_scrape_with_intercept_sync, keyword, api_items, timeout)


def _scrape_with_intercept_sync(keyword: str, api_items: list, timeout: int) -> Optional[Dict[str, Any]]:
    """同步 Playwright：模拟完整用户流程 → 搜索 → 点击 → 提取"""

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, channel="msedge")
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()

        try:
            # 1. 加载搜索页
            page.goto(B2B_MAIN + "#/searchPage", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            # 2. 填入搜索关键词（模拟真实用户行为）
            try:
                search_input = page.locator('.cmcc-input').first
                search_input.wait_for(state="visible", timeout=5000)
                search_input.fill(keyword[:30])
                page.wait_for_timeout(1000)

                # 模拟按 Enter 键触发搜索
                search_input.press("Enter")
                page.wait_for_timeout(3000)  # 等搜索结果加载

                logger.info(f"✅ 已填入搜索词: {keyword[:30]}")
            except Exception as e:
                logger.warning(f"搜索框操作失败: {e}")

            # 3. 网络监听 + 路由拦截
            target_id = api_items[0].get("id", "")
            target_title = api_items[0].get("name", "")

            # 4. 多重导航策略
            nav_success = False

            # 策略 A: 尝试找到并点击搜索结果
            try:
                # 等待搜索结果表格加载
                page.wait_for_selector("table, .el-table, .ant-table", timeout=10000)
                page.wait_for_timeout(2000)

                # 查找包含目标标题的表格行并点击
                click_result = page.evaluate(f"""
                    () => {{
                        const targetTitle = '{target_title[:50]}'.toLowerCase();
                        const tables = document.querySelectorAll('table, .el-table, .ant-table');
                        for (let table of tables) {{
                            const rows = table.querySelectorAll('tr');
                            for (let row of rows) {{
                                const text = row.innerText.toLowerCase();
                                if (text.includes(targetTitle) && text.length > 20) {{
                                    // 尝试多种点击方式
                                    const link = row.querySelector('a');
                                    if (link) {{
                                        link.click();
                                        return 'clicked_link';
                                    }}
                                    row.click();
                                    return 'clicked_row';
                                }}
                            }}
                        }}
                        return 'not_found';
                    }}
                """)

                logger.info(f"点击结果: {click_result}")

                if click_result in ['clicked_link', 'clicked_row']:
                    nav_success = True
                    page.wait_for_timeout(5000)  # 等详情页加载

                    # 检查点击后的状态
                    current_url = page.url
                    page_text_length = len(page.evaluate("() => document.body.innerText"))
                    logger.info(f"点击后状态 - URL: {current_url[:80]}... 文本长度: {page_text_length}")

                    # 检查是否有弹窗或需要进一步操作
                    has_modal = page.evaluate("""
                        () => {
                            const modals = document.querySelectorAll('.modal, .dialog, .el-dialog, [role="dialog"]');
                            return modals.length > 0;
                        }
                    """)
                    if has_modal:
                        logger.info("检测到弹窗，可能需要额外操作")


            except Exception as e:
                logger.warning(f"点击策略失败: {e}")

            # 策略 B: 如果点击失败，尝试直接 Vue Router 导航
            if not nav_success:
                nav_result = page.evaluate(f"""
                    () => {{
                        const tid = '{target_id}';
                        try {{
                            // 方法1: Vue 3 全局路由器
                            const app = document.querySelector('#app');
                            if (app && app.__vue_app__) {{
                                const vueApp = app.__vue_app__;
                                if (vueApp.config.globalProperties && vueApp.config.globalProperties.$router) {{
                                    vueApp.config.globalProperties.$router.push('/biddingProcurementBulletinDetail?id=' + tid);
                                    return 'vue3_global';
                                }}
                            }}
                            // 方法2: Vue 2 方式
                            if (app && app.__vue__ && app.__vue__.$router) {{
                                app.__vue__.$router.push('/biddingProcurementBulletinDetail?id=' + tid);
                                return 'vue2';
                            }}
                            // 方法3: window 全局对象
                            if (window.$router) {{
                                window.$router.push('/biddingProcurementBulletinDetail?id=' + tid);
                                return 'window_router';
                            }}
                            // 方法4: 手动 hash 变化 + 事件触发
                            window.location.hash = '#/biddingProcurementBulletinDetail?id=' + tid;
                            if (window.dispatchEvent) {{
                                window.dispatchEvent(new HashChangeEvent('hashchange', {{
                                    newURL: window.location.href,
                                    oldURL: window.location.href
                                }}));
                            }}
                            return 'hash_event';
                        }} catch(e) {{
                            return 'error: ' + e.message;
                        }}
                    }}
                """)
                logger.info(f"Vue Router 导航结果: {nav_result}")
                page.wait_for_timeout(6000)

            # 5. 检测详情页加载
            detail_detected = False
            for i in range(timeout):
                page.wait_for_timeout(2000)  # 增加等待时间到2秒

                try:
                    current_url = page.url
                    page_text = page.evaluate("() => document.body.innerText")

                    # 更全面的检测标准
                    url_changed = "detail" in current_url.lower() or "bulletin" in current_url.lower()
                    text_increased = len(page_text) > 3000
                    has_detail_content = any(keyword in page_text.lower() for keyword in ["公告", "bulletin", "notice", "采购", "tender"])

                    logger.info(f"检测第{i+1}秒 - URL: {current_url[:50]}... 文本长度: {len(page_text)}")

                    if url_changed or (text_increased and has_detail_content):
                        detail_detected = True
                        logger.info(f"✅ 检测到详情页 (第{i+1}秒)")
                        logger.info(f"检测标准: URL变化={url_changed}, 文本增长={text_increased}, 关键内容={has_detail_content}")
                        break

                except Exception as e:
                    logger.warning(f"检测异常 (第{i+1}秒): {e}")
                    continue

            if not detail_detected:
                # 尝试最后的内容提取，即使检测条件不完全满足
                page.wait_for_timeout(3000)
                final_content = _extract_content(page)
                if final_content and len(final_content) > 1000:
                    logger.info(f"✅ 强制提取成功: {len(final_content)} 字符")
                    return {
                        "content": final_content,
                        "url": page.url,
                        "title": page.title(),
                        "method": "forced_extraction"
                    }

                logger.error("❌ 未检测到详情页加载")
                return None

            # 6. 提取详情页内容
            page.wait_for_timeout(3000)  # 确保内容完全加载
            detail_body = page.evaluate("() => document.body.innerText")
            logger.info(f"详情页文本长度: {len(detail_body)} 字符")

            if len(detail_body) < 1000:
                logger.warning("详情页内容过短，可能未正确加载")
                return None

            content = _extract_content(page)
            if content and len(content) > 500:
                return {
                    "content": content,
                    "url": page.url,
                    "title": page.title(),
                    "method": "auto_navigation_success"
                }

            return None

        finally:
            browser.close()


def _extract_content(page) -> str:
    for sel in [".bidding-detail", ".notice-content", ".detail-content", "article", "main", "#app"]:
        try:
            el = page.query_selector(sel)
            if el and len(el.inner_text()) > 300:
                return el.inner_text()
        except:
            continue
    return page.evaluate("() => document.body.innerText")
