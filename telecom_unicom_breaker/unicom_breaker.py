"""
╔══════════════════════════════════════════════════════════════╗
║  中国联通采购平台 (chinaunicombidding.cn) 独立攻关脚本        ║
║  Unicom Breaker - 阶段一：技术攻关                           ║
╚══════════════════════════════════════════════════════════════╝

目标：
  1. 分析 UmiJS 框架路由和数据加载机制
  2. 处理 CORS 跨域限制
  3. 找到真实 API 接口
  4. 实现稳定的数据采集

技术难点：
  - UmiJS 路由混淆（/umi.29547abc.js）
  - CORS 限制：access-control-allow-origin: https://inneruscm.chinaunicom.cn
  - X-Frame-Options: SAMEORIGIN
  - JavaScript 代码混淆（$_ts 系列变量）

使用方式：
  # 先运行网络分析模式：
  python unicom_breaker.py --mode analyze

  # 确认 API 后运行采集模式：
  python unicom_breaker.py --mode collect --keyword "广告"
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

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
        logging.FileHandler(LOG_DIR / "unicom_breaker.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("unicom_breaker")

# ─────────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────────
CONFIG = {
    # 中国联通采购平台主域名
    "base_url": "https://www.chinaunicombidding.cn",
    # ✅ 已通过浏览器分析确认的真实 API
    "list_api": "https://www.chinaunicombidding.cn/api/v1/bizAnno/getAnnoList",
    "detail_api": "https://www.chinaunicombidding.cn/api/v1/bizAnno/getAnnoDetail",
    "dict_api": "https://www.chinaunicombidding.cn/api/v1/dict/anno",
    # 公告类型配置
    "anno_types": {
        "BizAnnoVoMtable": "主表格公告",
        "BizAnnoVoBtable": "首页公告",
    },
    # 可能的子域名/路径
    "candidate_urls": [
        "https://www.chinaunicombidding.cn",
    ],
    # 可能的内网 API 地址
    "inner_api_candidates": [],
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
    if min_s is None:
        min_s = CONFIG["min_delay"]
    if max_s is None:
        max_s = CONFIG["max_delay"]
    delay = min_s + (max_s - min_s) * (hash(str(time.time())) % 1000) / 1000.0
    logger.debug(f"等待 {delay:.1f}s...")
    time.sleep(delay)

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
# 模式一：浏览器网络监控分析
# ═══════════════════════════════════════════════════════════════

class UnicomAPIAnalyzer:
    """
    使用 Playwright 启动浏览器，监控所有网络请求，
    分析中国联通采购平台的 UmiJS 框架和 API 接口。

    中国联通采购平台特点：
      - 基于 UmiJS (React 企业级框架)
      - 四个模块：慧采、慧供、慧购、慧问
      - CORS origin: https://inneruscm.chinaunicom.cn
      - JS 混淆: $_ts 系列变量
    """

    def __init__(self):
        self.captured_apis = []
        self.cookies = {}
        self.umi_routes = []
        self.playwright = None
        self.browser = None
        self.page = None

    def _on_request(self, request):
        """拦截所有请求。"""
        url = request.url
        method = request.method
        resource_type = request.resource_type

        # 记录所有 XHR/Fetch 请求
        if resource_type not in ("xhr", "fetch"):
            # 也记录 JS 文件（用于分析 UmiJS 路由）
            if resource_type == "script" and "umi" in url.lower():
                logger.info(f"📜 UmiJS 脚本: {url[:150]}")
                self.umi_routes.append(url)
            return

        # 过滤无关请求
        skip_patterns = [
            "google", "baidu", "hm.baidu", "analytics",
            "beacon", "collect", "track",
        ]
        if any(p in url.lower() for p in skip_patterns):
            return

        headers = dict(request.headers)
        post_data = request.post_data

        captured = {
            "url": url,
            "method": method,
            "headers": {k: v for k, v in headers.items()
                       if k.lower() not in ("user-agent", "accept", "accept-language",
                                            "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform")},
            "post_data": post_data,
            "timestamp": datetime.now().isoformat(),
        }
        self.captured_apis.append(captured)

        logger.info(f"🔍 捕获 API: {method} {url[:150]}")
        if post_data:
            try:
                body = json.loads(post_data) if isinstance(post_data, str) else post_data
                logger.info(f"   Body: {json.dumps(body, ensure_ascii=False)[:200]}")
            except Exception:
                logger.info(f"   Body (raw): {str(post_data)[:200]}")

        # 特别关注 inneruscm.chinaunicom.cn 的请求
        if "inneruscm.chinaunicom.cn" in url:
            logger.info(f"   ⭐ 内网 API 请求!")

    def _on_response(self, response):
        """拦截所有响应。"""
        url = response.url
        resource_type = response.request.resource_type

        if resource_type not in ("xhr", "fetch"):
            return

        for api in reversed(self.captured_apis):
            if api["url"] == url and "response" not in api:
                try:
                    body = response.text()
                    api["response_status"] = response.status
                    api["response_headers"] = dict(response.headers)
                    if len(body) > 5000:
                        api["response_preview"] = body[:2000]
                        api["response_truncated"] = True
                    else:
                        api["response_preview"] = body
                    logger.info(f"📥 响应 {response.status}: {url[:150]} (len={len(body)})")
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
        启动浏览器，分析中国联通采购平台。

        策略：
          1. 先访问外网域名 chinaunicombidding.cn
          2. 尝试搜索操作
          3. 监控是否有内网 API 调用
          4. 分析 UmiJS 路由表
        """
        from playwright.sync_api import sync_playwright

        logger.info("=" * 60)
        logger.info("🚀 启动 Playwright 浏览器，开始分析中国联通采购平台...")
        logger.info(f"   主 URL: {CONFIG['base_url']}")
        logger.info(f"   搜索关键词: {search_keyword}")
        logger.info(f"   无头模式: {headless}")
        logger.info("=" * 60)

        with sync_playwright() as p:
            # 不使用 --disable-web-security，因为需要正确处理 CORS
            # 但添加一些反检测参数
            self.browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--ignore-certificate-errors",
                ],
            )
            context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random_ua(),
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )

            context.on("request", self._on_request)
            context.on("response", self._on_response)

            self.page = context.new_page()

            try:
                # Step 1: 依次尝试多个候选 URL
                logger.info("📄 Step 1: 尝试访问各候选 URL...")
                page_loaded = False
                for url in CONFIG["candidate_urls"]:
                    try:
                        logger.info(f"   尝试: {url}")
                        self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        self.page.wait_for_timeout(5000)

                        # 检查页面是否正常加载
                        title = self.page.title()
                        if title and "联通" in title:
                            logger.info(f"   ✅ 页面标题: {title}")
                            page_loaded = True
                            break
                        elif title:
                            logger.info(f"   页面标题: {title}")
                            # 即使标题不含"联通"也可能正常
                            body_text = self.page.content()[:500]
                            if any(kw in body_text for kw in ["联通", "unicom", "招标", "采购"]):
                                page_loaded = True
                                break
                    except Exception as e:
                        logger.warning(f"   ❌ 访问失败: {e}")

                if not page_loaded:
                    logger.warning("⚠️ 所有候选 URL 均未能确认加载成功，继续分析...")

                # 保存 Cookie
                cookies = context.cookies()
                self.cookies = {c["name"]: c["value"] for c in cookies}
                logger.info(f"   Cookie 数量: {len(cookies)}")
                for c in cookies:
                    logger.info(f"   🍪 {c['name']}: {c['value'][:50]}...")

                # Step 2: 尝试搜索（如果有搜索框）
                logger.info(f"🔍 Step 2: 搜索 '{search_keyword}'...")
                self._try_search(search_keyword)

                # Step 3: 等待异步请求
                logger.info("⏳ Step 3: 等待异步请求...")
                self.page.wait_for_timeout(10000)

                # Step 4: 尝试翻页
                logger.info("📖 Step 4: 尝试翻页...")
                self._try_pagination()
                self.page.wait_for_timeout(5000)

                # Step 5: 尝试点击不同模块
                logger.info("🧭 Step 5: 尝试导航到不同模块...")
                self._try_navigate_modules()

            except Exception as e:
                logger.error(f"❌ 分析过程出错: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.browser.close()

        # 去重
        seen_urls = set()
        unique_apis = []
        for api in self.captured_apis:
            url_key = api["url"].split("?")[0]
            if url_key not in seen_urls:
                seen_urls.add(url_key)
                unique_apis.append(api)

        logger.info(f"\n📊 共捕获 {len(unique_apis)} 个唯一 API 端点:")
        for i, api in enumerate(unique_apis):
            logger.info(f"   [{i+1}] {api['method']} {api['url'][:150]}")
            if "response_preview" in api:
                logger.info(f"       响应: {api['response_preview'][:100]}...")

        logger.info(f"\n📜 UmiJS 路由脚本 ({len(self.umi_routes)} 个):")
        for r in self.umi_routes:
            logger.info(f"   {r[:150]}")

        return unique_apis

    def _try_search(self, keyword: str):
        """尝试在页面上进行搜索。"""
        page = self.page

        search_selectors = [
            'input[type="search"]', 'input[type="text"]',
            'input[placeholder*="搜索"]', 'input[placeholder*="查询"]',
            'input[placeholder*="关键词"]', 'input[name*="keyword"]',
            'input[name*="search"]', 'input[name*="key"]',
            'input[id*="keyword"]', 'input[id*="search"]',
            '.ant-input', 'input',
        ]

        for selector in search_selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=1000):
                    logger.info(f"   找到输入框: {selector}")
                    el.click()
                    el.fill(keyword)
                    page.wait_for_timeout(1500)

                    btn_selectors = [
                        'button:has-text("搜索")', 'button:has-text("查询")',
                        'button:has-text("检索")', 'input[type="submit"]',
                        'button[type="submit"]', '.ant-btn-primary',
                        'button.search-btn',
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

                    el.press("Enter")
                    page.wait_for_timeout(5000)
                    return
            except Exception:
                continue

        logger.warning("   ⚠️ 未找到搜索框")

    def _try_pagination(self):
        """尝试翻页。"""
        page = self.page

        pagination_selectors = [
            'button:has-text("下一页")', 'a:has-text("下一页")',
            '.ant-pagination-next', 'li.next', '.next',
            'button:has-text(">")', 'button:has-text("»")',
        ]

        for selector in pagination_selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=1000) and el.is_enabled(timeout=500):
                    el.click()
                    logger.info(f"   点击翻页: {selector}")
                    page.wait_for_timeout(5000)
                    return
            except Exception:
                continue

    def _try_navigate_modules(self):
        """尝试导航到四个模块：慧采、慧供、慧购、慧问。"""
        page = self.page

        module_names = ["慧采", "慧供", "慧购", "慧问", "中标公告", "采购公告", "招标公告"]
        for name in module_names:
            try:
                el = page.locator(f'text="{name}"').first
                if el.is_visible(timeout=1000):
                    el.click()
                    logger.info(f"   点击模块: {name}")
                    page.wait_for_timeout(5000)
            except Exception:
                continue

    def save_analysis(self, output_path: str = None):
        """保存分析结果。"""
        if output_path is None:
            output_path = str(Path(CONFIG["output_dir"]) / "unicom_api_analysis.json")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        result = {
            "target": "chinaunicombidding.cn",
            "analysis_time": datetime.now().isoformat(),
            "cookies": self.cookies,
            "captured_apis": self.captured_apis,
            "umi_routes": self.umi_routes,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"📁 分析结果已保存到: {output_path}")
        return output_path


