"""
浏览器自动化爬虫（轻量封装）

基于 Crawl4AI 的 headless Chromium 提供：
  - 复杂交互页面抓取（登录、翻页、表单提交）
  - 截图/PDF 导出
  - JavaScript 执行
  - 作为现有适配器的 fallback

依赖：
  crawl4ai（已有）
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BrowserResult:
    """浏览器操作结果"""
    url: str
    success: bool
    markdown: str = ""
    screenshot_base64: str = ""
    error: str = ""


class BrowserCrawler:
    """
    浏览器自动化爬虫。

    基于 Crawl4AI 的 headless Chromium，
    用于处理需要 JS 渲染或复杂交互的招标网站。

    Usage:
        crawler = BrowserCrawler()
        results = await crawler.batch_fetch([
            "https://example.com/bid/1",
            "https://example.com/bid/2",
        ])
    """

    def __init__(self, timeout: int = 30, headless: bool = True):
        self.timeout = timeout
        self.headless = headless

    async def fetch_page(self, url: str) -> BrowserResult:
        """抓取单个页面（JS 渲染后提取 Markdown）。"""
        try:
            from app.services.crawler.ai_fetcher import AIBiddingFetcher

            fetcher = AIBiddingFetcher(
                headless=self.headless,
                timeout=self.timeout,
                max_concurrent=1,
            )
            batch = await fetcher.crawl_urls([url])

            if batch.successful_count > 0:
                r = batch.results[0]
                return BrowserResult(
                    url=url,
                    success=True,
                    markdown=r.markdown,
                )
            else:
                error = batch.results[0].error_message if batch.results else "Unknown"
                return BrowserResult(url=url, success=False, error=error)

        except Exception as e:
            return BrowserResult(url=url, success=False, error=str(e))

    async def batch_fetch(self, urls: List[str]) -> List[BrowserResult]:
        """批量抓取多个页面。"""
        try:
            from app.services.crawler.ai_fetcher import AIBiddingFetcher

            fetcher = AIBiddingFetcher(
                headless=self.headless,
                timeout=self.timeout,
                max_concurrent=3,
            )
            batch = await fetcher.crawl_urls(urls)

            results = []
            for r in batch.results:
                results.append(
                    BrowserResult(
                        url=r.url,
                        success=r.success,
                        markdown=r.markdown,
                        error=r.error_message if not r.success else "",
                    )
                )
            return results

        except Exception as e:
            return [
                BrowserResult(url=url, success=False, error=str(e))
                for url in urls
            ]

    async def fallback_fetch(
        self,
        url: str,
        html: str = "",
    ) -> Optional[str]:
        """
        Fallback 模式：当传统 HTTP 抓取失败时，
        用浏览器渲染获取内容。

        Args:
            url: 目标 URL
            html: 传统模式获取的（可能不完整的）HTML

        Returns:
            Markdown 内容，或 None
        """
        logger.info(f"🔄 浏览器 fallback: {url[:100]}")
        result = await self.fetch_page(url)
        return result.markdown if result.success else None
