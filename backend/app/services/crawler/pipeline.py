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
)
from .fetcher import BiddingFetcher, RateLimiter
from .parser import parse_list_page, parse_detail_page

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
        self.results: List[Dict] = []
        self.stats = {
            "total_list_items": 0,
            "detail_fetched": 0,
            "detail_failed": 0,
            "ad_filtered": 0,
            "non_ad_filtered": 0,
            "pages_crawled": 0,
        }

    async def run(
        self,
        max_pages: int = MAX_PAGES,
        use_search: bool = False,
    ) -> List[Dict]:
        """
        执行完整采集流程。

        Args:
            max_pages: 最大翻页数
            use_search: 是否使用搜索模式（搜索"广东移动"+"广告"）

        Returns:
            广告类招标项目列表
        """
        logger.info("=" * 50)
        logger.info("🚀 标中宝爬虫管道启动")
        logger.info("=" * 50)

        self.fetcher = BiddingFetcher()

        try:
            if use_search:
                list_items = await self._search_mode()
            else:
                list_items = await self._list_mode(max_pages)

            self.stats["total_list_items"] = len(list_items)
            logger.info(f"列表页共获取 {len(list_items)} 条公告")

            # ── 第 2 步：抓取详情页 ──
            details = await self._fetch_details(list_items)
            self.stats["detail_fetched"] = len(details)
            logger.info(
                f"详情页抓取完成: 成功 {len(details)}, "
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
        logger.info(f"  翻页数:       {self.stats['pages_crawled']}")
        logger.info(f"  列表项总数:   {self.stats['total_list_items']}")
        logger.info(f"  详情抓取成功: {self.stats['detail_fetched']}")
        logger.info(f"  详情抓取失败: {self.stats['detail_failed']}")
        logger.info(f"  广告类项目:   {self.stats['ad_filtered']}")
        logger.info(f"  非广告类:     {self.stats['non_ad_filtered']}")
        logger.info("=" * 50)
