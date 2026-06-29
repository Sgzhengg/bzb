"""
爬虫主控管道模块

负责编排整个采集流程：
  列表页翻页 → 详情页抓取 → 字段提取 → 关键词过滤 → JSON 输出
"""

import os
import json
import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from .config import (
    LIST_URL,
    SEARCH_API_URL,
    SEARCH_KEYWORDS,
    MAX_PAGES,
    OUTPUT_DIR,
    OUTPUT_FILENAME,
    AI_CRAWLER_ENABLED,
    AI_CRAWLER_TIMEOUT,
    AI_CRAWLER_MAX_CONCURRENT,
)
from .fetcher import BiddingFetcher, RateLimiter
from .parser import parse_list_page, parse_detail_page
from .ai_fetcher import AIBiddingFetcher, AICrawlResult, is_ai_crawler_available

# 导入关键词过滤器（相对于 app/services）
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from keyword_filter import filter_advertisement_projects, batch_filter
except ImportError:
    # Docker 容器内路径
    from app.services.keyword_filter import (
        filter_advertisement_projects,
        batch_filter,
    )

logger = logging.getLogger(__name__)


# ============================================================
# 爬虫管道
# ============================================================

class BiddingCrawlerPipeline:
    """
    招标公告爬虫管道。

    Usage:
        pipeline = BiddingCrawlerPipeline()
        results = await pipeline.run(max_pages=3)
        # results 只包含广告类项目
    """

    def __init__(self):
        self.fetcher: Optional[BiddingFetcher] = None
        self.ai_fetcher: Optional[AIBiddingFetcher] = None
        self.results: List[Dict] = []
        self.stats = {
            "total_list_items": 0,
            "detail_fetched": 0,
            "detail_failed": 0,
            "ai_detail_fetched": 0,
            "ai_detail_failed": 0,
            "ad_filtered": 0,
            "non_ad_filtered": 0,
            "pages_crawled": 0,
        }

    async def run(
        self,
        max_pages: int = MAX_PAGES,
        use_search: bool = False,
        use_ai: bool = False,
        ai_detail_urls: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        执行完整采集流程。

        Args:
            max_pages: 最大翻页数
            use_search: 是否使用搜索模式（搜索"广东移动"+"广告"）
            use_ai: 是否使用 AI 增强模式抓取详情页
            ai_detail_urls: AI 模式下的目标详情 URL 列表（跳过列表页）

        Returns:
            广告类招标项目列表
        """
        logger.info("=" * 50)
        logger.info(f"🚀 标中宝爬虫管道启动 (AI模式: {'ON' if use_ai else 'OFF'})")
        logger.info("=" * 50)

        self.fetcher = BiddingFetcher()

        # ── AI 直采模式：跳过列表页，直接 AI 抓取详情 ──
        if use_ai and ai_detail_urls:
            return await self._run_ai_direct_mode(ai_detail_urls)

        try:
            if use_search:
                list_items = await self._search_mode()
            else:
                list_items = await self._list_mode(max_pages)

            self.stats["total_list_items"] = len(list_items)
            logger.info(f"列表页共获取 {len(list_items)} 条公告")

            # ── 第 2 步：抓取详情页 ──
            if use_ai and AI_CRAWLER_ENABLED and is_ai_crawler_available():
                details = await self._fetch_details_ai(list_items)
            else:
                if use_ai and not is_ai_crawler_available():
                    logger.warning("AI 爬虫不可用（crawl4ai 未安装或浏览器未就绪），回退到传统 HTTP 模式")
                details = await self._fetch_details(list_items)

            self.stats["detail_fetched"] = (
                self.stats.get("detail_fetched", 0)
                + self.stats.get("ai_detail_fetched", 0)
            )
            self.stats["detail_failed"] = (
                self.stats.get("detail_failed", 0)
                + self.stats.get("ai_detail_failed", 0)
            )
            logger.info(
                f"详情页抓取完成: 成功 {self.stats['detail_fetched']}, "
                f"失败 {self.stats['detail_failed']}"
            )

            # ── 第 3 步：关键词过滤 ──
            self.results = self._apply_keyword_filter(details)
            self.stats["ad_filtered"] = len(self.results)
            self.stats["non_ad_filtered"] = len(details) - len(self.results)

            logger.info(
                f"关键词过滤: 广告类 {len(self.results)} 条, "
                f"非广告类 {self.stats['non_ad_filtered']} 条"
            )

            # ── 第 4 步：输出 JSON ──
            self._save_results()

        finally:
            await self.fetcher.close()

        self._print_stats()
        return self.results

    # ── 列表页模式 ──

    async def _list_mode(self, max_pages: int) -> List[Dict]:
        """标准列表页翻页模式。"""
        all_items = []

        for page in range(1, max_pages + 1):
            logger.info(f"📄 抓取列表页 第 {page} 页...")

            params = {}
            if page > 1:
                params["page"] = page

            try:
                status, html = await self.fetcher.fetch(LIST_URL, params=params)
                if status != 200:
                    logger.warning(f"列表页第 {page} 页返回 {status}，停止翻页")
                    break

                items = parse_list_page(html)

                if not items:
                    logger.info(f"第 {page} 页无数据，翻页结束")
                    break

                all_items.extend(items)
                self.stats["pages_crawled"] = page
                logger.info(f"第 {page} 页提取 {len(items)} 条公告")

            except Exception as e:
                logger.error(f"列表页第 {page} 页抓取失败: {e}")
                break

        return all_items

    # ── 搜索模式 ──

    async def _search_mode(self) -> List[Dict]:
        """搜索模式：按关键词组合搜索。"""
        all_items = []
        seen_titles = set()

        for keyword_combo in [
            "广东移动 广告",
            "广东移动 品牌",
            "广东移动 宣传",
            "广东移动 营销",
            "广东移动 活动",
        ]:
            logger.info(f"🔍 搜索关键词: {keyword_combo}")

            try:
                status, html = await self.fetcher.fetch(
                    SEARCH_API_URL,
                    params={"keyword": keyword_combo, "noticeType": "2"},
                )

                if status != 200:
                    continue

                items = parse_list_page(html)

                # 去重
                new_items = []
                for item in items:
                    if item["title"] not in seen_titles:
                        seen_titles.add(item["title"])
                        new_items.append(item)

                all_items.extend(new_items)
                logger.info(f"搜索 '{keyword_combo}' 获取 {len(new_items)} 条去重新公告")

            except Exception as e:
                logger.error(f"搜索 '{keyword_combo}' 失败: {e}")
                continue

        return all_items

    # ── 详情页抓取 ──

    async def _fetch_details(self, list_items: List[Dict]) -> List[Dict]:
        """逐一抓取详情页。"""
        details = []

        for i, item in enumerate(list_items):
            detail_url = item.get("detail_url", "")
            if not detail_url:
                # 无详情链接，用列表页已有字段生成条目
                entry = {
                    "title": item.get("title", ""),
                    "purchaser": "",
                    "purchaser_level": "",
                    "procurement_method": item.get("procurement_method", ""),
                    "budget": None,
                    "project_category": "",
                    "announce_date": item.get("publish_date", ""),
                    "deadline": "",
                    "qualification_requirements": "",
                    "score_weight": None,
                    "source_url": "",
                }
                details.append(entry)
                continue

            logger.debug(f"抓取详情页 [{i + 1}/{len(list_items)}]: {detail_url[:100]}")

            try:
                status, html = await self.fetcher.fetch(detail_url)
                if status == 200:
                    parsed = parse_detail_page(html, url=detail_url)
                    # 合并列表页已有字段（列表页的日期可能更准）
                    if not parsed.get("announce_date"):
                        parsed["announce_date"] = item.get("publish_date", "")
                    if not parsed.get("procurement_method"):
                        parsed["procurement_method"] = item.get("procurement_method", "")
                    details.append(parsed)
                else:
                    self.stats["detail_failed"] += 1
                    logger.warning(f"详情页 {detail_url} 返回 {status}")
            except Exception as e:
                self.stats["detail_failed"] += 1
                logger.error(f"详情页抓取异常: {detail_url} - {e}")

        return details

    # ── 关键词过滤 ──

    def _apply_keyword_filter(self, details: List[Dict]) -> List[Dict]:
        """使用关键词过滤脚本筛选广告类项目。"""
        ad_projects = []

        for item in details:
            title = item.get("title", "")
            content = item.get("qualification_requirements", "")

            result = filter_advertisement_projects(title, content)

            if result["is_ad"]:
                # 将过滤结果合并到项目中
                item["matched_keywords"] = result["matched_keywords"]
                item["project_category"] = (
                    result["category"] or item.get("project_category", "")
                )
                ad_projects.append(item)
            else:
                logger.debug(f"过滤非广告项目: {title[:60]} → {result.get('reason', '')}")

        return ad_projects

    # ── AI 增强详情页抓取 ──

    async def _fetch_details_ai(self, list_items: List[Dict]) -> List[Dict]:
        """
        使用 AI 爬虫 (Crawl4AI) 抓取详情页。

        与传统 HTTP 模式并行使用：先 AI 抓取，失败的 fallback 到传统模式。
        """
        if self.ai_fetcher is None:
            self.ai_fetcher = AIBiddingFetcher(
                timeout=AI_CRAWLER_TIMEOUT,
                max_concurrent=AI_CRAWLER_MAX_CONCURRENT,
            )

        details = []
        detail_urls = [item.get("detail_url", "") for item in list_items if item.get("detail_url")]
        failed_urls = []

        if detail_urls:
            logger.info(f"🤖 AI 模式抓取 {len(detail_urls)} 个详情页...")
            batch_result = await self.ai_fetcher.crawl_urls(detail_urls)

            self.stats["ai_detail_fetched"] = batch_result.successful_count
            self.stats["ai_detail_failed"] = batch_result.failed_count

            # 处理 AI 成功抓取的结果
            for i, ai_result in enumerate(batch_result.results):
                if ai_result.success:
                    # 从 Markdown 中提取招标字段
                    parsed = self._parse_ai_markdown(
                        ai_result.markdown,
                        url=ai_result.url,
                        ai_result=ai_result,
                    )
                    # 合并列表页字段
                    list_item = list_items[i] if i < len(list_items) else {}
                    if not parsed.get("announce_date"):
                        parsed["announce_date"] = list_item.get("publish_date", "")
                    if not parsed.get("procurement_method"):
                        parsed["procurement_method"] = list_item.get(
                            "procurement_method", ""
                        )
                    parsed["_ai_crawled"] = True
                    details.append(parsed)
                else:
                    failed_urls.append(ai_result.url)
                    # 无详情链接的条目直接使用列表页数据
                    list_item = list_items[i] if i < len(list_items) else {}
                    entry = self._make_fallback_entry(list_item, ai_result.url)
                    details.append(entry)

        # 处理无详情链接的条目
        for item in list_items:
            if not item.get("detail_url"):
                entry = self._make_fallback_entry(item, "")
                details.append(entry)

        # Fallback: AI 失败的 URL 用传统模式重试
        if failed_urls:
            logger.info(
                f"🔄 AI 失败 {len(failed_urls)} 条，使用传统 HTTP 模式重试..."
            )
            for url in failed_urls:
                try:
                    status, html = await self.fetcher.fetch(url)
                    if status == 200:
                        parsed = parse_detail_page(html, url=url)
                        parsed["_ai_fallback"] = True
                        # 更新已有条目
                        for d in details:
                            if d.get("source_url") == url:
                                d.update(parsed)
                                break
                        else:
                            details.append(parsed)
                        self.stats["detail_fetched"] += 1
                        self.stats["ai_detail_failed"] -= 1
                    else:
                        logger.warning(f"Fallback 也失败: {url} HTTP {status}")
                except Exception as e:
                    logger.error(f"Fallback 异常: {url} - {e}")

        return details

    def _parse_ai_markdown(
        self,
        markdown: str,
        url: str = "",
        ai_result: AICrawlResult = None,
    ) -> Dict:
        """
        从 AI 提取的 Markdown 中解析招标公告字段。

        利用 Markdown 的结构化特性（标题、列表、表格）提取关键信息。
        """
        import re

        result = {
            "title": ai_result.title if ai_result else "",
            "purchaser": "",
            "purchaser_level": "",
            "procurement_method": "",
            "budget": None,
            "project_category": "",
            "announce_date": "",
            "deadline": "",
            "qualification_requirements": "",
            "score_weight": None,
            "source_url": url,
            "_ai_extracted": True,
        }

        if not markdown:
            return result

        # 从 Markdown 标题提取
        title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        if title_match and not result["title"]:
            result["title"] = title_match.group(1).strip()

        # 提取采购方式
        method_patterns = [
            (r"采购方式[：:]\s*(.+?)(?:\n|$)", 1),
            (r"(公开招标|公开比选|公开询比|竞争性谈判|单一来源|询价|比选)", 0),
        ]
        for pattern, group in method_patterns:
            match = re.search(pattern, markdown)
            if match:
                method = match.group(group) if group else match.group(1)
                from .parser import _normalize_procurement_method
                result["procurement_method"] = _normalize_procurement_method(method)
                break

        # 提取预算金额
        budget_match = re.search(
            r"(?:预算|采购预算|项目预算|预算金额)[：:]\s*(\d[\d,.]*)\s*万",
            markdown,
        )
        if budget_match:
            try:
                result["budget"] = float(budget_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # 提取截止日期
        date_patterns = [
            r"(?:截止|递交截止|投标截止)[^\d]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
            r"(?:开标时间|报价截止)[^\d]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, markdown)
            if match:
                result["deadline"] = match.group(1)
                break

        # 提取采购人
        purchaser_match = re.search(
            r"(?:采购人|采购单位|招标人|业主)[：:]\s*(.+?)(?:\n|$)",
            markdown,
        )
        if purchaser_match:
            result["purchaser"] = purchaser_match.group(1).strip()

        # 全文作为资质要求（供后续 LLM 进一步提取）
        result["qualification_requirements"] = markdown[:2000]

        return result

    def _make_fallback_entry(self, list_item: Dict, url: str = "") -> Dict:
        """创建 fallback 条目（详情页抓取失败时使用列表页数据）。"""
        return {
            "title": list_item.get("title", ""),
            "purchaser": "",
            "purchaser_level": "",
            "procurement_method": list_item.get("procurement_method", ""),
            "budget": None,
            "project_category": "",
            "announce_date": list_item.get("publish_date", ""),
            "deadline": "",
            "qualification_requirements": "",
            "score_weight": None,
            "source_url": url or list_item.get("detail_url", ""),
        }

    # ── AI 直采模式 ──

    async def _run_ai_direct_mode(self, detail_urls: List[str]) -> List[Dict]:
        """
        AI 直采模式：跳过列表页，直接 AI 抓取指定详情 URL。

        适用于已知目标 URL 的场景（如搜索结果页提取的链接）。
        """
        logger.info(f"🎯 AI 直采模式: {len(detail_urls)} 个目标 URL")

        if self.ai_fetcher is None:
            self.ai_fetcher = AIBiddingFetcher(
                timeout=AI_CRAWLER_TIMEOUT,
                max_concurrent=AI_CRAWLER_MAX_CONCURRENT,
            )

        batch_result = await self.ai_fetcher.crawl_urls(detail_urls)

        self.stats["ai_detail_fetched"] = batch_result.successful_count
        self.stats["ai_detail_failed"] = batch_result.failed_count
        self.stats["total_list_items"] = len(detail_urls)

        details = []
        for ai_result in batch_result.results:
            if ai_result.success:
                parsed = self._parse_ai_markdown(
                    ai_result.markdown,
                    url=ai_result.url,
                    ai_result=ai_result,
                )
                details.append(parsed)
            else:
                logger.warning(f"AI 直采失败: {ai_result.url}")

        self.stats["detail_fetched"] = len(details)
        self.stats["detail_failed"] = batch_result.failed_count

        # 关键词过滤
        self.results = self._apply_keyword_filter(details)
        self.stats["ad_filtered"] = len(self.results)
        self.stats["non_ad_filtered"] = len(details) - len(self.results)

        self._save_results()
        self._print_stats()
        return self.results

    # ── 结果输出 ──

    def _save_results(self):
        """将采集结果保存为 JSON 文件。"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

        output_data = {
            "crawl_time": datetime.now().isoformat(),
            "stats": self.stats,
            "total": len(self.results),
            "results": self.results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 结果已保存: {output_path} ({len(self.results)} 条)")

    def _print_stats(self):
        """打印采集统计信息。"""
        logger.info("=" * 50)
        logger.info("📊 采集统计")
        logger.info(f"  翻页数:         {self.stats['pages_crawled']}")
        logger.info(f"  列表项总数:     {self.stats['total_list_items']}")
        logger.info(f"  详情抓取成功:   {self.stats['detail_fetched']}")
        logger.info(f"    └─ AI 模式:   {self.stats.get('ai_detail_fetched', 0)}")
        logger.info(f"  详情抓取失败:   {self.stats['detail_failed']}")
        logger.info(f"    └─ AI 失败:   {self.stats.get('ai_detail_failed', 0)}")
        logger.info(f"  广告类项目:     {self.stats['ad_filtered']}")
        logger.info(f"  非广告类:       {self.stats['non_ad_filtered']}")
        logger.info("=" * 50)
