"""
基础爬虫适配器抽象类

所有数据源适配器必须继承此类并实现抽象方法。
提供统一的抓取→解析→过滤→入库流程。
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


class BaseAdapter(ABC):
    """
    招标数据源适配器基类。

    子类需实现四个核心方法：
      fetch_list / parse_list / fetch_detail / parse_detail

    内置功能：
      - User-Agent 轮换
      - 随机请求延迟（3-6秒）
      - 指数退避重试（最多3次）
      - 结构化日志
      - 广告类关键词过滤集成
    """

    # User-Agent 池
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) "
        "Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ]

    def __init__(self, config: dict):
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.base_url = config.get("base_url", "")
        self.min_delay = config.get("min_delay", 3.0)
        self.max_delay = config.get("max_delay", 6.0)
        self.max_retries = config.get("max_retries", 3)
        self.timeout = config.get("timeout", 30)
        self.max_pages = config.get("max_pages", 5)

        self.logger = logging.getLogger(f"adapter.{self.name}")
        self._ua_index = 0
        self._client: Optional[httpx.Client] = None

    # ── HTTP 客户端 ──

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                headers={"User-Agent": self._next_ua()},
            )
        return self._client

    def _next_ua(self) -> str:
        ua = self.USER_AGENTS[self._ua_index % len(self.USER_AGENTS)]
        self._ua_index += 1
        return ua

    def _random_delay(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        self.logger.debug(f"等待 {delay:.1f}s...")
        time.sleep(delay)

    def _request(self, url: str, params: dict = None) -> Tuple[int, str]:
        """带重试的 HTTP GET 请求。"""
        client = self._get_client()
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                self._random_delay()
                self.logger.info(f"[{attempt+1}/{self.max_retries+1}] GET {url[:100]}")
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    return 200, resp.text
                if resp.status_code == 429:
                    wait = 30 * (2 ** attempt)
                    self.logger.warning(f"429 限流，等待 {wait}s")
                    time.sleep(wait)
                    continue
                self.logger.warning(f"HTTP {resp.status_code}: {url[:100]}")
                if attempt < self.max_retries:
                    time.sleep(10 * (2 ** attempt))
            except Exception as e:
                last_error = e
                self.logger.warning(f"请求失败 [{attempt+1}]: {e}")
                if attempt < self.max_retries:
                    time.sleep(10 * (2 ** attempt))

        raise last_error or RuntimeError(f"请求失败: {url}")

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    # ── 抽象方法 ──

    @abstractmethod
    def get_source_name(self) -> str:
        """返回数据源名称，用于日志和标识。"""
        ...

    @abstractmethod
    def fetch_list(self, page: int = 1) -> str:
        """抓取列表页，返回 HTML 文本。"""
        ...

    @abstractmethod
    def parse_list(self, html: str) -> List[Dict]:
        """
        解析列表页 HTML，返回公告摘要列表。

        Returns:
            [{"title": "", "publish_date": "", "detail_url": "", "notice_type": ""}, ...]
        """
        ...

    @abstractmethod
    def fetch_detail(self, url: str) -> Tuple[str, Optional[bytes]]:
        """
        抓取详情页。

        Returns:
            (html_text, pdf_bytes_or_None)
        """
        ...

    @abstractmethod
    def parse_detail(self, html: str, pdf_bytes: Optional[bytes] = None) -> Dict:
        """
        解析详情页/PDF，返回标准化字段字典。

        Returns:
            {
                "title": str, "purchaser": str, "purchaser_level": str,
                "bid_number": str, "notice_type": str,
                "publish_date": str, "deadline": str,
                "budget": float|None, "content_text": str,
                "source_url": str, "attachments": list
            }
        """
        ...

    # ── 标准化映射 ──

    def _normalize_record(self, raw: Dict) -> Dict:
        """将适配器原始字段映射为系统标准 announcements 表结构。"""
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            from app.services.keyword_filter import filter_with_llm_fallback
        except ImportError:
            from services.keyword_filter import filter_with_llm_fallback

        title = raw.get("title", "")
        content = raw.get("content_text", "")

        # 混合分类：关键词优先 + LLM 兜底
        filter_result = filter_with_llm_fallback(title, content)

        # 中标公示强制标记为非广告（应入 awards 表）
        if filter_result["is_ad"]:
            winning_keywords = ["中选候选人", "中选结果", "中选人", "中标候选人", "中标结果", "中标人", "成交候选人", "成交结果"]
            if any(kw in title for kw in winning_keywords):
                filter_result["is_ad"] = False
                filter_result["category"] = "中标公示"
                self.logger.info(f"  ⏭️ 中标公示跳过: {title[:60]}")

        # 预算提取：正则优先 → LLM 兜底
        budget = raw.get("budget")
        registration_fee = raw.get("registration_fee")
        deposit = raw.get("deposit")

        if not budget or budget == 0:
            try:
                from app.services.budget_extractor import extract_budget_hybrid
                budget_result = extract_budget_hybrid(title, content, existing_budget=budget)
                budget = budget_result.get("budget") or budget
                registration_fee = budget_result.get("registration_fee") or registration_fee
                deposit = budget_result.get("deposit") or deposit
                if budget_result.get("extractor") == "llm" and budget:
                    self.logger.info(f"  💰 LLM提取预算: {budget}万元 ({title[:40]})")
            except Exception as e:
                self.logger.debug(f"预算提取跳过: {e}")

        return {
            "title": title,
            "purchaser": raw.get("purchaser", ""),
            "purchaser_level": raw.get("purchaser_level", ""),
            "procurement_method": raw.get("procurement_method", "公开招标"),
            "budget": budget,
            "registration_fee": registration_fee,
            "deposit": deposit,
            "project_category": filter_result.get("category", ""),
            "announce_date": raw.get("publish_date", ""),
            "deadline": raw.get("deadline", ""),
            "qualification_requirements": content[:2000],
            "original_content": content,
            "score_weight": raw.get("score_weight"),
            "source_url": raw.get("source_url", ""),
            "notice_type": raw.get("notice_type", "招标公告"),
            "bid_number": raw.get("bid_number", ""),
            "is_ad": filter_result["is_ad"],
            "matched_keywords": filter_result["matched_keywords"],
            "province": raw.get("province", ""),
            "city": raw.get("city", ""),
            "industry": raw.get("purchaser", ""),
        }

    # ── 主流程 ──

    def run(self, save_to_db: bool = True) -> List[Dict]:
        """
        执行完整采集流程：列表翻页 → 详情抓取 → 解析 → 过滤 → 入库。

        Args:
            save_to_db: 是否自动入库（通过 announcements 表）

        Returns:
            采集到的广告类项目列表
        """
        all_results = []
        seen_urls = set()

        self.logger.info(f"===== {self.name} 开始采集 =====")

        for page in range(1, self.max_pages + 1):
            self.logger.info(f"--- 列表页 第 {page} 页 ---")
            try:
                html = self.fetch_list(page=page)
                items = self.parse_list(html)

                if not items:
                    self.logger.info("无更多公告，翻页结束")
                    break

                for i, item in enumerate(items):
                    detail_url = item.get("detail_url", "")
                    if not detail_url or detail_url in seen_urls:
                        continue
                    seen_urls.add(detail_url)

                    try:
                        html_detail, pdf_bytes = self.fetch_detail(detail_url)
                        parsed = self.parse_detail(html_detail, pdf_bytes)
                        parsed["source_url"] = detail_url
                        parsed["notice_type"] = item.get("notice_type", parsed.get("notice_type", ""))

                        # 标准化 + 关键词过滤
                        record = self._normalize_record(parsed)

                        if record["is_ad"]:
                            all_results.append(record)
                            self.logger.info(
                                f"  ✅ [{i+1}/{len(items)}] {record['title'][:60]} "
                                f"| {record['project_category']}"
                            )
                        else:
                            self.logger.debug(
                                f"  ⏭️ 非广告: {record['title'][:60]}"
                            )

                        # 入库
                        if save_to_db and record["is_ad"]:
                            self._save_to_db(record)

                    except Exception as e:
                        self.logger.error(f"详情页失败: {detail_url[:80]} - {e}")

            except Exception as e:
                self.logger.error(f"列表页第 {page} 页失败: {e}")
                break

        self.logger.info(f"===== {self.name} 采集完成: {len(all_results)} 条广告类 =====")
        self.close()
        return all_results

    def _save_to_db(self, record: Dict):
        """将记录保存到数据库（异步包装）。"""
        try:
            import asyncio
            from app.db.session import AsyncSessionLocal
            from app.models.announcement import Announcement
            from datetime import date, datetime

            async def _save():
                async with AsyncSessionLocal() as db:
                    ann = Announcement(
                        title=record["title"],
                        purchaser_id=1,
                        purchaser_level=record.get("purchaser_level", ""),
                        procurement_method=record.get("procurement_method", "公开招标"),
                        budget=record.get("budget"),
                        registration_fee=record.get("registration_fee"),
                        deposit=record.get("deposit"),
                        project_category=record.get("project_category", ""),
                        announce_date=_parse_date(record.get("announce_date", "")),
                        deadline=_parse_datetime(record.get("deadline", "")),
                        qualification_requirements=record.get("qualification_requirements", ""),
                        original_content=record.get("original_content", ""),
                        source_url=record.get("source_url", ""),
                        province=record.get("province", ""),
                        city=record.get("city", ""),
                        industry=record.get("industry", ""),
                    )
                    db.add(ann)
                    await db.commit()
                    self.logger.info(f"  💾 入库: {record['title'][:50]}")

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio
                    nest_asyncio.apply()
                asyncio.run(_save())
            except RuntimeError:
                asyncio.run(_save())
        except ImportError as e:
            self.logger.warning(f"数据库模块不可用，跳过入库: {e}")
        except Exception as e:
            self.logger.error(f"入库失败: {e}")


def _parse_date(s: str):
    from datetime import date
    import re
    if not s:
        return date.today()
    m = re.match(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return date.today()


def _parse_datetime(s: str):
    from datetime import datetime
    import re
    if not s:
        return datetime(1900, 1, 1)
    m = re.match(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[T\s]?(\d{1,2}):(\d{2})", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                        int(m.group(4)), int(m.group(5)))
    return datetime(1900, 1, 1)
    m = re.match(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 17, 0)
    return None
