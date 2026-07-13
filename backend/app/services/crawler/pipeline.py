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
        search_keywords: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        执行完整采集流程。

        Args:
            max_pages: 最大翻页数
            use_search: 是否使用搜索模式
            use_ai: 是否使用 AI 增强模式抓取详情页
            ai_detail_urls: AI 模式下的目标详情 URL 列表（跳过列表页）
            search_keywords: 自定义搜索关键词列表

        Returns:
            广告类招标项目列表
        """
        logger.info("=" * 50)
        logger.info(f"🚀 标中宝爬虫管道启动 (AI模式: {'ON' if use_ai else 'OFF'})")
        logger.info("=" * 50)

        self.fetcher = BiddingFetcher()

        if use_ai and ai_detail_urls:
            return await self._run_ai_direct_mode(ai_detail_urls)

        try:
            # ── 第 1 步：列表采集（b2b JSON API）──
            list_items = await self._list_mode(max_pages, search_keywords)
            self.stats["total_list_items"] = len(list_items)
            logger.info(f"列表页共获取 {len(list_items)} 条公告")

            # ── 第 2 步：详情页抓取 ──
            details = await self._fetch_details(list_items)
            self.stats["detail_fetched"] = len(details)
            logger.info(f"详情页抓取完成: 成功 {len(details)}")

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

    async def _list_mode(
        self, max_pages: int, search_keywords: Optional[List[str]] = None
    ) -> List[Dict]:
        """列表页采集：通过 b2b.10086.cn JSON API 搜索招标公告。"""
        import ssl, httpx

        if search_keywords is None:
            search_keywords = SEARCH_KEYWORDS

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= 0x4  # SSL_OP_LEGACY_SERVER_CONNECT

        all_items = []
        seen_ids = set()

        async with httpx.AsyncClient(verify=ctx, timeout=30) as client:
            for keyword in search_keywords:
                logger.info(f"🔍 搜索: {keyword}")
                for page in range(1, max_pages + 1):
                    try:
                        resp = await client.post(
                            "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryList",
                            json={
                                "name": keyword,
                                "publishType": "PROCUREMENT",
                                "size": 20, "current": page,
                                "sfactApplColumn5": "PC",
                            },
                            headers={
                                "Content-Type": "application/json",
                                "User-Agent": "Mozilla/5.0",
                            },
                        )
                        if resp.status_code != 200:
                            break
                        data = resp.json()
                        items = data.get("data", {}).get("content", [])
                        if not items:
                            break

                        for item in items:
                            item_id = str(item.get("id", ""))
                            if item_id and item_id not in seen_ids:
                                seen_ids.add(item_id)
                                all_items.append({
                                    "title": item.get("name", ""),
                                    "detail_url": self._build_detail_url(item),
                                    "source": "b2b.10086.cn",
                                    "_b2b_item": item,
                                })
                                logger.debug(f"  → {item.get('name', '')[:60]}")

                        self.stats["pages_crawled"] = page
                    except Exception as e:
                        logger.error(f"  搜索失败 '{keyword}' p{page}: {e}")
                        break

        return all_items

    def _build_detail_url(self, item: dict) -> str:
        """从 b2b API item 构造详情页 URL。"""
        pid = item.get("id", "")
        return f"https://b2b.10086.cn/b2b/main/viewNoticeContent.html?noticeBean.id={pid}"

    # ── 详情页抓取 ──

    async def _fetch_details(self, list_items: List[Dict]) -> List[Dict]:
        """详情页抓取：通过 b2b queryDetail API 获取 PDF 正文并提取字段。"""
        import ssl, httpx, base64

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= 0x4

        details = []
        detail_headers = {
            "Content-Type": "application/json",
            "userloginname": "-1",
            "processinstid": "-1",
            "User-Agent": "Mozilla/5.0",
        }

        async with httpx.AsyncClient(verify=ctx, timeout=30) as client:
            for i, item in enumerate(list_items):
                b2b = item.get("_b2b_item", {})
                pid = str(b2b.get("id", ""))
                puid = b2b.get("uuid", "")
                title = item.get("title", "")

                if not pid:
                    details.append(self._empty_detail(item))
                    continue

                logger.info(f"📄 [{i+1}/{len(list_items)}] {title[:50]}...")

                try:
                    resp = await client.post(
                        "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryDetail",
                        json={
                            "publishId": pid,
                            "publishUuid": puid,
                            "publishType": "PROCUREMENT",
                            "sfactApplColumn5": "PC",
                        },
                        headers=detail_headers,
                    )

                    content_text = ""
                    if resp.status_code == 200:
                        detail = resp.json().get("data", {})
                        b64 = detail.get("noticeContent", "")
                        if b64:
                            try:
                                import fitz
                                pdf_bytes = base64.b64decode(b64)
                                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                                pages = []
                                for pn in range(len(doc)):
                                    t = doc[pn].get_text()
                                    if t.strip():
                                        pages.append(t)
                                doc.close()
                                content_text = "\n".join(pages)
                            except Exception as e:
                                logger.debug(f"  PDF decode failed: {e}")

                    # 提取城市
                    city = self._extract_city(title)

                    # LLM 分类
                    from app.services.keyword_filter import filter_with_llm_fallback
                    classify_result = filter_with_llm_fallback(title, content_text)

                    # LLM 预算提取
                    budget_info = {}
                    if classify_result["is_ad"]:
                        try:
                            from app.services.budget_extractor import extract_budget_hybrid
                            budget_info = extract_budget_hybrid(title, content_text)
                        except Exception:
                            pass

                    entry = {
                        "title": title,
                        "purchaser": "",
                        "purchaser_level": "省公司" if "分公司" not in title else "地市公司",
                        "procurement_method": "公开招标",
                        "budget": budget_info.get("budget"),
                        "registration_fee": budget_info.get("registration_fee"),
                        "deposit": budget_info.get("deposit"),
                        "project_category": classify_result.get("category", ""),
                        "announce_date": b2b.get("publishDate", ""),
                        "deadline": b2b.get("bidEndDate", "") or "",
                        "qualification_requirements": content_text[:2000] if content_text else "",
                        "original_content": content_text[:50000] if content_text else title,
                        "score_weight": None,
                        "source_url": item.get("detail_url", ""),
                        "city": city,
                        "industry": b2b.get("companyName", ""),
                        "province": self._extract_province(title, b2b),
                        "_is_ad": classify_result["is_ad"],
                        "_classifier": classify_result.get("classifier", ""),
                    }
                    details.append(entry)
                    logger.info(f"  ✅ [{classify_result.get('classifier','?')}] "
                                f"{classify_result.get('category','')} | budget={entry['budget']}")

                except Exception as e:
                    logger.error(f"  详情抓取失败: {e}")
                    details.append(self._empty_detail(item))

        return details

    def _empty_detail(self, item: dict) -> dict:
        return {
            "title": item.get("title", ""),
            "purchaser": "", "purchaser_level": "",
            "procurement_method": "", "budget": None,
            "project_category": "", "announce_date": "",
            "deadline": "", "qualification_requirements": "",
            "score_weight": None, "source_url": item.get("detail_url", ""),
            "original_content": "", "city": "", "industry": "",
            "province": "", "_is_ad": False, "_classifier": "",
        }

    def _extract_city(self, title: str) -> str:
        cities = [
            "广州", "深圳", "东莞", "佛山", "珠海", "惠州", "中山",
            "江门", "汕头", "湛江", "茂名", "肇庆", "梅州", "汕尾",
            "河源", "阳江", "清远", "韶关", "潮州", "揭阳", "云浮",
            "南宁", "柳州", "桂林", "玉林", "梧州", "北海", "贵港",
            "钦州", "百色", "河池", "贺州", "来宾", "崇左", "防城港",
            "福州", "厦门", "泉州", "漳州", "龙岩", "三明", "南平", "莆田", "宁德",
            "海口", "三亚", "儋州",
            "杭州", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华", "衢州", "舟山", "台州", "丽水",
            "长沙", "株洲", "湘潭", "衡阳", "邵阳", "岳阳", "常德",
            "张家界", "益阳", "郴州", "永州", "怀化", "娄底",
            "合肥", "芜湖", "蚌埠", "淮南", "马鞍山", "淮北", "铜陵",
            "安庆", "黄山", "滁州", "阜阳", "宿州", "六安", "亳州", "池州", "宣城",
            "济南", "青岛", "淄博", "枣庄", "东营", "烟台", "潍坊",
            "济宁", "泰安", "威海", "日照", "临沂", "德州", "聊城", "滨州", "菏泽",
        ]
        for c in sorted(cities, key=lambda x: -len(x)):
            if c in title:
                return c
        return ""

    def _extract_province(self, title: str, b2b_item: dict) -> str:
        provinces = [
            "广东", "广西", "福建", "海南", "浙江", "湖南", "安徽", "山东",
            "江苏", "四川", "湖北", "河南", "河北", "辽宁", "江西", "陕西",
            "山西", "云南", "贵州", "吉林", "黑龙江", "甘肃", "内蒙古",
            "新疆", "西藏", "青海", "宁夏", "北京", "上海", "天津", "重庆",
        ]
        for p in sorted(provinces, key=lambda x: -len(x)):
            if p in title:
                return p
        region = b2b_item.get("regionName", "") or b2b_item.get("region", "")
        return region

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
