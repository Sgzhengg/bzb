"""
╔══════════════════════════════════════════════════════════════╗
║  中国电信采购平台 (caigou.chinatelecom.com.cn) 独立攻关脚本    ║
║  Telecom Breaker - 阶段一：技术攻关                          ║
╚══════════════════════════════════════════════════════════════╝

目标：
  1. 使用 Playwright 浏览器监控网络请求，找到真实 API 接口
  2. 分析 Cookie 生成和刷新机制
  3. 破解请求参数加密/签名逻辑
  4. 实现稳定的数据采集

技术难点：
  - JavaScript 高度混淆（Webpack + 自定义混淆器）
  - 多层 Cookie 验证（F82089F504F67EE2、D1DEA30ACA0D4D8A、sag_agent_cookie）
  - 请求参数可能加密签名
  - 频率限制严格

使用方式：
  # 先运行网络分析模式，找到真实 API：
  python telecom_breaker.py --mode analyze

  # 确认 API 后运行采集模式：
  python telecom_breaker.py --mode collect --keyword "广告"
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import httpx
from bs4 import BeautifulSoup

# 配置日志
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "telecom_breaker.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("telecom_breaker")

# ─────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────
CONFIG = {
    "base_url": "https://caigou.chinatelecom.com.cn",
    # 通过浏览器网络监控发现的候选 API（初始为空，analyze 模式填充）
    # ✅ 已通过浏览器分析确认的真实 API
    "list_api": "https://caigou.chinatelecom.com.cn/portal/base/announcementJoin/queryListNew",
    "detail_api": "https://caigou.chinatelecom.com.cn/portal/base/announcementJoin/queryDetail",
    # type 参数编码对应公告类型：
    #   xi9s → 采购公告, n0eves → 结果公告
    "announce_types": {
        "xi9s": "采购公告",
        "n0eves": "结果公告",
    },
    "candidate_apis": [],
    "search_keywords": [
        "广告", "宣传", "品牌", "活动策划", "新媒体",
        "视频制作", "营销", "设计", "物料", "推广",
    ],
    "max_pages": 3,
    "page_size": 20,
    "min_delay": 3.0,
    "max_delay": 6.0,
    "max_retries": 3,
    "timeout": 30,
    "output_dir": str(Path(__file__).parent / "output"),
}

# ─────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Edg/126.0.0.0",
]

_ua_index = 0

def random_ua() -> str:
    global _ua_index
    ua = USER_AGENTS[_ua_index % len(USER_AGENTS)]
    _ua_index += 1
    return ua

def random_delay(min_s: float = None, max_s: float = None):
    """随机延迟，模拟人类行为。"""
    if min_s is None:
        min_s = CONFIG["min_delay"]
    if max_s is None:
        max_s = CONFIG["max_delay"]
    delay = min_s + (max_s - min_s) * (hash(str(time.time())) % 1000) / 1000.0
    logger.debug(f"等待 {delay:.1f}s...")
    time.sleep(delay)

def safe_json_loads(text: str) -> dict:
    """安全 JSON 解析，支持多种格式。"""
    text = text.strip()
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试提取 JSONP
    m = re.search(r'(\w+)\((\{.*\})\)', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(2))
        except json.JSONDecodeError:
            pass
    # 尝试提取 {...} 块
    m = re.search(r'(\{.*\})', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return {}

def is_ad_keyword(title: str) -> bool:
    """判断标题是否包含广告类关键词。"""
    ad_kw = [
        "广告", "宣传", "品牌", "活动策划", "新媒体", "视频制作",
        "营销", "设计", "物料", "推广", "媒介", "创意",
        "直播", "短视频", "H5", "喷绘", "展会", "路演",
        "内容制作", "品牌推广", "品牌宣传", "广告设计", "广告制作",
        "广告代理", "宣传品", "宣传物料", "营销策划", "营销推广",
    ]
    return any(kw in title for kw in ad_kw)


# ═══════════════════════════════════════════════════════════════
# 模式一：浏览器网络监控分析（核心攻关）
# ═══════════════════════════════════════════════════════════════

class TelecomAPIAnalyzer:
    """
    使用 Playwright 启动浏览器，监控所有网络请求，
    找到中国电信采购平台的真实 API 接口。

    分析内容：
      - API 端点 URL
      - 请求方法 (GET/POST)
      - 请求头和 Cookie
      - 请求参数/Body
      - 响应格式
      - 分页机制
    """

    def __init__(self):
        self.captured_apis = []  # 捕获到的 API 请求
        self.cookies = {}
        self.session_info = {}
        self.playwright = None
        self.browser = None
        self.page = None

    def _on_request(self, request):
        """拦截所有请求。"""
        url = request.url
        method = request.method
        resource_type = request.resource_type

        # 只关注 XHR/Fetch 请求
        if resource_type not in ("xhr", "fetch"):
            return

        # 过滤静态资源和无关请求
        skip_patterns = [
            ".js", ".css", ".png", ".jpg", ".gif", ".svg", ".woff",
            ".ico", "google", "baidu", "hm.baidu", "analytics",
            "beacon", "collect", "track",
        ]
        if any(p in url.lower() for p in skip_patterns):
            return

        # 记录 API 请求
        headers = dict(request.headers)
        post_data = request.post_data

        captured = {
            "url": url,
            "method": method,
            "headers": {k: v for k, v in headers.items()
                       if k.lower() not in ("user-agent", "accept", "accept-language")},
            "post_data": post_data,
            "timestamp": datetime.now().isoformat(),
        }
        self.captured_apis.append(captured)

        logger.info(f"🔍 捕获 API: {method} {url[:120]}")
        if post_data:
            try:
                body = json.loads(post_data) if isinstance(post_data, str) else post_data
                logger.info(f"   Body: {json.dumps(body, ensure_ascii=False)[:200]}")
            except Exception:
                logger.info(f"   Body (raw): {str(post_data)[:200]}")

    def _on_response(self, response):
        """拦截所有响应。"""
        url = response.url
        resource_type = response.request.resource_type

        if resource_type not in ("xhr", "fetch"):
            return

        # 匹配最近捕获的 API
        for api in reversed(self.captured_apis):
            if api["url"] == url and "response" not in api:
                try:
                    body = response.text()
                    api["response_status"] = response.status
                    api["response_headers"] = dict(response.headers)
                    # 截断过长响应
                    if len(body) > 5000:
                        api["response_preview"] = body[:2000]
                        api["response_truncated"] = True
                    else:
                        api["response_preview"] = body
                    logger.info(f"📥 响应 {response.status}: {url[:120]} (len={len(body)})")
                except Exception as e:
                    api["response_error"] = str(e)
                    logger.warning(f"⚠️ 无法读取响应: {e}")
                break

    def analyze(
        self,
        headless: bool = False,
        search_keyword: str = "广告",
        timeout: int = 120000,
    ) -> list:
        """
        启动浏览器，搜索关键词，监控所有 API 调用。

        Args:
            headless: 是否无头模式（False 可以看到浏览器操作过程）
            search_keyword: 搜索关键词
            timeout: 页面加载超时(ms)

        Returns:
            捕获到的 API 列表
        """
        from playwright.sync_api import sync_playwright

        logger.info("=" * 60)
        logger.info("🚀 启动 Playwright 浏览器，开始分析中国电信采购平台...")
        logger.info(f"   URL: {CONFIG['base_url']}")
        logger.info(f"   搜索关键词: {search_keyword}")
        logger.info(f"   无头模式: {headless}")
        logger.info("=" * 60)

        with sync_playwright() as p:
            # 启动浏览器（非无头模式便于观察和手动操作）
            self.browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )
            context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random_ua(),
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )

            # 设置请求拦截
            context.on("request", self._on_request)
            context.on("response", self._on_response)

            self.page = context.new_page()

            try:
                # Step 1: 访问首页
                logger.info("📄 Step 1: 访问首页...")
                self.page.goto(CONFIG["base_url"], wait_until="networkidle", timeout=timeout)
                self.page.wait_for_timeout(3000)

                # 保存首页 Cookie
                cookies = context.cookies()
                self.cookies = {c["name"]: c["value"] for c in cookies}
                logger.info(f"   Cookie 数量: {len(cookies)}")
                for c in cookies:
                    logger.info(f"   🍪 {c['name']}: {c['value'][:50]}...")

                # Step 2: 尝试找到搜索框
                logger.info(f"🔍 Step 2: 搜索 '{search_keyword}'...")
                self._try_search(search_keyword)

                # Step 3: 等待更多 API 调用
                logger.info("⏳ Step 3: 等待异步请求...")
                self.page.wait_for_timeout(8000)

                # Step 4: 尝试翻页（如果有分页）
                logger.info("📖 Step 4: 尝试翻页...")
                self._try_pagination()

                # Step 5: 等待更多请求
                self.page.wait_for_timeout(5000)

            except Exception as e:
                logger.error(f"❌ 分析过程出错: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.browser.close()

        # 去重 API
        seen_urls = set()
        unique_apis = []
        for api in self.captured_apis:
            url_key = api["url"].split("?")[0]  # 忽略查询参数
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                unique_apis.append(api)

        logger.info(f"\n📊 共捕获 {len(unique_apis)} 个唯一 API 端点:")
        for i, api in enumerate(unique_apis):
            logger.info(f"   [{i+1}] {api['method']} {api['url'][:120]}")
            if "response_preview" in api:
                logger.info(f"       响应: {api['response_preview'][:100]}...")

        return unique_apis

    def _try_search(self, keyword: str):
        """尝试在页面上进行搜索操作。"""
        page = self.page

        # 常见的搜索框选择器
        search_selectors = [
            'input[type="search"]',
            'input[type="text"]',
            'input[placeholder*="搜索"]',
            'input[placeholder*="查询"]',
            'input[placeholder*="关键词"]',
            'input[name*="keyword"]',
            'input[name*="search"]',
            'input[name*="key"]',
            'input[id*="keyword"]',
            'input[id*="search"]',
            'input[id*="key"]',
            'input[class*="search"]',
            'input[class*="keyword"]',
            '.el-input__inner',
            '.ant-input',
            'input',
        ]

        for selector in search_selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=1000):
                    logger.info(f"   找到输入框: {selector}")
                    el.click()
                    el.fill(keyword)
                    page.wait_for_timeout(1500)

                    # 尝试找搜索按钮
                    btn_selectors = [
                        'button:has-text("搜索")',
                        'button:has-text("查询")',
                        'button:has-text("检索")',
                        'input[type="submit"]',
                        'button[type="submit"]',
                        '.el-button--primary',
                        'button.search-btn',
                        'button:has-text("Search")',
                    ]
                    for btn_sel in btn_selectors:
                        try:
                            btn = page.locator(btn_sel).first
                            if btn.is_visible(timeout=500):
                                logger.info(f"   找到搜索按钮: {btn_sel}")
                                btn.click()
                                page.wait_for_timeout(5000)
                                return
                        except Exception:
                            continue

                    # 尝试按回车搜索
                    el.press("Enter")
                    page.wait_for_timeout(5000)
                    return
            except Exception:
                continue

        logger.warning("   ⚠️ 未找到搜索框，使用 URL 参数搜索...")
        # 尝试直接通过 URL 参数搜索
        search_urls = [
            f"{CONFIG['base_url']}/search?keyword={keyword}",
            f"{CONFIG['base_url']}/ggzy/index?key={keyword}",
            f"{CONFIG['base_url']}/search.html?key={keyword}",
            f"{CONFIG['base_url']}/ggzy/jyxx/search?keyword={keyword}",
        ]
        for url in search_urls:
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(5000)
                logger.info(f"   尝试 URL: {url}")
                return
            except Exception:
                continue

    def _try_pagination(self):
        """尝试翻页操作触发更多 API 调用。"""
        page = self.page

        pagination_selectors = [
            'button:has-text("下一页")',
            'a:has-text("下一页")',
            '.el-pagination button',
            '.ant-pagination-next',
            'li.next',
            '.next',
            '[class*="pagination"] button:last-child',
            'button:has-text(">")',
        ]

        for selector in pagination_selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=1000):
                    el.click()
                    logger.info(f"   点击翻页: {selector}")
                    page.wait_for_timeout(5000)
                    return
            except Exception:
                continue

    def save_analysis(self, output_path: str = None):
        """保存分析结果到 JSON 文件。"""
        if output_path is None:
            output_path = str(Path(CONFIG["output_dir"]) / "telecom_api_analysis.json")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        result = {
            "target": "caigou.chinatelecom.com.cn",
            "analysis_time": datetime.now().isoformat(),
            "cookies": self.cookies,
            "captured_apis": self.captured_apis,
            "session_info": self.session_info,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"📁 分析结果已保存到: {output_path}")
        return output_path


# ═══════════════════════════════════════════════════════════════
# Direct API 采集（使用已确认的真实 API）
# ═══════════════════════════════════════════════════════════════

def fetch_telecom_data_direct(
    keyword: str = "广告",
    max_pages: int = 3,
    page_size: int = 20,
    ann_type: str = "xi9s",
) -> list:
    """
    直接调用已确认的中国电信 API 获取数据。

    API: POST https://caigou.chinatelecom.com.cn/portal/base/announcementJoin/queryListNew
    参数: {"pageNum": 1, "pageSize": 20, "type": "xi9s", "name": "广告"}
    """
    import ssl

    all_items = []
    seen_ids = set()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with httpx.Client(
        timeout=httpx.Timeout(30),
        follow_redirects=True,
        headers={
            "User-Agent": random_ua(),
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://caigou.chinatelecom.com.cn/",
            "Origin": "https://caigou.chinatelecom.com.cn",
        },
        transport=httpx.HTTPTransport(verify=ctx),
    ) as client:
        # 访问首页获取 Cookie
        logger.info("🍪 获取初始 Cookie...")
        try:
            client.get("https://caigou.chinatelecom.com.cn/", follow_redirects=True)
            random_delay(2, 3)
        except Exception as e:
            logger.warning(f"首页访问失败（继续尝试 API）: {e}")

        for page in range(1, max_pages + 1):
            body = {
                "pageNum": page,
                "pageSize": page_size,
                "type": ann_type,
            }
            if keyword:
                body["name"] = keyword

            logger.info(f"📡 请求第 {page} 页: type={ann_type}, keyword={keyword}")

            for attempt in range(3):
                try:
                    random_delay()
                    resp = client.post(CONFIG["list_api"], json=body)

                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("code") == 200:
                            page_info = data.get("data", {}).get("pageInfo", {})
                            items = page_info.get("list", [])
                            total = page_info.get("total", 0)

                            logger.info(f"   ✅ 第 {page} 页: {len(items)} 条 (总计 {total})")

                            for item in items:
                                item_id = item.get("id", "")
                                if item_id and item_id not in seen_ids:
                                    seen_ids.add(item_id)
                                    title = item.get("docTitle", "")
                                    all_items.append({
                                        "title": title,
                                        "publish_date": item.get("createDate", "")[:10],
                                        "detail_url": (
                                            f"https://caigou.chinatelecom.com.cn"
                                            f"/portal/base/announcementJoin/detail"
                                            f"?id={item.get('id', '')}"
                                            f"&idEncryStr={item.get('idEncryStr', '')}"
                                            f"&encryCode={item.get('encryCode', '')}"
                                        ),
                                        "notice_type": item.get("docType", ""),
                                        "province": item.get("provinceName", ""),
                                        "source": "caigou.chinatelecom.com.cn",
                                        "_raw": item,
                                    })

                            # CT API 的 hasNextPage 始终为 false，改用 total 判断
                            if len(items) < page_size:
                                logger.info(f"   📄 返回不足一页，停止")
                                return all_items
                            if total > 0 and page * page_size >= total:
                                logger.info(f"   📄 已到最后一页 (total={total})")
                                return all_items
                            break
                        else:
                            logger.warning(f"   API 返回错误: {data.get('msg')}")
                    elif resp.status_code == 429:
                        wait = 30 * (2 ** attempt)
                        logger.warning(f"   429 限流，等待 {wait}s")
                        time.sleep(wait)
                    else:
                        logger.warning(f"   HTTP {resp.status_code}")
                except Exception as e:
                    logger.warning(f"   请求失败 (attempt {attempt+1}): {e}")
                    time.sleep(5 * (2 ** attempt))
            else:
                logger.warning(f"   第 {page} 页重试耗尽")
                break

    return all_items


# ═══════════════════════════════════════════════════════════════
# 模式二：基于分析结果的自动化采集
# ═══════════════════════════════════════════════════════════════

class TelecomDataCollector:
    """
    基于 API 分析结果，实现自动化数据采集。

    支持两种采集策略：
      Strategy A: 如果发现了 JSON API，直接使用 httpx 调用
      Strategy B: 如果没有 JSON API，使用 Playwright 进行页面级采集
    """

    def __init__(self, api_analysis_path: str = None):
        self.api_config = {}
        self.client: Optional[httpx.AsyncClient] = None

        # 加载 API 分析结果
        if api_analysis_path and os.path.exists(api_analysis_path):
            with open(api_analysis_path, "r", encoding="utf-8") as f:
                self.api_config = json.load(f)
            logger.info(f"📂 已加载 API 分析: {api_analysis_path}")
            logger.info(f"   捕获 API 数量: {len(self.api_config.get('captured_apis', []))}")

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(CONFIG["timeout"]),
                follow_redirects=True,
                headers={
                    "User-Agent": random_ua(),
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Referer": CONFIG["base_url"] + "/",
                    "Origin": CONFIG["base_url"],
                },
            )
        return self.client

    async def _try_api_endpoint(
        self, api_info: dict, keyword: str, page: int = 1
    ) -> Optional[list]:
        """
        尝试复现一个 API 调用。

        根据捕获到的 API 信息，构造请求并解析响应。
        """
        url_template = api_info.get("url", "")
        method = api_info.get("method", "GET")
        headers = api_info.get("headers", {})
        post_data = api_info.get("post_data")

        client = await self._get_client()

        # 构造请求
        req_headers = dict(client.headers)
        req_headers.update(headers)

        try:
            if method == "POST":
                # 尝试替换搜索关键词
                body = {}
                if post_data:
                    try:
                        body = json.loads(post_data) if isinstance(post_data, str) else post_data
                    except Exception:
                        body = {}

                # 常见的搜索参数名
                for key in ("keyword", "key", "search", "name", "title", "query", "searchKey", "keyWord"):
                    if key in body:
                        body[key] = keyword
                        break
                # 分页参数
                for key in ("page", "pageNum", "current", "pageNo", "pageIndex", "offset"):
                    if key in body:
                        body[key] = page
                        break
                for key in ("size", "pageSize", "limit", "rows"):
                    if key in body:
                        body[key] = CONFIG["page_size"]
                        break

                resp = await client.post(url_template, json=body, headers=req_headers)
            else:
                # GET 请求
                params = parse_qs(urlparse(url_template).query)
                for key in ("keyword", "key", "search", "name", "title", "query"):
                    if key in params:
                        params[key] = [keyword]
                        break
                for key in ("page", "pageNum", "current", "pageNo"):
                    if key in params:
                        params[key] = [str(page)]
                        break

                resp = await client.get(
                    url_template.split("?")[0],
                    params={k: v[0] for k, v in params.items()},
                    headers=req_headers,
                )

            if resp.status_code == 200:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if isinstance(data, dict):
                    # 尝试各种常见的响应结构
                    for list_key in ("data", "list", "records", "rows", "content", "items", "result", "results"):
                        if list_key in data and isinstance(data[list_key], list):
                            return data[list_key]
                    if "data" in data and isinstance(data["data"], dict):
                        for list_key in ("list", "records", "rows", "content", "items"):
                            if list_key in data["data"] and isinstance(data["data"][list_key], list):
                                return data["data"][list_key]
                elif isinstance(data, list):
                    return data

            logger.warning(f"   API 调用失败: {method} {url_template[:100]} -> {resp.status_code}")
        except Exception as e:
            logger.debug(f"   API 异常: {e}")

        return None

    async def collect_via_api(self, keyword: str = "广告", max_pages: int = None) -> list:
        """
        Strategy A: 通过发现的 JSON API 采集数据。
        """
        if max_pages is None:
            max_pages = CONFIG["max_pages"]

        all_items = []
        captured_apis = self.api_config.get("captured_apis", [])

        # 筛选可能的列表 API（POST 或包含 search/list 的 URL）
        list_apis = [
            a for a in captured_apis
            if any(kw in a.get("url", "").lower() for kw in
                   ("search", "list", "query", "page", "notice", "announcement", "gg", "pub"))
        ]
        if not list_apis:
            list_apis = captured_apis

        logger.info(f"🔍 尝试 {len(list_apis)} 个候选 API 端点...")

        for api in list_apis[:5]:  # 最多尝试 5 个
            logger.info(f"   测试: {api['method']} {api['url'][:120]}")
            for page in range(1, max_pages + 1):
                items = await self._try_api_endpoint(api, keyword, page)
                if items:
                    all_items.extend(items)
                    logger.info(f"   ✅ 成功! 第{page}页获取 {len(items)} 条")
                    time.sleep(random_delay.__wrapped__(1, 3) if hasattr(random_delay, '__wrapped__') else random_delay(1, 3))
                else:
                    break  # 该 API 不可用

            if all_items:
                logger.info(f"🎯 使用 API: {api['method']} {api['url'][:120]}")
                break

        return all_items

    def collect_via_playwright(
        self, keyword: str = "广告", max_pages: int = None, headless: bool = True
    ) -> list:
        """
        Strategy B: 使用 Playwright 进行页面级采集。

        在页面上操作搜索，解析 HTML 结果列表。
        """
        from playwright.sync_api import sync_playwright

        if max_pages is None:
            max_pages = CONFIG["max_pages"]

        all_items = []

        logger.info("🌐 使用 Playwright 页面级采集...")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random_ua(),
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            page = context.new_page()

            try:
                # 导航到首页
                page.goto(CONFIG["base_url"], wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(3000)

                # 搜索
                self._page_search(page, keyword)

                for pg in range(1, max_pages + 1):
                    logger.info(f"📄 解析第 {pg} 页...")
                    page.wait_for_timeout(2000)

                    # 解析列表
                    items = self._parse_list_html(page.content())
                    for item in items:
                        item["source_page"] = pg
                        if item.get("url"):
                            item["url"] = urljoin(CONFIG["base_url"], item["url"])
                    all_items.extend(items)
                    logger.info(f"   获取 {len(items)} 条")

                    if pg < max_pages:
                        # 翻页
                        if not self._page_next(page):
                            logger.info("   已到最后一页")
                            break
                        time.sleep(random_delay.__wrapped__(1, 3) if hasattr(random_delay, '__wrapped__') else random_delay(1, 3))

            except Exception as e:
                logger.error(f"❌ Playwright 采集出错: {e}")
                import traceback
                traceback.print_exc()
            finally:
                browser.close()

        return all_items

    def _page_search(self, page, keyword: str):
        """在页面上执行搜索操作。"""
        # 使用与 Analyzer 相同的搜索逻辑
        search_selectors = [
            'input[type="search"]', 'input[type="text"]',
            'input[placeholder*="搜索"]', 'input[placeholder*="查询"]',
            'input[name*="keyword"]', 'input[name*="search"]',
            '.el-input__inner', '.ant-input', 'input',
        ]

        for selector in search_selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=1000):
                    el.click()
                    el.fill("")
                    el.fill(keyword)
                    page.wait_for_timeout(1500)

                    btn_selectors = [
                        'button:has-text("搜索")', 'button:has-text("查询")',
                        '.el-button--primary', 'button[type="submit"]',
                    ]
                    for btn_sel in btn_selectors:
                        try:
                            btn = page.locator(btn_sel).first
                            if btn.is_visible(timeout=500):
                                btn.click()
                                page.wait_for_timeout(5000)
                                return
                        except Exception:
                            continue

                    el.press("Enter")
                    page.wait_for_timeout(5000)
                    return
            except Exception:
                continue

        logger.warning("⚠️ 搜索操作失败")

    def _parse_list_html(self, html: str) -> list:
        """解析列表页 HTML，提取招标项目。"""
        soup = BeautifulSoup(html, "lxml")
        items = []

        # 常见的列表结构模式
        list_patterns = [
            # 表格行
            ("table tbody tr", {
                "title": "td:nth-child(2) a, td:nth-child(3) a, td a",
                "date": "td:last-child, td:nth-child(4), td:nth-child(5)",
                "url": "td a[href]",
            }),
            # li 列表
            ("ul.list li, ul.news-list li, ul.result-list li", {
                "title": "a, .title, h3, h4",
                "date": ".date, .time, span:last-child",
                "url": "a[href]",
            }),
            # div 列表
            ("div.list-item, div.news-item, div.result-item, div.announcement-item", {
                "title": "a, .title, h3, h4, .name",
                "date": ".date, .time, .publish-date",
                "url": "a[href]",
            }),
        ]

        for row_selector, field_map in list_patterns:
            rows = soup.select(row_selector)
            if rows:
                for row in rows:
                    try:
                        title_el = row.select_one(field_map["title"])
                        date_el = row.select_one(field_map["date"])
                        url_el = row.select_one(field_map["url"])

                        if title_el:
                            title = title_el.get_text(strip=True)
                            if title and len(title) > 4:
                                items.append({
                                    "title": title,
                                    "publish_date": date_el.get_text(strip=True) if date_el else "",
                                    "url": url_el.get("href", "") if url_el else "",
                                    "source": "caigou.chinatelecom.com.cn",
                                })
                    except Exception:
                        continue

                if items:
                    break  # 找到匹配的列表结构

        return items

    def _page_next(self, page) -> bool:
        """翻到下一页，返回是否成功。"""
        next_selectors = [
            'button:has-text("下一页")', 'a:has-text("下一页")',
            '.el-pagination button:last-child', '.ant-pagination-next',
            'li.next', '.next', 'a:has-text(">")',
            'button:has-text("»")',
        ]

        for selector in next_selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=1000) and el.is_enabled(timeout=500):
                    el.click()
                    page.wait_for_timeout(5000)
                    return True
            except Exception:
                continue

        return False


# ═══════════════════════════════════════════════════════════════
# 模式三：详情页采集
# ═══════════════════════════════════════════════════════════════

async def fetch_detail_async(url: str) -> dict:
    """异步获取详情页内容。"""
    detail = {
        "url": url,
        "title": "",
        "content": "",
        "publish_date": "",
        "error": None,
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30), follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": random_ua(), "Accept": "text/html,application/json"},
            )
            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    data = resp.json()
                    detail["raw"] = json.dumps(data, ensure_ascii=False)
                    if isinstance(data, dict):
                        detail["title"] = data.get("title", data.get("name", ""))
                        detail["content"] = data.get("content", data.get("body", ""))
                        detail["publish_date"] = data.get("publishDate", data.get("date", ""))
                else:
                    soup = BeautifulSoup(resp.text, "lxml")
                    # 提取正文
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()
                    detail["content"] = soup.get_text("\n", strip=True)[:10000]
                    # 提取标题
                    title_tag = soup.select_one("h1, h2, .title, .article-title")
                    if title_tag:
                        detail["title"] = title_tag.get_text(strip=True)
            else:
                detail["error"] = f"HTTP {resp.status_code}"
    except Exception as e:
        detail["error"] = str(e)

    return detail


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def run_analyze_mode(headless: bool = False):
    """运行 API 分析模式。"""
    analyzer = TelecomAPIAnalyzer()
    apis = analyzer.analyze(headless=headless)

    # 保存分析结果
    output_path = analyzer.save_analysis()

    # 打印总结
    print("\n" + "=" * 60)
    print("📊 分析总结")
    print("=" * 60)
    print(f"捕获 API 端点: {len(apis)} 个")
    print(f"Cookie 数量: {len(analyzer.cookies)} 个")
    print(f"结果保存至: {output_path}")

    # 筛选可能的列表 API
    list_candidates = [
        a for a in apis
        if any(kw in a.get("url", "").lower() for kw in ("list", "search", "query", "notice", "announcement"))
    ]
    if list_candidates:
        print(f"\n🎯 候选列表 API ({len(list_candidates)} 个):")
        for a in list_candidates:
            print(f"   {a['method']} {a['url'][:120]}")
            if "response_preview" in a:
                preview = a["response_preview"][:200]
                print(f"   响应预览: {preview}...")

    return apis


def run_collect_mode(keyword: str = "广告", api_analysis_path: str = None):
    """运行数据采集模式（优先使用已确认的直接 API）。"""
    output_dir = Path(CONFIG["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # ✅ 优先使用已确认的直接 API
    logger.info("🎯 使用已确认的直接 API 采集...")
    all_items = fetch_telecom_data_direct(keyword=keyword, max_pages=CONFIG["max_pages"])

    # 也尝试不同公告类型
    for ann_type in CONFIG["announce_types"]:
        if ann_type != "xi9s":
            more = fetch_telecom_data_direct(keyword=keyword, max_pages=2, ann_type=ann_type)
            for item in more:
                if item.get("title") not in {i.get("title") for i in all_items}:
                    all_items.append(item)

    # 如果直接 API 也失败，回退到通用采集器
    if not all_items:
        logger.info("直接 API 未获取数据，回退到通用采集器...")
        collector = TelecomDataCollector(api_analysis_path)
        all_items = asyncio.run(collector.collect_via_api(keyword))
        if not all_items:
            all_items = collector.collect_via_playwright(keyword, headless=True)

    # 过滤广告类
    ad_items = [item for item in all_items if is_ad_keyword(item.get("title", ""))]
    logger.info(f"\n📊 共采集 {len(all_items)} 条，其中广告类 {len(ad_items)} 条")

    # 去重
    seen_titles = set()
    unique = []
    for item in ad_items:
        t = item.get("title", "")
        if t and t not in seen_titles:
            seen_titles.add(t)
            unique.append(item)

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"telecom_data_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    logger.info(f"📁 数据已保存: {output_path}")

    # 打印样例
    print("\n" + "=" * 60)
    print("📋 采集结果样例")
    print("=" * 60)
    for i, item in enumerate(unique[:10]):
        print(f"\n[{i+1}] {item.get('title', 'N/A')}")
        print(f"    日期: {item.get('publish_date', 'N/A')}")
        print(f"    链接: {item.get('url', item.get('detail_url', 'N/A'))}")

    return unique


def run_validate_mode(api_analysis_path: str = None):
    """运行验证测试：连续采集 10 次验证稳定性。"""
    logger.info("=" * 60)
    logger.info("🧪 开始验证测试：连续运行 10 次...")
    logger.info("=" * 60)

    success_count = 0
    total_items = 0

    for i in range(10):
        logger.info(f"\n--- 第 {i+1}/10 次测试 ---")
        try:
            items = fetch_telecom_data_direct(keyword="广告", max_pages=2, page_size=20)
            if items and len(items) > 0:
                success_count += 1
                total_items += len(items)
                logger.info(f"✅ 第 {i+1} 次成功: {len(items)} 条")
            else:
                logger.warning(f"⚠️ 第 {i+1} 次无数据")
        except Exception as e:
            logger.error(f"❌ 第 {i+1} 次失败: {e}")
        time.sleep(2)

    logger.info(f"\n{'='*60}")
    logger.info(f"📊 验证结果: {success_count}/10 次成功")
    logger.info(f"📊 平均每次: {total_items/max(success_count,1):.1f} 条")
    logger.info(f"{'='*60}")


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="中国电信采购平台独立攻关脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 浏览器分析模式（可视化，可观察浏览器操作）
  python telecom_breaker.py --mode analyze

  # 无头浏览器分析模式
  python telecom_breaker.py --mode analyze --headless

  # 数据采集模式（基于分析结果）
  python telecom_breaker.py --mode collect --keyword "广告"

  # 验证测试
  python telecom_breaker.py --mode validate

  # 采集+详情获取
  python telecom_breaker.py --mode collect --keyword "广告" --fetch-detail
        """,
    )
    parser.add_argument(
        "--mode", choices=["analyze", "collect", "validate", "all"],
        default="analyze",
        help="运行模式: analyze=网络分析, collect=数据采集, validate=验证测试, all=全流程",
    )
    parser.add_argument(
        "--keyword", default="广告",
        help="搜索关键词 (默认: 广告)",
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="浏览器无头模式（analyze 模式默认有界面以便观察）",
    )
    parser.add_argument(
        "--api-analysis", default=None,
        help="API 分析结果文件路径（collect/validate 模式使用）",
    )
    parser.add_argument(
        "--fetch-detail", action="store_true",
        help="是否获取详情页内容（collect 模式）",
    )

    args = parser.parse_args()

    # 查找已有的分析文件
    analysis_file = args.api_analysis
    if not analysis_file:
        default_analysis = Path(CONFIG["output_dir"]) / "telecom_api_analysis.json"
        if default_analysis.exists():
            analysis_file = str(default_analysis)

    logger.info("╔══════════════════════════════════════════════════════╗")
    logger.info("║  中国电信采购平台 独立攻关脚本 v1.0                   ║")
    logger.info("║  目标: caigou.chinatelecom.com.cn                     ║")
    logger.info("╚══════════════════════════════════════════════════════╝")
    logger.info(f"运行模式: {args.mode}")

    if args.mode == "analyze":
        run_analyze_mode(headless=args.headless)

    elif args.mode == "collect":
        items = run_collect_mode(args.keyword, analysis_file)

        if args.fetch_detail and items:
            logger.info(f"\n📄 获取 {min(5, len(items))} 条详情...")
            async def fetch_all():
                tasks = [fetch_detail_async(item.get("url", item.get("detail_url", ""))) for item in items[:5]]
                return await asyncio.gather(*tasks)
            details = asyncio.run(fetch_all())
            detail_path = Path(CONFIG["output_dir"]) / f"telecom_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(detail_path, "w", encoding="utf-8") as f:
                json.dump(details, f, ensure_ascii=False, indent=2)
            logger.info(f"📁 详情已保存: {detail_path}")

    elif args.mode == "validate":
        run_validate_mode(analysis_file)

    elif args.mode == "all":
        logger.info("🔄 执行全流程...")
        if not analysis_file:
            run_analyze_mode(headless=args.headless)
            analysis_file = str(Path(CONFIG["output_dir"]) / "telecom_api_analysis.json")
        run_collect_mode(args.keyword, analysis_file)
        run_validate_mode(analysis_file)


if __name__ == "__main__":
    main()