# ═══════════════════════════════════════════════════════════════
# Direct API 采集（使用已确认的真实 API）
# ═══════════════════════════════════════════════════════════════

def _get_unicom_token_from_page() -> str:
    """
    从中国联通首页获取动态 token (Ym82oUM4 参数)。

    策略：使用 httpx 获取首页 HTML，从中提取 UmiJS 注入的 token。
    如果 HTML 中找不到，使用 Playwright 快速获取。
    """
    logger.info("🔑 获取动态 token...")

    try:
        resp = httpx.get(
            "https://www.chinaunicombidding.cn/",
            headers={"User-Agent": random_ua()},
            follow_redirects=True,
            timeout=15,
        )
        if resp.status_code == 200:
            html = resp.text
            # 尝试从 HTML 或 JS 中提取 token 模式
            # token 格式: Ym82oUM4={base64_like_string}
            patterns = [
                r'Ym82oUM4=([a-zA-Z0-9_\-]+)',
                r'"token"\s*:\s*"([^"]+)"',
                r'window\.__token__\s*=\s*"([^"]+)"',
            ]
            for pattern in patterns:
                m = re.search(pattern, html)
                if m:
                    token = m.group(1)
                    logger.info(f"   ✅ 从 HTML 提取 token: {token[:30]}...")
                    return token

            # 从 Cookie 中尝试
            cookies = resp.cookies
            for name in ("Ym82oUM4", "token", "auth_token"):
                if name in cookies:
                    logger.info(f"   ✅ 从 Cookie 提取 token")
                    return cookies[name]

            logger.info("   HTML 中未找到 token，将通过首次 API 调用自动获取")
    except Exception as e:
        logger.warning(f"   获取 token 失败: {e}")

    return ""


