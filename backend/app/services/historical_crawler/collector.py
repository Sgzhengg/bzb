"""
历史中标公告 — 断点续传采集器

特性：
- 多关键词组合搜索翻页
- 断点续传（基于 URL 去重）
- 随机延迟 3-5 秒
- 详情页解析 + 数据清洗管道
- 分批保存，最终合并 JSON
"""

import os
import sys
import json
import time
import random
import hashlib
import logging
import asyncio
from typing import List, Dict, Set, Optional
from datetime import datetime

# 确保路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.historical_crawler.config import (
    AWARD_LIST_URL,
    AWARD_SEARCH_URL,
    SEARCH_KEYWORD_COMBOS,
    MAX_PAGES_PER_SEARCH,
    MIN_DELAY,
    MAX_DELAY,
    USER_AGENTS,
    BASE_HEADERS,
    CHECKPOINT_DIR,
    CHECKPOINT_FILE,
    PARTIAL_DIR,
    OUTPUT_DIR,
    OUTPUT_FILENAME,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    REQUEST_TIMEOUT,
)
from app.services.historical_crawler.cleaner import clean_award_record, batch_clean
from app.services.crawler.fetcher import BiddingFetcher, RateLimiter
from app.services.crawler.parser import (
    parse_list_page,
    parse_detail_page,
    _resolve_url,
    _normalize_date,
)
from app.services.keyword_filter import filter_advertisement_projects

logger = logging.getLogger(__name__)


# ============================================================
# 断点管理器
# ============================================================

