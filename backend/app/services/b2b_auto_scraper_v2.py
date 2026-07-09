"""
b2b.10086.cn 全自动刮削器 V2 - 网络拦截版本

核心策略：page.route() 拦截 luceneSearchList → 注入 queryList 结果 → 点击真实 DOM → 详情页
"""
import asyncio
import logging
import json
from typing import Optional, Dict, Any

from playwright.sync_api import sync_playwright

import httpx
from app.services.b2b_proxy import _get_ssl_context

logger = logging.getLogger(__name__)

B2B_MAIN = "https://b2b.10086.cn/b2b/main/listVendorNotice.html?noticeType=2"
QUERY_API = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryList"


def _search_api(keyword: str) -> list:
    """用 httpx 调 queryList API（带 SSL 修复）"""
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


async def scrape_auto_v2(keyword: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
    """全自动 b2b 公告正文抓取 V2 - 网络拦截版"""

    # Step 1: 用 API 搜索（带 SSL 修复的 httpx）
    api_items = _search_api(keyword)
    if not api_items:
        logger.error(f"API 搜索无结果: {keyword}")
        return None

    target_name = api_items[0].get("name", "")[:80]
    logger.info(f"API 找到: {target_name}")

    # Step 2: Playwright 网络拦截 + 自动点击
    return await asyncio.to_thread(_scrape_with_route_intercept, keyword, api_items, timeout)


def _scrape_with_route_intercept(keyword: str, api_items: list, timeout: int) -> Optional[Dict[str, Any]]:
    """同步 Playwright：拦截 SPA 网络请求 → 注入 queryList 结果 → 点击真实 DOM → 提取详情页"""

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, channel="msedge", slow_mo=100)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()

        try:
            # 1. 设置网络拦截 - 拦截 luceneSearchList API
            def intercept_search_api(route):
                """拦截搜索 API 请求，注入 queryList 结果"""
                request = route.request
                url = request.url

                # 拦截 luceneSearchList 请求
                if "luceneSearchList" in url:
                    logger.info(f"✋ 拦截到 luceneSearchList 请求")

                    # 调试：记录原始请求信息
                    logger.info(f"原始请求方法: {request.method}")
                    logger.info(f"原始请求头: {dict(request.headers)}")

                    # 构造与 luceneSearchList 相同格式的响应
                    mock_response = {
                        "code": 0,
                        "msg": "success",
                        "data": {
                            "content": api_items,
                            "total": len(api_items),
                            "size": 10,
                            "current": 1,
                            "pages": 1
                        }
                    }

                    # 使用正确的 JSON 序列化
                    import json
                    response_body = json.dumps(mock_response, ensure_ascii=False)

                    logger.info(f"注入响应数据: {response_body[:200]}...")

                    # 注入响应数据
                    route.fulfill(
                        status=200,
                        headers={
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*"
                        },
                        body=response_body
                    )
                    logger.info(f"✅ 注入了 {len(api_items)} 条搜索结果")
                else:
                    # 其他请求正常放行
                    route.continue_()

            # 注册拦截器
            page.route("**/*", intercept_search_api)

            # 2. 加载搜索页
            page.goto(B2B_MAIN + "#/searchPage", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)

            # 3. 填入搜索关键词并触发搜索
            try:
                search_input = page.locator('.cmcc-input').first
                search_input.wait_for(state="visible", timeout=5000)
                search_input.fill(keyword[:30])
                page.wait_for_timeout(1000)

                # 触发搜索
                search_input.press("Enter")
                logger.info(f"✅ 触发搜索: {keyword[:30]}")

                # 等待 SPA 渲染搜索结果（现在会显示我们注入的数据）
                page.wait_for_timeout(5000)

            except Exception as e:
                logger.warning(f"搜索操作失败: {e}")

            # 4. 检查注入的数据是否正确渲染
            rendered_info = page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table, .el-table, .ant-table');
                    const info = {
                        tableCount: tables.length,
                        rows: []
                    };

                    if (tables.length > 0) {
                        const rows = tables[0].querySelectorAll('tr');
                        info.rows = Array.from(rows).slice(0, 5).map(row => ({
                            text: row.innerText.substring(0, 50),
                            length: row.innerText.length,
                            hasLink: !!row.querySelector('a'),
                            hasButton: !!row.querySelector('button, .btn'),
                            hasOnclick: !!row.querySelector('[onclick]')
                        }));
                    }

                    return info;
                }
            """)

            logger.info(f"📊 SPA 渲染信息:")
            logger.info(f"  - 表格数量: {rendered_info.get('tableCount', 0)}")
            logger.info(f"  - 前5行信息:")

            for i, row_info in enumerate(rendered_info.get('rows', [])):
                logger.info(f"    行{i}: 文本={row_info['text'][:30]}... 长度={row_info['length']} 链接={row_info['hasLink']} 按钮={row_info['hasButton']} onclick={row_info['hasOnclick']}")

            if rendered_info.get('tableCount', 0) == 0:
                logger.warning("⚠️ SPA 没有正确渲染搜索结果")
                # 尝试强制点击策略
                return _try_force_click_strategy(page, api_items, timeout)

            # 5. 点击真实 DOM 元素触发 Vue Router 导航
            target_id = api_items[0].get("id", "")
            target_title = api_items[0].get("name", "")

            logger.info(f"🎯 准备点击: {target_title[:50]}")

            click_success = False
            try:
                # 等待表格完全加载
                page.wait_for_selector("table tbody tr", timeout=10000)
                page.wait_for_timeout(2000)

                # 使用 Playwright 的原生点击（更可靠）
                click_result = page.evaluate(f"""
                    () => {{
                        const targetTitle = '{target_title[:50]}'.toLowerCase();
                        const tables = document.querySelectorAll('table, .el-table, .ant-table');

                        console.log('查找目标标题:', targetTitle);
                        console.log('找到表格数量:', tables.length);

                        for (let table of tables) {{
                            const rows = table.querySelectorAll('tr');
                            console.log('检查表格，共有', rows.length, '行');

                            for (let i = 0; i < rows.length; i++) {{
                                const row = rows[i];
                                const text = row.innerText.toLowerCase();

                                console.log('行', i, '文本长度:', text.length, '是否包含目标:', text.includes(targetTitle));

                                if (text.includes(targetTitle) && text.length > 20) {{
                                    console.log('✅ 找到匹配行:', text.substring(0, 50));

                                    // 尝试多种点击方式
                                    const link = row.querySelector('a');
                                    if (link) {{
                                        console.log('🔗 点击链接');
                                        link.click();
                                        return 'clicked_link';
                                    }}

                                    // 尝试按钮元素
                                    const button = row.querySelector('button, .btn, [type="button"]');
                                    if (button) {{
                                        console.log('🔘 点击按钮');
                                        button.click();
                                        return 'clicked_button';
                                    }}

                                    // 尝试包含 onclick 的元素
                                    const onclickElement = row.querySelector('[onclick]');
                                    if (onclickElement) {{
                                        console.log('⚡ 点击 onclick 元素');
                                        onclickElement.click();
                                        return 'clicked_onclick';
                                    }}

                                    // 直接点击行
                                    console.log('🖱️ 直接点击行');
                                    row.click();
                                    return 'clicked_row';
                                }}
                            }}
                        }}
                        return 'not_found';
                    }}
                """)

                logger.info(f"点击结果: {click_result}")

                if click_result.startswith('clicked'):
                    click_success = True
                    page.wait_for_timeout(5000)  # 等待 Vue Router 导航完成

            except Exception as e:
                logger.warning(f"点击操作失败: {e}")

            # 6. 检测详情页加载
            detail_detected = False
            for i in range(timeout):
                page.wait_for_timeout(2000)

                try:
                    current_url = page.url
                    page_text = page.evaluate("() => document.body.innerText")

                    # 详情页检测标准
                    url_changed = "detail" in current_url.lower() or "bulletin" in current_url.lower()
                    text_increased = len(page_text) > 4000  # 详情页通常更长
                    has_budget_keywords = any(kw in page_text for kw in ["预算", "万元", "元", "保证金", "标书费"])

                    logger.info(f"检测第{i+1}秒 - URL: {current_url[:60]}... 文本长度: {len(page_text)} 预算关键词: {has_budget_keywords}")

                    if url_changed or (text_increased and has_budget_keywords):
                        detail_detected = True
                        logger.info(f"✅ 检测到详情页 (第{i+1}秒)")
                        break

                except Exception as e:
                    logger.warning(f"检测异常 (第{i+1}秒): {e}")
                    continue

            if not detail_detected:
                logger.error("❌ 未检测到详情页加载")
                return None

            # 7. 提取详情页内容
            page.wait_for_timeout(3000)  # 确保内容完全加载
            detail_body = page.evaluate("() => document.body.innerText")
            logger.info(f"📄 详情页文本长度: {len(detail_body)} 字符")

            if len(detail_body) < 3000:
                logger.warning("详情页内容过短，可能未正确加载")
                return None

            content = _extract_content(page)
            if content and len(content) > 2000:
                logger.info(f"✅ 成功提取详情页: {len(content)} 字符")
                return {
                    "content": content,
                    "url": page.url,
                    "title": page.title(),
                    "method": "route_intercept_success"
                }

            return None

        finally:
            browser.close()


def _try_force_click_strategy(page, api_items: list, timeout: int) -> Optional[Dict[str, Any]]:
    """强制点击策略 - 当 SPA 渲染失败时的备用方案"""
    target_id = api_items[0].get("id", "")
    target_title = api_items[0].get("name", "")

    logger.info("🔄 尝试强制点击策略")

    try:
        # 尝试通过 Vue Router 直接导航
        nav_result = page.evaluate(f"""
            () => {{
                const tid = '{target_id}';
                try {{
                    // 尝试直接修改 hash
                    window.location.hash = '#/biddingProcurementBulletinDetail?id=' + tid;

                    // 触发 hashchange 事件
                    window.dispatchEvent(new HashChangeEvent('hashchange', {{
                        newURL: window.location.href,
                        oldURL: window.location.href
                    }}));

                    return 'hash_navigation';
                }} catch(e) {{
                    return 'error: ' + e.message;
                }}
            }}
        """)

        logger.info(f"强制导航结果: {nav_result}")
        page.wait_for_timeout(5000)

        # 检测是否成功导航
        current_url = page.url
        if "detail" in current_url.lower():
            return _extract_and_return(page)

    except Exception as e:
        logger.warning(f"强制点击策略失败: {e}")

    return None


def _extract_and_return(page) -> Optional[Dict[str, Any]]:
    """提取页面内容并返回"""
    content = _extract_content(page)
    if content and len(content) > 2000:
        return {
            "content": content,
            "url": page.url,
            "title": page.title(),
            "method": "force_extract_success"
        }
    return None


def _extract_content(page) -> str:
    """从详情页 DOM 提取正文"""
    for sel in [".bidding-detail", ".notice-content", ".detail-content", "article", "main", "#app"]:
        try:
            el = page.query_selector(sel)
            if el and len(el.inner_text()) > 300:
                return el.inner_text()
        except:
            continue
    return page.evaluate("() => document.body.innerText")