def fetch_unicom_data_direct(
    keyword: str = "广告",
    max_pages: int = 3,
    page_size: int = 20,
) -> list:
    """
    直接调用已确认的中国联通 API 获取数据。

    API: POST https://www.chinaunicombidding.cn/api/v1/bizAnno/getAnnoList?Ym82oUM4={token}
    参数: {"pageNo": 1, "pageSize": 20, "modeNo": "BizAnnoVoMtable", "annoName": "广告"}

    关键发现：
      - Ym82oUM4 是动态 token，需要从首页获取
      - modeNo 控制数据源：BizAnnoVoMtable=搜索模式, BizAnnoVoBtable=首页展示
      - CORS 限制不影响 httpx 服务端请求
    """
    all_items = []
    seen_ids = set()

    # 获取动态 token
    token = _get_unicom_token_from_page()

    with httpx.Client(
        timeout=httpx.Timeout(30),
        follow_redirects=True,
        headers={
            "User-Agent": random_ua(),
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.chinaunicombidding.cn/",
            "Origin": "https://www.chinaunicombidding.cn",
        },
    ) as client:
        # 访问首页获取完整 Cookie
        logger.info("🍪 访问首页获取 Cookie...")
        try:
            client.get("https://www.chinaunicombidding.cn/", follow_redirects=True)
            random_delay(2, 3)
        except Exception as e:
            logger.warning(f"首页访问失败（继续尝试 API）: {e}")

        # 如果还没有 token，尝试从首页响应中提取
        if not token:
            token = _get_unicom_token_from_page()

        for page in range(1, max_pages + 1):
            body = {
                "pageNo": page,
                "pageSize": page_size,
                "modeNo": "BizAnnoVoMtable",
                "annoName": keyword,
            }

            url = CONFIG["list_api"]
            if token:
                url = f"{url}?Ym82oUM4={token}"

            logger.info(f"📡 请求第 {page} 页: {url[:100]}...")

            for attempt in range(3):
                try:
                    random_delay()
                    resp = client.post(url, json=body)

                    if resp.status_code == 200:
                        # 尝试从响应中提取新 token
                        data = resp.json() if resp.text else {}

                        # 中国联通响应格式
                        if isinstance(data, dict):
                            # 数据可能在 data 字段中（直接数组或包装对象）
                            records = data.get("data", data.get("rows", []))
                            if isinstance(records, dict):
                                records = records.get("records", records.get("list", []))
                            # total 可能在 data 内或顶层
                            data_inner = data.get("data", {}) if isinstance(data.get("data"), dict) else {}
                            total = data.get("total", data_inner.get("total", 0))

                            logger.info(f"   ✅ 第 {page} 页: {len(records) if isinstance(records, list) else 0} 条 (总计 {total})")

                            if isinstance(records, list):
                                for item in records:
                                    item_id = str(item.get("id", item.get("noticeId", "")))
                                    if item_id and item_id not in seen_ids:
                                        seen_ids.add(item_id)
                                        # 字段映射（基于 actual API response）
                                        title = item.get("annoName", item.get("noticeName", item.get("title", "")))
                                        create_date = item.get("createDate", item.get("publishDate", ""))
                                        all_items.append({
                                            "title": title,
                                            "publish_date": str(create_date)[:10] if create_date else "",
                                            "detail_url": (
                                                f"https://www.chinaunicombidding.cn"
                                                f"/detail?id={item_id}"
                                            ),
                                            "notice_type": item.get("annoType", item.get("noticeType", "")),
                                            "province": item.get("provinceName", ""),
                                            "company": item.get("bidCompany", ""),
                                            "procurement_type": item.get("procurementType", ""),
                                            "source": "chinaunicombidding.cn",
                                            "_raw": item,
                                        })

                                # 翻页判断
                                if len(records) < page_size:
                                    logger.info(f"   📄 返回不足一页，停止")
                                    return all_items
                                if total > 0 and page * page_size >= total:
                                    logger.info(f"   📄 已到最后一页 (total={total})")
                                    return all_items
                            break
                    elif resp.status_code == 403 or resp.status_code == 401:
                        # Token 过期，重新获取
                        logger.warning("   Token 过期，重新获取...")
                        token = _get_unicom_token_from_page()
                        url = f"{CONFIG['list_api']}?Ym82oUM4={token}" if token else CONFIG["list_api"]
                    elif resp.status_code == 429:
                        wait = 30 * (2 ** attempt)
                        logger.warning(f"   429 限流，等待 {wait}s")
                        time.sleep(wait)
                    else:
                        logger.warning(f"   HTTP {resp.status_code}: {resp.text[:200]}")
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