class CheckpointManager:
    """
    断点续传管理器。

    以 detail_url 的 MD5 哈希为唯一标识，
    记录已采集的公告 URL，支持中断后跳过已采集项。
    """

    def __init__(self, checkpoint_path: str):
        self.checkpoint_path = checkpoint_path
        self.processed_urls: Set[str] = set()
        self._load()

    def _load(self):
        """从磁盘加载断点。"""
        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        if os.path.exists(self.checkpoint_path):
            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.processed_urls = set(data.get("processed_urls", []))
                logger.info(f"📂 加载断点: {len(self.processed_urls)} 条已采集")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"断点文件损坏，重新开始: {e}")
                self.processed_urls = set()
        else:
            logger.info("📂 未发现断点文件，从头开始采集")

    def is_processed(self, url: str) -> bool:
        """检查 URL 是否已采集。"""
        return self._hash_url(url) in self.processed_urls

    def mark_processed(self, url: str):
        """标记 URL 为已采集并立即保存。"""
        self.processed_urls.add(self._hash_url(url))
        self._save()

    def _save(self):
        """保存断点到磁盘。"""
        data = {
            "updated_at": datetime.now().isoformat(),
            "total_processed": len(self.processed_urls),
            "processed_urls": list(self.processed_urls),
        }
        with open(self.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _hash_url(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    @property
    def count(self) -> int:
        return len(self.processed_urls)


# ============================================================
# 分批保存器
# ============================================================

class BatchSaver:
    """
    分批保存采集结果。
    每采集完一个关键词组合，将结果保存为独立的 JSON 文件，
    最终合并为一个总文件。
    """

    def __init__(self, partial_dir: str, output_path: str):
        self.partial_dir = partial_dir
        self.output_path = output_path
        os.makedirs(partial_dir, exist_ok=True)
        self.batch_index = 0

    def save_batch(self, records: List[Dict], label: str = ""):
        """保存一批记录。"""
        if not records:
            return
        self.batch_index += 1
        filename = f"batch_{self.batch_index:04d}_{label}.json"
        filepath = os.path.join(self.partial_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 分批保存: {filename} ({len(records)} 条)")

    def merge_all(self) -> int:
        """合并所有分批文件为最终输出。"""
        all_records = []
        if not os.path.exists(self.partial_dir):
            return 0

        for filename in sorted(os.listdir(self.partial_dir)):
            if filename.endswith(".json"):
                filepath = os.path.join(self.partial_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        records = json.load(f)
                    all_records.extend(records)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"分批文件损坏: {filename} - {e}")

        # 去重（按 source_url）
        seen = set()
        unique = []
        for r in all_records:
            url = r.get("source_url", "")
            if url and url in seen:
                continue
            seen.add(url)
            unique.append(r)

        output_data = {
            "crawl_time": datetime.now().isoformat(),
            "total": len(unique),
            "results": unique,
        }

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 合并完成: {self.output_path} ({len(unique)} 条)")
        return len(unique)


# ============================================================
# 中标详情页解析器
# ============================================================

def parse_award_detail(html: str, url: str = "") -> Dict:
    """
    解析中标公告详情页，提取中标特有字段。

    在通用详情页解析基础上，额外提取：
    - 中标方名称
    - 中标金额
    - 预算金额
    """
    # 先用通用解析器获取基础字段
    base = parse_detail_page(html, url=url)

    # 从页面文本中补充提取
    import re
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    page_text = soup.get_text(separator="\n", strip=True)[:10000]

    # ── 中标方 ──
    winner_patterns = [
        r"(?:中标|中选|成交)(?:人|方|单位|供应商)[：:]\s*(.+?)(?:\n|$)",
        r"(?:中标|中选|成交)(?:人|方|单位|供应商)\s*[：:]\s*(.+?)(?:。|\n)",
        r"第\s*一\s*(?:中标|中选|成交)(?:候选)?(?:人|方)[：:]\s*(.+?)(?:\n|$)",
        r"拟?(?:中标|中选|成交)(?:人|方|单位)[：:]\s*(.+?)(?:\n|$)",
    ]
    winner_name = ""
    for pat in winner_patterns:
        match = re.search(pat, page_text)
        if match:
            winner_name = match.group(1).strip()
            # 截断到下一个常见分隔符
            winner_name = winner_name.split("；")[0].split("。")[0][:200]
            break

    # ── 金额 ──
    bid_amount = None
    budget_amount = None

    bid_pats = [
        r"中标(?:金额|价)[：:]\s*(.+?)(?:\n|；|。|$)",
        r"成交(?:金额|价)[：:]\s*(.+?)(?:\n|；|。|$)",
        r"中选(?:金额|价)[：:]\s*(.+?)(?:\n|；|。|$)",
    ]
    budget_pats = [
        r"(?:项目)?预算(?:金额)?[：:]\s*(.+?)(?:\n|；|。|$)",
    ]

    from app.services.historical_crawler.cleaner import normalize_amount
    for pat in bid_pats:
        m = re.search(pat, page_text)
        if m:
            bid_amount = normalize_amount(m.group(1))
            break
    for pat in budget_pats:
        m = re.search(pat, page_text)
        if m:
            budget_amount = normalize_amount(m.group(1))
            break

    # 如果没有明确的"中标金额"，尝试从页面提取最大金额
    if bid_amount is None:
        amounts = []
        for m in re.finditer(r"(\d+\.?\d*)\s*万", page_text):
            amounts.append(float(m.group(1)))
        if amounts:
            bid_amount = max(amounts)

    return {
        **base,
        "winner_name": winner_name,
        "bid_amount": bid_amount,
        "budget_amount": budget_amount,
        "bid_amount_raw": "",
        "budget_amount_raw": "",
        "content": page_text,  # 完整页面文本，供清洗器提取合同期限等
    }


# ============================================================
# 历史中标采集器
# ============================================================

class HistoricalAwardCollector:
    """
    历史中标公告采集器。

    Usage:
        collector = HistoricalAwardCollector()
        results = await collector.run()
    """

    def __init__(self):
        self.fetcher: Optional[BiddingFetcher] = None
        self.checkpoint = CheckpointManager(
            os.path.join(CHECKPOINT_DIR, CHECKPOINT_FILE)
        )
        self.saver = BatchSaver(
            os.path.join(CHECKPOINT_DIR, "partial"),
            os.path.join(OUTPUT_DIR, OUTPUT_FILENAME),
        )
        self.stats = {
            "list_items_found": 0,
            "detail_fetched": 0,
            "detail_failed": 0,
            "detail_skipped": 0,
            "ad_passed": 0,
            "ad_filtered_out": 0,
            "cleaned_saved": 0,
        }

    async def run(self) -> List[Dict]:
        """执行完整的历史中标采集。"""
        logger.info("=" * 60)
        logger.info("📊 标中宝 — 历史中标公告批量采集")
        logger.info(f"   采集范围: 2023-01-01 至今（广东移动广告类）")
        logger.info(f"   断点状态: 已采集 {self.checkpoint.count} 条")
        logger.info("=" * 60)

        self.fetcher = BiddingFetcher(
            rate_limiter=RateLimiter(min_interval=MIN_DELAY),
            timeout=REQUEST_TIMEOUT,
        )

        try:
            all_awards = []

            for combo_idx, keyword_combo in enumerate(SEARCH_KEYWORD_COMBOS):
                keyword_str = " ".join(keyword_combo)
                logger.info(f"\n🔍 [{combo_idx + 1}/{len(SEARCH_KEYWORD_COMBOS)}] "
                            f"搜索: {keyword_str}")

                items = await self._search_and_fetch(keyword_combo)

                if not items:
                    logger.info(f"  无新公告")
                    continue

                # 抓取详情
                details = await self._fetch_award_details(items, keyword_str)
                self.stats["detail_fetched"] += len(details)

                if not details:
                    continue

                # 广告类关键词过滤
                ad_awards = self._filter_ad_only(details)

                # 数据清洗
                cleaned = batch_clean(ad_awards)
                self.stats["cleaned_saved"] += len(cleaned)

                # 分批保存
                label = keyword_str.replace(" ", "_")[:50]
                self.saver.save_batch(cleaned, label=label)
                all_awards.extend(cleaned)

                logger.info(f"  ✅ 本组: 列表{len(items)} → "
                            f"详情{len(details)} → 广告{len(ad_awards)} → 清洗{len(cleaned)}")

            # 最终合并
            total = self.saver.merge_all()
            self._print_stats()

            return all_awards

        finally:
            await self.fetcher.close()

    async def _search_and_fetch(self, keywords: tuple) -> List[Dict]:
        """按关键词组合搜索并翻页，返回去重后的列表项。"""
        all_items = []
        keyword_str = "+".join(keywords)

        for page in range(1, MAX_PAGES_PER_SEARCH + 1):
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            await asyncio.sleep(delay)

            params = {
                "keyword": keyword_str,
                "noticeType": "2",  # 结果公告
                "page": page,
            }

            try:
                status, html = await self.fetcher.fetch(AWARD_SEARCH_URL, params=params)
                if status != 200:
                    logger.warning(f"  搜索 '{keyword_str}' 第{page}页 返回 {status}")
                    break

                items = parse_list_page(html)
                if not items:
                    break

                # 去重
                new_items = []
                for item in items:
                    url = item.get("detail_url", "")
                    if url and self.checkpoint.is_processed(url):
                        self.stats["detail_skipped"] += 1
                        continue
                    new_items.append(item)

                all_items.extend(new_items)
                self.stats["list_items_found"] += len(new_items)
                logger.debug(f"  第{page}页: {len(new_items)} 条新公告 "
                             f"(跳过 {len(items) - len(new_items)} 条已采集)")

            except Exception as e:
                logger.error(f"  搜索 '{keyword_str}' 第{page}页 失败: {e}")
                break

        return all_items

    async def _fetch_award_details(
        self, items: List[Dict], label: str
    ) -> List[Dict]:
        """逐条抓取详情页。"""
        details = []

        for i, item in enumerate(items):
            url = item.get("detail_url", "")
            if not url:
                continue

            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            await asyncio.sleep(delay)

            try:
                status, html = await self.fetcher.fetch(url)
                if status == 200:
                    parsed = parse_award_detail(html, url=url)
                    if not parsed.get("announce_date"):
                        parsed["announce_date"] = item.get("publish_date", "")
                    details.append(parsed)
                    self.checkpoint.mark_processed(url)
                else:
                    self.stats["detail_failed"] += 1
            except Exception as e:
                self.stats["detail_failed"] += 1
                logger.error(f"详情页失败 [{i+1}/{len(items)}]: {url[:100]} - {e}")

            if (i + 1) % 10 == 0:
                logger.info(f"  进度 [{i+1}/{len(items)}] {label}")

        return details

    def _filter_ad_only(self, details: List[Dict]) -> List[Dict]:
        """使用关键词过滤器筛选广告类项目。"""
        ad_awards = []
        for item in details:
            title = item.get("title", "")
            content = item.get("qualification_requirements", "")
            result = filter_advertisement_projects(title, content)
            if result["is_ad"]:
                item["matched_keywords"] = result["matched_keywords"]
                item["project_category"] = result.get("category", "")
                ad_awards.append(item)
                self.stats["ad_passed"] += 1
            else:
                self.stats["ad_filtered_out"] += 1
        return ad_awards

    def _print_stats(self):
        """打印统计信息。"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 采集统计")
        logger.info(f"  列表项发现:     {self.stats['list_items_found']}")
        logger.info(f"  跳过(已采集):   {self.stats['detail_skipped']}")
        logger.info(f"  详情抓取成功:   {self.stats['detail_fetched']}")
        logger.info(f"  详情抓取失败:   {self.stats['detail_failed']}")
        logger.info(f"  广告类通过:     {self.stats['ad_passed']}")
        logger.info(f"  非广告类过滤:   {self.stats['ad_filtered_out']}")
        logger.info(f"  清洗后保存:     {self.stats['cleaned_saved']}")
        logger.info("=" * 60)
