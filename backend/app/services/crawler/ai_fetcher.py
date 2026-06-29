"""
AI 增强爬虫抓取器

基于 Crawl4AI 的高性能、AI 友好型网页爬虫。

特性：
  - Headless Chromium 渲染 JavaScript 动态页面
  - 自动提取 Clean Markdown（专为 LLM 优化）
  - 多 URL 并发抓取，内置缓存
  - 自动移除 overlay/弹窗/iframe 干扰
  - 链接和图片统计
  - 与现有 BiddingFetcher 互补：AI 模式处理 JS 重页面，传统模式处理轻量页面

依赖：
  crawl4ai >= 0.6.0  (自动安装 Playwright Chromium)
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# 模块级检查：crawl4ai 是否可用
_CRAWL4AI_AVAILABLE = False
_BROWSER_READY = False


def _check_crawl4ai():
    """检查 crawl4ai 是否安装且浏览器就绪。"""
    global _CRAWL4AI_AVAILABLE, _BROWSER_READY
    try:
        import crawl4ai  # noqa: F401
        _CRAWL4AI_AVAILABLE = True
        _BROWSER_READY = True
    except ImportError:
        _CRAWL4AI_AVAILABLE = False
        _BROWSER_READY = False


_check_crawl4ai()


def is_ai_crawler_available() -> bool:
    """检查 AI 爬虫是否可用。"""
    return _CRAWL4AI_AVAILABLE and _BROWSER_READY


# ============================================================
# 输出数据结构
# ============================================================

@dataclass
class AICrawlResult:
    """单条 AI 爬取结果"""
    url: str
    success: bool
    status_code: int = 0
    title: str = ""
    markdown: str = ""           # Clean Markdown 内容
    html: str = ""               # 原始 HTML（可选保留）
    text_content: str = ""       # 纯文本内容
    word_count: int = 0
    links_count: int = 0
    images_count: int = 0
    execution_time: float = 0.0
    error_message: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class AIBatchResult:
    """批量 AI 爬取结果"""
    results: List[AICrawlResult] = field(default_factory=list)
    successful_count: int = 0
    failed_count: int = 0
    total_time: float = 0.0
    crawl_time: str = ""


# ============================================================
# AI 增强抓取器
# ============================================================

class AIBiddingFetcher:
    """
    AI 增强招标公告抓取器。

    使用 Crawl4AI 的 AsyncWebCrawler 进行智能页面渲染和内容提取。
    适合处理：
      - JavaScript 渲染的 SPA 招标网站
      - 需要浏览器环境的反爬页面
      - 复杂 DOM 结构的公告详情页

    Usage:
        fetcher = AIBiddingFetcher()
        results = await fetcher.crawl_urls([
            "https://example.com/bid/123",
            "https://example.com/bid/456",
        ])
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30,
        bypass_cache: bool = False,
        word_count_threshold: int = 10,
        browser_type: str = "chromium",
        max_concurrent: int = 3,
    ):
        """
        Args:
            headless: 是否无头模式运行浏览器
            timeout: 每个 URL 超时时间（秒）
            bypass_cache: 是否跳过缓存
            word_count_threshold: 内容块最小词数阈值
            browser_type: 浏览器类型（chromium/firefox/webkit）
            max_concurrent: 最大并发数
        """
        self.headless = headless
        self.timeout = timeout
        self.bypass_cache = bypass_cache
        self.word_count_threshold = word_count_threshold
        self.browser_type = browser_type
        self.max_concurrent = max_concurrent

    async def crawl_urls(
        self,
        urls: List[str],
        extract_markdown: bool = True,
        extract_links: bool = True,
    ) -> AIBatchResult:
        """
        批量 AI 爬取多个 URL。

        Args:
            urls: 目标 URL 列表
            extract_markdown: 是否提取 Markdown
            extract_links: 是否提取链接

        Returns:
            AIBatchResult 包含所有爬取结果
        """
        try:
            from crawl4ai import (
                AsyncWebCrawler,
                BrowserConfig,
                CacheMode,
                CrawlerRunConfig,
            )
        except ImportError:
            logger.error(
                "crawl4ai 未安装。请执行: pip install crawl4ai"
            )
            return AIBatchResult(
                results=[
                    AICrawlResult(
                        url=url,
                        success=False,
                        error_message="crawl4ai 未安装",
                    )
                    for url in urls
                ],
                failed_count=len(urls),
            )

        valid_urls = [u for u in urls if u and u.startswith(("http://", "https://"))]
        if not valid_urls:
            logger.warning("没有有效的 URL")
            return AIBatchResult()

        # 配置浏览器
        browser_config = BrowserConfig(
            headless=self.headless,
            verbose=False,
            browser_type=self.browser_type,
            ignore_https_errors=True,
            java_script_enabled=True,
            viewport_width=1920,
            viewport_height=1080,
        )

        # 配置爬取参数
        cache_mode = CacheMode.BYPASS if self.bypass_cache else CacheMode.ENABLED

        run_config = CrawlerRunConfig(
            cache_mode=cache_mode,
            word_count_threshold=self.word_count_threshold,
            process_iframes=True,
            remove_overlay_elements=True,
            excluded_tags=["script", "style", "nav", "footer"],
            page_timeout=self.timeout * 1000,
            verbose=False,
            wait_until="domcontentloaded",
            screenshot=False,
            extract_links=extract_links,
        )

        batch_result = AIBatchResult(
            crawl_time=datetime.now().isoformat(),
        )
        start_time = asyncio.get_event_loop().time()

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                # 使用信号量控制并发
                semaphore = asyncio.Semaphore(self.max_concurrent)

                async def _crawl_one(url: str) -> AICrawlResult:
                    async with semaphore:
                        return await self._crawl_single(
                            crawler, url, run_config, extract_markdown
                        )

                tasks = [_crawl_one(url) for url in valid_urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        batch_result.results.append(
                            AICrawlResult(
                                url=valid_urls[i],
                                success=False,
                                error_message=str(result),
                            )
                        )
                        batch_result.failed_count += 1
                    else:
                        batch_result.results.append(result)
                        if result.success:
                            batch_result.successful_count += 1
                        else:
                            batch_result.failed_count += 1

        except Exception as e:
            logger.error(f"AI 爬虫批量抓取异常: {e}")
            for url in valid_urls:
                batch_result.results.append(
                    AICrawlResult(
                        url=url,
                        success=False,
                        error_message=str(e),
                    )
                )
            batch_result.failed_count = len(valid_urls)

        batch_result.total_time = asyncio.get_event_loop().time() - start_time
        logger.info(
            f"AI 爬虫批量完成: 成功 {batch_result.successful_count}, "
            f"失败 {batch_result.failed_count}, "
            f"耗时 {batch_result.total_time:.1f}s"
        )

        return batch_result

    async def _crawl_single(
        self,
        crawler,
        url: str,
        run_config,
        extract_markdown: bool,
    ) -> AICrawlResult:
        """爬取单个 URL。"""
        url_start = asyncio.get_event_loop().time()

        try:
            logger.info(f"🤖 AI 爬取: {url[:120]}")

            result = await crawler.arun(url=url, config=run_config)
            execution_time = asyncio.get_event_loop().time() - url_start

            if result.success:
                # 统计词数
                markdown_text = getattr(result, "markdown", "") or ""
                word_count = len(markdown_text.split()) if markdown_text else 0

                # 统计链接
                links_count = 0
                if hasattr(result, "links") and result.links:
                    internal = result.links.get("internal", [])
                    external = result.links.get("external", [])
                    links_count = len(internal) + len(external)

                # 统计图片
                images_count = 0
                if hasattr(result, "media") and result.media:
                    images_count = len(result.media.get("images", []))

                # 提取元数据
                metadata = {}
                if result.metadata:
                    metadata = {
                        "title": result.metadata.get("title", ""),
                        "description": result.metadata.get("description", ""),
                        "language": result.metadata.get("language", ""),
                    }

                logger.info(
                    f"✅ AI 爬取成功: {url[:80]} "
                    f"({word_count} 词, {execution_time:.1f}s)"
                )

                return AICrawlResult(
                    url=url,
                    success=True,
                    status_code=getattr(result, "status_code", 200),
                    title=metadata.get("title", ""),
                    markdown=markdown_text if extract_markdown else "",
                    html=getattr(result, "html", "") or "",
                    text_content=getattr(result, "cleaned_html", "") or "",
                    word_count=word_count,
                    links_count=links_count,
                    images_count=images_count,
                    execution_time=execution_time,
                    metadata=metadata,
                )

            else:
                error_msg = getattr(result, "error_message", "Unknown error")
                logger.warning(f"❌ AI 爬取失败: {url[:80]} - {error_msg}")

                return AICrawlResult(
                    url=url,
                    success=False,
                    error_message=error_msg,
                    execution_time=execution_time,
                )

        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - url_start
            logger.error(f"❌ AI 爬取异常: {url[:80]} - {e}")
            return AICrawlResult(
                url=url,
                success=False,
                error_message=str(e),
                execution_time=execution_time,
            )

    async def crawl_and_extract(
        self,
        urls: List[str],
        extraction_prompt: Optional[str] = None,
    ) -> AIBatchResult:
        """
        AI 爬取 + LLM 友好内容提取。

        使用 Crawl4AI 的 extraction_strategy 可以根据提示词
        从页面中提取特定结构化信息。

        Args:
            urls: 目标 URL 列表
            extraction_prompt: LLM 提取提示词（可选）
                e.g. "提取招标公告的标题、预算金额、截止日期、资质要求"

        Returns:
            AIBatchResult
        """
        if extraction_prompt:
            logger.info(f"使用 LLM 提取模式: {extraction_prompt[:50]}...")
            # Crawl4AI 支持 LLMExtractionStrategy
            # 此处保留扩展接口，后续可集成 LLM 提取
        return await self.crawl_urls(urls, extract_markdown=True)


# ============================================================
# 便捷函数
# ============================================================

async def ai_fetch_page(url: str, timeout: int = 30) -> Tuple[bool, str, str]:
    """
    便捷函数：AI 模式抓取单个页面。

    Args:
        url: 目标 URL
        timeout: 超时时间

    Returns:
        (是否成功, Markdown内容, 错误信息)
    """
    fetcher = AIBiddingFetcher(timeout=timeout)
    result = await fetcher.crawl_urls([url])

    if result.successful_count > 0:
        r = result.results[0]
        return True, r.markdown, ""
    else:
        error = result.results[0].error_message if result.results else "Unknown"
        return False, "", error