class UnicomDataCollector:
    """
    基于 API 分析结果，实现自动化数据采集。
    """

    def __init__(self, api_analysis_path: str = None):
        self.api_config = {}
        self.client: Optional[httpx.AsyncClient] = None

        if api_analysis_path and os.path.exists(api_analysis_path):
            with open(api_analysis_path, "r", encoding="utf-8") as f:
                self.api_config = json.load(f)
            logger.info(f"📂 已加载 API 分析: {api_analysis_path}")

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
                },
            )
        return self.client

    async def _try_api_endpoint(
        self, api_info: dict, keyword: str, page: int = 1
    ) -> Optional[list]:
        """尝试复现 API 调用。"""
        url_template = api_info.get("url", "")
        method = api_info.get("method", "GET")
        headers = api_info.get("headers", {})
        post_data = api_info.get("post_data")

        client = await self._get_client()
        req_headers = dict(client.headers)
        req_headers.update(headers)

        # 中国联通可能需要的特殊请求头
        req_headers.setdefault("Referer", CONFIG["base_url"] + "/")
        req_headers.setdefault("Origin", CONFIG["base_url"])

        try:
            if method == "POST":
                body = {}
                if post_data:
                    try:
                        body = json.loads(post_data) if isinstance(post_data, str) else post_data
                    except Exception:
                        body = {}

                # 替换搜索参数
                for key in ("keyword", "key", "search", "name", "title", "query", "projectName", "noticeName"):
                    if key in body:
                        body[key] = keyword
                        break
                for key in ("page", "pageNum", "current", "pageNo", "pageIndex"):
                    if key in body:
                        body[key] = page
                        break
                for key in ("size", "pageSize", "limit"):
                    if key in body:
                        body[key] = CONFIG["page_size"]
                        break

                resp = await client.post(url_template, json=body, headers=req_headers)
            else:
                resp = await client.get(url_template, headers=req_headers)

            if resp.status_code == 200:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                if isinstance(data, dict):
                    for list_key in ("data", "list", "records", "rows", "content", "items", "result"):
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
        """Strategy A: 通过 API 采集。"""
        if max_pages is None:
            max_pages = CONFIG["max_pages"]

        all_items = []
        captured_apis = self.api_config.get("captured_apis", [])

        list_apis = [
            a for a in captured_apis
            if any(kw in a.get("url", "").lower() for kw in
                   ("search", "list", "query", "notice", "announcement", "bid"))
        ]
        if not list_apis:
            list_apis = captured_apis

        logger.info(f"🔍 尝试 {len(list_apis)} 个候选 API 端点...")

        for api in list_apis[:5]:
            logger.info(f"   测试: {api['method']} {api['url'][:150]}")
            for page in range(1, max_pages + 1):
                items = await self._try_api_endpoint(api, keyword, page)
                if items:
                    all_items.extend(items)
                    logger.info(f"   ✅ 第{page}页获取 {len(items)} 条")
                    time.sleep(2)
                else:
                    break

            if all_items:
                logger.info(f"🎯 使用 API: {api['method']} {api['url'][:150]}")
                break

        return all_items

    def collect_via_playwright(
        self, keyword: str = "广告", max_pages: int = None, headless: bool = True
    ) -> list:
        """Strategy B: Playwright 页面级采集。"""
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
                    "--ignore-certificate-errors",
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
                # 尝试访问
                for url in CONFIG["candidate_urls"][:3]:
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_timeout(3000)
                        if page.title():
                            logger.info(f"   页面加载: {page.title()}")
                            break
                    except Exception:
                        continue

                # 搜索
                self._page_search(page, keyword)

                for pg in range(1, max_pages + 1):
                    logger.info(f"📄 解析第 {pg} 页...")
                    page.wait_for_timeout(2000)

                    items = self._parse_list_html(page.content())
                    for item in items:
                        item["source_page"] = pg
                        if item.get("url"):
                            item["url"] = urljoin(CONFIG["base_url"], item["url"])
                    all_items.extend(items)
                    logger.info(f"   获取 {len(items)} 条")

                    if pg < max_pages and not self._page_next(page):
                        logger.info("   已到最后一页")
                        break
                    time.sleep(2)

            except Exception as e:
                logger.error(f"❌ Playwright 采集出错: {e}")
                import traceback
                traceback.print_exc()
            finally:
                browser.close()

        return all_items

    def _page_search(self, page, keyword: str):
        """在页面上执行搜索。"""
        search_selectors = [
            'input[type="search"]', 'input[type="text"]',
            'input[placeholder*="搜索"]', 'input[placeholder*="查询"]',
            'input[name*="keyword"]', '.ant-input', 'input',
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
                        '.ant-btn-primary', 'button[type="submit"]',
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

    def _parse_list_html(self, html: str) -> list:
        """解析列表页 HTML。"""
        soup = BeautifulSoup(html, "lxml")
        items = []

        # UmiJS 通常使用 Ant Design 组件
        list_patterns = [
            # Ant Design Table
            (".ant-table-tbody tr.ant-table-row", {
                "title": "td:nth-child(2), td:nth-child(3), td a",
                "date": "td:last-child, td:nth-child(4), td:nth-child(5)",
                "url": "td a[href]",
            }),
            # 通用表格
            ("table tbody tr", {
                "title": "td:nth-child(2) a, td:nth-child(3) a, td a",
                "date": "td:last-child, td:nth-child(4)",
                "url": "td a[href]",
            }),
            # 列表
            ("ul li, .list-item, .card-item", {
                "title": "a, .title, h3, h4, span",
                "date": ".date, .time, span:last-child",
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
                                    "source": "chinaunicombidding.cn",
                                })
                    except Exception:
                        continue
                if items:
                    break

        return items

    def _page_next(self, page) -> bool:
        """翻页。"""
        next_selectors = [
            'button:has-text("下一页")', 'a:has-text("下一页")',
            '.ant-pagination-next', 'li.next', '.next',
            'button:has-text(">")', 'button:has-text("»")',
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
# CORS 绕过策略
# ═══════════════════════════════════════════════════════════════

async def test_cors_bypass() -> dict:
    """
    测试 CORS 绕过策略。

    中国联通的 CORS 限制：
      access-control-allow-origin: https://inneruscm.chinaunicom.cn

    绕过方案：
      1. 使用 httpx 直接请求（不经过浏览器 CORS 检查）
      2. 通过代理转发
      3. 使用 Playwright 的 route 拦截修改响应头
    """
    results = {
        "direct_httpx": None,
        "with_origin_header": None,
        "playwright_route": None,
    }

    # 测试 URL（从分析结果获取或使用默认值）
    test_url = "https://www.chinaunicombidding.cn/api/search"

    # 方案 1: httpx 直接请求（不受 CORS 限制）
    logger.info("🧪 测试 httpx 直接请求...")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15), follow_redirects=True) as client:
            resp = await client.get(
                test_url,
                headers={
                    "User-Agent": random_ua(),
                    "Accept": "application/json",
                    "Origin": CONFIG["base_url"],
                    "Referer": CONFIG["base_url"] + "/",
                },
            )
            results["direct_httpx"] = {
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "body_preview": resp.text[:500],
            }
            logger.info(f"   httpx 直接请求: HTTP {resp.status_code}")
    except Exception as e:
        results["direct_httpx"] = {"error": str(e)}
        logger.warning(f"   httpx 失败: {e}")

    # 方案 2: 添加 Origin 头模拟合法来源
    logger.info("🧪 测试带特殊请求头...")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15), follow_redirects=True) as client:
            resp = await client.get(
                test_url,
                headers={
                    "User-Agent": random_ua(),
                    "Accept": "application/json",
                    "Origin": "https://inneruscm.chinaunicom.cn",
                    "Referer": "https://inneruscm.chinaunicom.cn/",
                    "Host": urlparse(test_url).hostname,
                },
            )
            results["with_origin_header"] = {
                "status": resp.status_code,
                "body_preview": resp.text[:500],
            }
            logger.info(f"   带 Origin 头: HTTP {resp.status_code}")
    except Exception as e:
        results["with_origin_header"] = {"error": str(e)}
        logger.warning(f"   失败: {e}")

    return results


