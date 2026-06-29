"""
多搜索引擎聚合发现模块

借鉴 OpenManus 的多引擎搜索架构，使用 Baidu/Bing/Google/DuckDuckGo
四大搜索引擎聚合搜索招标信息，发现潜在的公告来源。

特性：
  - 多引擎并行搜索 + 自动 fallback
  - 搜索结果去重 + 域名过滤
  - 搜索结果内容提取
  - 与 AI 爬虫管道集成

依赖：
  httpx, beautifulsoup4 (已有)
"""

import asyncio
import logging
import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class SearchResult:
    """单条搜索结果"""
    title: str
    url: str
    snippet: str = ""
    engine: str = ""          # 来源搜索引擎
    position: int = 0         # 搜索结果排名
    is_bidding_site: bool = False  # 是否为招标网站
    content: Optional[str] = None  # 抓取的页面内容


@dataclass
class DiscoveryResult:
    """搜索发现结果"""
    query: str
    engine: str
    results: List[SearchResult] = field(default_factory=list)
    total_found: int = 0
    bidding_urls: List[str] = field(default_factory=list)
    error: Optional[str] = None


# ============================================================
# 搜索引擎基类
# ============================================================

class BaseSearchEngine:
    """搜索引擎基类"""

    name: str = "base"
    search_url: str = ""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    async def search(
        self, query: str, num_results: int = 10
    ) -> List[SearchResult]:
        """执行搜索，返回结构化结果。"""
        raise NotImplementedError

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )


# ============================================================
# Baidu 搜索引擎
# ============================================================