def run_playwright_cors_test():
    """使用 Playwright route 拦截测试 CORS。"""
    from playwright.sync_api import sync_playwright

    logger.info("🧪 使用 Playwright route 拦截测试 CORS...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 拦截响应，移除 CORS 限制
        def handle_route(route):
            response = route.fetch()
            # 移除 X-Frame-Options
            headers = dict(response.headers)
            headers.pop("x-frame-options", None)
            headers.pop("X-Frame-Options", None)
            # 添加宽松的 CORS 头
            headers["access-control-allow-origin"] = "*"
            headers["access-control-allow-methods"] = "GET, POST, OPTIONS"
            headers["access-control-allow-headers"] = "*"
            route.fulfill(response=response, headers=headers)

        page.route("**/*", handle_route)

        try:
            page.goto(CONFIG["base_url"], wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            page_text = page.content()[:500]
            logger.info(f"   Playwright 页面访问成功: {page_text[:100]}...")
        except Exception as e:
            logger.error(f"   Playwright 测试失败: {e}")
        finally:
            browser.close()


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def run_analyze_mode(headless: bool = False):
    """运行 API 分析模式。"""
    analyzer = UnicomAPIAnalyzer()
    apis = analyzer.analyze(headless=headless)
    analyzer.save_analysis()

    print("\n" + "=" * 60)
    print("📊 中国联通平台分析总结")
    print("=" * 60)
    print(f"捕获 API 端点: {len(apis)} 个")
    print(f"UmiJS 脚本: {len(analyzer.umi_routes)} 个")
    print(f"Cookie 数量: {len(analyzer.cookies)} 个")

    return apis


def run_collect_mode(keyword: str = "广告", api_analysis_path: str = None):
    """运行数据采集模式（优先使用已确认的直接 API）。"""
    output_dir = Path(CONFIG["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # ✅ 优先使用已确认的直接 API
    logger.info("🎯 使用已确认的直接 API 采集...")
    all_items = fetch_unicom_data_direct(keyword=keyword, max_pages=CONFIG["max_pages"])

    # 如果直接 API 失败，回退到通用采集器
    if not all_items:
        logger.info("直接 API 未获取数据，回退到通用采集器...")
        collector = UnicomDataCollector(api_analysis_path)
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

    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"unicom_data_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    logger.info(f"📁 数据已保存: {output_path}")

    # 打印
    print("\n" + "=" * 60)
    print("📋 采集结果样例")
    print("=" * 60)
    for i, item in enumerate(unique[:10]):
        print(f"\n[{i+1}] {item.get('title', 'N/A')}")
        print(f"    日期: {item.get('publish_date', 'N/A')}")
        print(f"    链接: {item.get('url', 'N/A')}")

    return unique


def run_validate_mode(api_analysis_path: str = None):
    """验证测试。"""
    logger.info("=" * 60)
    logger.info("🧪 开始验证测试：连续运行 10 次...")
    logger.info("=" * 60)

    success_count = 0
    total_items = 0

    for i in range(10):
        logger.info(f"\n--- 第 {i+1}/10 次测试 ---")
        try:
            items = fetch_unicom_data_direct(keyword="广告", max_pages=2, page_size=20)
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


def run_cors_test():
    """运行 CORS 绕过测试。"""
    logger.info("=" * 60)
    logger.info("🧪 CORS 绕过策略测试")
    logger.info("=" * 60)

    # httpx 测试
    results = asyncio.run(test_cors_bypass())
    print("\n📊 httpx 测试结果:")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # Playwright 测试
    run_playwright_cors_test()


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="中国联通采购平台独立攻关脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 浏览器分析模式（推荐先用这个）
  python unicom_breaker.py --mode analyze

  # 无头浏览器分析
  python unicom_breaker.py --mode analyze --headless

  # CORS 绕过测试
  python unicom_breaker.py --mode cors-test

  # 数据采集模式
  python unicom_breaker.py --mode collect --keyword "广告"

  # 验证测试
  python unicom_breaker.py --mode validate

  # 全流程
  python unicom_breaker.py --mode all
        """,
    )
    parser.add_argument(
        "--mode", choices=["analyze", "collect", "validate", "cors-test", "all"],
        default="analyze",
        help="运行模式",
    )
    parser.add_argument("--keyword", default="广告", help="搜索关键词")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--api-analysis", default=None, help="API 分析文件路径")

    args = parser.parse_args()

    analysis_file = args.api_analysis
    if not analysis_file:
        default_analysis = Path(CONFIG["output_dir"]) / "unicom_api_analysis.json"
        if default_analysis.exists():
            analysis_file = str(default_analysis)

    logger.info("╔══════════════════════════════════════════════════════╗")
    logger.info("║  中国联通采购平台 独立攻关脚本 v1.0                   ║")
    logger.info("║  目标: chinaunicombidding.cn                          ║")
    logger.info("╚══════════════════════════════════════════════════════╝")
    logger.info(f"运行模式: {args.mode}")

    if args.mode == "analyze":
        run_analyze_mode(headless=args.headless)

    elif args.mode == "collect":
        run_collect_mode(args.keyword, analysis_file)

    elif args.mode == "validate":
        run_validate_mode(analysis_file)

    elif args.mode == "cors-test":
        run_cors_test()

    elif args.mode == "all":
        logger.info("🔄 执行全流程...")
        if not analysis_file:
            run_analyze_mode(headless=args.headless)
            analysis_file = str(Path(CONFIG["output_dir"]) / "unicom_api_analysis.json")
        run_collect_mode(args.keyword, analysis_file)
        run_validate_mode(analysis_file)


if __name__ == "__main__":
    main()