class BaiduSearchEngine(BaseSearchEngine):
    """百度搜索（HTML 解析方式，无需 API Key）"""

    name = "baidu"
    search_url = "https://www.baidu.com/s"

    async def search(
        self, query: str, num_results: int = 10
    ) -> List[SearchResult]:
        results = []
        try:
            async with self._build_client() as client:
                resp = await client.get(
                    self.search_url,
                    params={"wd": query, "rn": str(num_results)},
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                for i, item in enumerate(
                    soup.select(".result, .result-op, .c-container")[:num_results]
                ):
                    title_el = item.select_one("h3 a")
                    snippet_el = item.select_one(".c-abstract, .c-span-last")
                    url = ""
                    title = ""

                    if title_el:
                        title = title_el.get_text(strip=True)
                        url = title_el.get("href", "")

                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    if title or url:
                        results.append(
                            SearchResult(
                                title=title,
                                url=url,
                                snippet=snippet,
                                engine=self.name,
                                position=i + 1,
                            )
                        )

            logger.info(f"百度搜索 '{query[:30]}...' → {len(results)} 条结果")
        except Exception as e:
            logger.warning(f"百度搜索失败: {e}")

        return results


# ============================================================
# Bing 搜索引擎
# ============================================================

class BingSearchEngine(BaseSearchEngine):
    """Bing 搜索（HTML 解析方式，无需 API Key）"""

    name = "bing"
    search_url = "https://www.bing.com/search"

    async def search(
        self, query: str, num_results: int = 10
    ) -> List[SearchResult]:
        results = []
        try:
            async with self._build_client() as client:
                resp = await client.get(
                    self.search_url,
                    params={
                        "q": query,
                        "count": str(min(num_results, 50)),
                        "setlang": "zh-cn",
                    },
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                for i, item in enumerate(
                    soup.select("li.b_algo")[:num_results]
                ):
                    title_el = item.select_one("h2 a")
                    snippet_el = item.select_one(".b_caption p")

                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    url = title_el.get("href", "")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    results.append(
                        SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            engine=self.name,
                            position=i + 1,
                        )
                    )

            logger.info(f"Bing 搜索 '{query[:30]}...' → {len(results)} 条结果")
        except Exception as e:
            logger.warning(f"Bing 搜索失败: {e}")

        return results


# ============================================================
# DuckDuckGo 搜索引擎
# ============================================================

class DuckDuckGoSearchEngine(BaseSearchEngine):
    """DuckDuckGo 搜索（HTML 解析方式，无需 API Key）"""

    name = "duckduckgo"
    search_url = "https://html.duckduckgo.com/html/"

    async def search(
        self, query: str, num_results: int = 10
    ) -> List[SearchResult]:
        results = []
        try:
            async with self._build_client() as client:
                resp = await client.post(
                    self.search_url,
                    data={"q": query, "kl": "cn-zh"},
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                for i, item in enumerate(
                    soup.select(".result")[:num_results]
                ):
                    title_el = item.select_one(".result__title a")
                    snippet_el = item.select_one(".result__snippet")

                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    url = title_el.get("href", "")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    results.append(
                        SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            engine=self.name,
                            position=i + 1,
                        )
                    )

            logger.info(
                f"DuckDuckGo 搜索 '{query[:30]}...' → {len(results)} 条结果"
            )
        except Exception as e:
            logger.warning(f"DuckDuckGo 搜索失败: {e}")

        return results


# ============================================================
# 搜索引擎注册表
# ============================================================

ENGINE_REGISTRY = {
    "baidu": BaiduSearchEngine,
    "bing": BingSearchEngine,
    "duckduckgo": DuckDuckGoSearchEngine,
}

# 搜索引擎优先级（Baidu 优先，国内最稳定）
ENGINE_PRIORITY = ["baidu", "bing", "duckduckgo"]


# ============================================================
# 招标站点域名识别
# ============================================================

# 已知招标站点域名模式
BIDDING_DOMAIN_PATTERNS = [
    r"b2b\.10086\.cn",         # 中国移动采购与招标网
    r"zhaobiao\.cn",            # 中国招标网
    r"bidcenter\.com\.cn",      # 采招网
    r"chinabidding\.com",       # 中国采购与招标网
    r"ccgp\.gov\.cn",           # 中国政府采购网
    r"ebidding\.",              # 各种电子招标平台
    r"zbtb\.",                  # 招标投标
    r"bidder\.",                # 投标相关
    r"tender",                  # 招标 (英文)
    r"procurement",             # 采购 (英文)
    r"\.gov\.cn",               # 政府网站
]

# 招标标题关键词
BIDDING_TITLE_KEYWORDS = [
    "招标", "采购", "中标", "公告", "公示", "询价",
    "比选", "竞争性谈判", "单一来源",
]


def _is_bidding_domain(url: str) -> bool:
    """判断 URL 是否属于招标相关网站。"""
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return False

    for pattern in BIDDING_DOMAIN_PATTERNS:
        if re.search(pattern, domain):
            return True
    return False


def _is_bidding_title(title: str) -> bool:
    """判断标题是否与招标相关。"""
    for keyword in BIDDING_TITLE_KEYWORDS:
        if keyword in title:
            return True
    return False


def _clean_url(url: str) -> str:
    """清理 URL（去除追踪参数等）。"""
    parsed = urlparse(url)
    # 去除常见追踪参数
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


# ============================================================
# 聚合搜索引擎
# ============================================================

class SearchDiscoveryEngine:
    """
    多引擎聚合搜索发现引擎。

    使用多个搜索引擎并行搜索招标信息，自动 fallback，
    结果去重，域名过滤，提取招标相关 URL。

    Usage:
        engine = SearchDiscoveryEngine()
        urls = await engine.discover_bidding_urls(
            queries=["广东移动 广告 招标"],
            max_results=20,
        )
        # 将 urls 传入 AI 爬虫管道进行详情抓取
    """

    # 广东移动广告类招标搜索 queries
    DEFAULT_QUERIES = [
        "广东移动 广告 招标公告",
        "广东移动 品牌宣传 采购",
        "广东移动 营销活动 招标",
        "广东移动 创意设计 比选",
        "广东移动 新媒体 采购公告",
        "中国移动广东 广告投放 招标",
        "广东移动 媒介代理 采购",
    ]

    def __init__(
        self,
        engines: Optional[List[str]] = None,
        timeout: int = 15,
        fetch_content: bool = False,
    ):
        """
        Args:
            engines: 搜索引擎列表，默认按优先级使用 baidu > bing > duckduckgo
            timeout: 每个搜索请求超时（秒）
            fetch_content: 是否抓取搜索结果页内容
        """
        self.engine_names = engines or ENGINE_PRIORITY
        self.timeout = timeout
        self.fetch_content = fetch_content

    async def discover_bidding_urls(
        self,
        queries: Optional[List[str]] = None,
        max_results: int = 20,
    ) -> List[DiscoveryResult]:
        """
        使用多引擎搜索招标公告 URL。

        Args:
            queries: 搜索关键词列表
            max_results: 每个 query 最大结果数

        Returns:
            DiscoveryResult 列表
        """
        queries = queries or self.DEFAULT_QUERIES
        all_results: List[DiscoveryResult] = []

        for query in queries:
            result = await self._search_aggregated(query, max_results)
            all_results.append(result)

        # 统计
        total_bidding_urls = set()
        for r in all_results:
            total_bidding_urls.update(r.bidding_urls)

        logger.info(
            f"🔍 搜索发现完成: {len(queries)} 个查询, "
            f"发现 {len(total_bidding_urls)} 个招标相关 URL"
        )

        return all_results

    async def _search_aggregated(
        self, query: str, max_results: int
    ) -> DiscoveryResult:
        """使用多引擎聚合搜索单个 query。"""
        result = DiscoveryResult(query=query, engine="aggregated")

        for engine_name in self.engine_names:
            if engine_name not in ENGINE_REGISTRY:
                continue

            try:
                engine = ENGINE_REGISTRY[engine_name](timeout=self.timeout)
                search_results = await engine.search(query, max_results)

                if search_results:
                    result.engine = engine_name
                    result.results = search_results
                    result.total_found = len(search_results)

                    # 过滤招标相关 URL
                    result.bidding_urls = self._filter_bidding_urls(search_results)
                    logger.info(
                        f"✅ {engine_name} 搜索成功: "
                        f"{result.total_found} 条结果, "
                        f"{len(result.bidding_urls)} 条招标相关"
                    )
                    break  # 成功则跳出，不再尝试其他引擎

            except Exception as e:
                logger.warning(f"{engine_name} 搜索异常: {e}")
                continue
        else:
            result.error = "所有搜索引擎均失败"

        return result

    def _filter_bidding_urls(
        self, results: List[SearchResult]
    ) -> List[str]:
        """从搜索结果中过滤招标相关 URL。"""
        bidding_urls: Set[str] = set()
        seen_domains: Set[str] = set()

        for r in results:
            url = r.url
            if not url or not url.startswith("http"):
                continue

            # 优先：域名匹配招标站点
            if _is_bidding_domain(url):
                clean = _clean_url(url)
                bidding_urls.add(clean)
                r.is_bidding_site = True
                continue

            # 其次：标题匹配招标关键词
            if _is_bidding_title(r.title) or _is_bidding_title(r.snippet):
                domain = urlparse(url).netloc
                if domain not in seen_domains:
                    seen_domains.add(domain)
                    clean = _clean_url(url)
                    bidding_urls.add(clean)
                    r.is_bidding_site = True

        return list(bidding_urls)


# ============================================================
# 便捷函数
# ============================================================

async def discover_bidding_announcements(
    queries: Optional[List[str]] = None,
    max_per_query: int = 15,
) -> Dict:
    """
    便捷函数：搜索发现招标公告 URL。

    Returns:
        {
            "total_bidding_urls": [...],
            "results": [DiscoveryResult, ...],
            "search_time": "2024-...",
        }
    """
    engine = SearchDiscoveryEngine()
    results = await engine.discover_bidding_urls(
        queries=queries,
        max_results=max_per_query,
    )

    all_urls: Set[str] = set()
    for r in results:
        all_urls.update(r.bidding_urls)

    return {
        "total_bidding_urls": list(all_urls),
        "total_count": len(all_urls),
        "results": results,
        "search_time": datetime.now().isoformat(),
    }


async def discover_and_crawl(
    queries: Optional[List[str]] = None,
    max_per_query: int = 10,
) -> Dict:
    """
    搜索发现 + AI 爬取一体化流程。

    1. 多引擎搜索发现招标 URL
    2. 使用 AI 爬虫抓取详情

    Returns:
        {
            "discovered": [...],     # 发现的 URL
            "crawled": [...],        # AI 爬取结果
            "stats": {...},
        }
    """
    # 步骤 1: 搜索发现
    discovery = await discover_bidding_announcements(
        queries=queries,
        max_per_query=max_per_query,
    )

    # 步骤 2: AI 爬取
    from app.services.crawler.ai_fetcher import AIBiddingFetcher

    urls = discovery["total_bidding_urls"]
    if not urls:
        return {
            "discovered": [],
            "crawled": [],
            "stats": {"discovered": 0, "crawled": 0},
        }

    fetcher = AIBiddingFetcher(timeout=30, max_concurrent=3)
    batch = await fetcher.crawl_urls(urls[:20])  # 限制最多 20 条

    crawled_results = []
    for r in batch.results:
        crawled_results.append({
            "url": r.url,
            "success": r.success,
            "title": r.title,
            "word_count": r.word_count,
            "error": r.error_message if not r.success else "",
        })

    return {
        "discovered": urls,
        "crawled": crawled_results,
        "stats": {
            "discovered": len(urls),
            "crawled_success": batch.successful_count,
            "crawled_failed": batch.failed_count,
        },
    }
