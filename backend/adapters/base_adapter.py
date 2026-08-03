"""
基础爬虫适配器抽象类

所有数据源适配器必须继承此类并实现抽象方法。
提供统一的抓取→解析→过滤→入库流程。
"""

import logging
import random
import time
from datetime import date
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple, Callable
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
        self.source_key = config.get("source_key", "")  # b2b_10086/telecom/unicom/gd_zbtb/gd_ygp

        self.logger = logging.getLogger(f"adapter.{self.name}")
        self._ua_index = 0
        self._client: Optional[httpx.Client] = None
        self._progress_callback: Optional[Callable[[int, str], None]] = None

    def set_progress_callback(self, callback: Callable[[int, str], None]):
        """设置进度回调函数。

        Args:
            callback: 接收 (progress_percent, message) 的回调函数
        """
        self._progress_callback = callback

    def _report_progress(self, progress: int, message: str = ""):
        """报告进度，如果设置了回调函数则调用。

        Args:
            progress: 进度百分比 (0-100)
            message: 进度消息
        """
        if self._progress_callback:
            self._progress_callback(progress, message)

    def _load_existing_titles(self) -> set:
        """从数据库加载已有的公告标题集合，用于跳过已采集的记录。"""
        try:
            import sqlite3
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "biaozhongbao.db")
            if not os.path.exists(db_path):
                return set()
            conn = sqlite3.connect(db_path, timeout=30)
            cur = conn.execute("SELECT title FROM announcements")
            titles = {row[0] for row in cur.fetchall()}
            conn.close()
            self.logger.info(f"📋 数据库中已有 {len(titles)} 条记录，将跳过重复项")
            return titles
        except Exception as e:
            self.logger.warning(f"加载已有标题失败: {e}")
            return set()

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

    # ── 标准化映射（V4: 仅运营商招标，统一分类流程）──

    def _normalize_record(self, raw: Dict) -> Dict:
        """将适配器原始字段映射为系统标准 announcements 表结构。"""
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        title = raw.get("title", "")
        content = raw.get("content_text", "")

        # ── 跳过关键词 ──
        SKIP_KEYWORDS = ["中选候选人", "中选结果", "中选人", "中标候选人", "中标结果", "中标人", "成交候选人", "成交结果"]
        if any(kw in title for kw in SKIP_KEYWORDS):
            return self._make_skip_record(title, content, raw, "中标公示")

        # ── 意见征集/技术规范征求意见类：招标前兆信号 ──
        # 用 LLM 判别正文是否指向真实招标机会：是→保留，否→跳过
        opinion_keywords = [
            "意见征求", "征求意见", "意见征询", "征集意见", "意见征集",
            "征询公告", "技术征询", "技术规范书", "技术评分表", "评审办法",
            "评分细则", "技术标准", "文件意见", "意见的公示", "意见的公告", "意见反馈",
        ]
        if any(kw in title for kw in opinion_keywords):
            keep = True  # LLM 不可用时保守保留
            try:
                from app.services.llm_summarizer import judge_opinion_value
            except ImportError:
                from services.llm_summarizer import judge_opinion_value
            try:
                v = judge_opinion_value(title, content)
                if v is not None:
                    keep = v
            except Exception as e:
                self.logger.warning(f"  意见征集判别异常: {e}")
            if keep:
                self.logger.info(f"  📋 意见征集保留(招标前兆): {title[:50]}")
                # 业务类别走行业分类器（意见征集类本身不是业务类别）
                try:
                    from app.services.industry_classifier import classify_industry_and_category
                    ind_result = classify_industry_and_category(title, content, self.source_key)
                    proj_cat = ind_result.get("project_category", "") or "其他采购"
                except Exception:
                    proj_cat = "其他采购"
                return self._build_final_record(title, content, raw,
                    is_target=True, project_category=proj_cat,
                    industry_type="运营商")
            self.logger.info(f"  ⏭️ 意见征集与招标无关跳过: {title[:50]}")
            return self._make_skip_record(title, content, raw, "意见征求-无关")

        # ── 行业分类器 ──
        try:
            from app.services.industry_classifier import classify_industry_and_category
        except ImportError:
            from services.industry_classifier import classify_industry_and_category

        # ── 关键词预过滤 ──
        try:
            from app.services.keyword_filter import filter_advertisement_projects, _is_mobile_purchaser
        except ImportError:
            from services.keyword_filter import filter_advertisement_projects, _is_mobile_purchaser

        # ── 第一步：关键词粗筛 → 判断是否广告类 ──
        kw_result = filter_advertisement_projects(title, content)

        if not kw_result["is_ad"] or not _is_mobile_purchaser(title):
            # 非广告项目 → 行业分类器判定 + LLM 辅助提取预算/日期
            ind_result = classify_industry_and_category(title, content, self.source_key)
            if ind_result["industry_type"] == "运营商":
                # 尝试 LLM 提取预算和日期
                budget = raw.get("budget")
                deadline = raw.get("deadline", "")
                bid_date = raw.get("bid_date")
                procurement_method = raw.get("procurement_method", "公开招标")
                budget, deadline, bid_date, procurement_method = self._try_llm_extract(
                    title, content, raw, budget, deadline, bid_date, procurement_method)
                self.logger.info(
                    f"  ✅ [运营商/{ind_result['project_category']}] {title[:50]}"
                )
                return self._build_final_record(title, content, raw,
                    is_target=True, project_category=ind_result["project_category"],
                    industry_type="运营商",
                    procurement_method=procurement_method,
                    budget=budget, deadline=deadline, bid_date=bid_date)
            return self._make_skip_record(title, content, raw, "非目标")

        # ── 第二步：广告类项目 → LLM 精细分类 + 字段提取 ──

        # 中标公示跳过
        winning_keywords = ["中选候选人", "中选结果", "中选人", "中标候选人", "中标结果", "中标人", "成交候选人", "成交结果"]
        if any(kw in title for kw in winning_keywords):
            self.logger.info(f"  ⏭️ 中标公示跳过: {title[:60]}")
            return self._make_skip_record(title, content, raw, "中标公示")

        if "意见征求" in title or "技术规范书" in title or "技术评分表" in title:
            self.logger.info(f"  ⏭️ 意见征求跳过: {title[:60]}")
            return self._make_skip_record(title, content, raw, "意见征求")

        # ── LLM 分类 ──
        is_ad = False
        category = kw_result.get("category", "其他营销类")
        budget = raw.get("budget")
        registration_fee = raw.get("registration_fee")
        deposit = raw.get("deposit")
        deadline = raw.get("deadline", "")
        bid_date = raw.get("bid_date")
        procurement_method = raw.get("procurement_method", "公开招标")

        try:
            from app.services.llm_classifier import classify_and_extract
            unified = classify_and_extract(title, content)

            is_ad = unified.get("is_ad", False)
            llm_category = unified.get("category", "")

            # LLM 未配置或返回 is_ad=False 时，回退到关键词过滤器的结果
            if not is_ad:
                is_ad = kw_result.get("is_ad", False)
                llm_category = kw_result.get("category", llm_category)
                self.logger.debug(f"  LLM未确认，回退关键词: [{llm_category}] {title[:50]}")

            # LLM 有结果时优先使用
            if llm_category and llm_category != "其他营销类":
                category = llm_category
            # 否则尝试 industry_classifier 获取更精确的赛道
            elif category == "其他营销类":
                ind_result = classify_industry_and_category(title, content, self.source_key)
                if ind_result["project_category"] != "其他采购":
                    category = ind_result["project_category"]
                    self.logger.info(f"  🔄 keyword→industry_classifier: [{category}] {title[:50]}")

            if is_ad:
                # LLM 提取的值优先
                if unified.get("budget"):
                    budget = unified["budget"]
                if unified.get("registration_fee"):
                    registration_fee = unified["registration_fee"]
                if unified.get("deposit"):
                    deposit = unified["deposit"]
                if unified.get("deadline"):
                    deadline = unified["deadline"]
                if unified.get("bid_date"):
                    bid_date = unified["bid_date"]
                if unified.get("procurement_method"):
                    procurement_method = unified["procurement_method"]

                extra = f", 截止{deadline}" if deadline else ""
                if bid_date:
                    extra += f", 投标{bid_date}"
                self.logger.info(
                    f"  {'✅' if is_ad else '⏭️'} [{category}] {title[:40]}"
                    f" | 预算{budget}万{extra}"
                )
            else:
                self.logger.debug(f"  ⏭️ LLM排除: {title[:50]} — {unified.get('reason','')}")

        except Exception as e:
            self.logger.warning(f"统一LLM调用失败，回退: {e}")
            # LLM 失败时回退到关键词结果
            is_ad = True  # 已通过关键词预筛
            category = kw_result.get("category", "其他营销类")

        return self._build_final_record(title, content, raw,
            is_target=is_ad, project_category=category,
            industry_type="运营商", procurement_method=procurement_method,
            budget=budget, registration_fee=registration_fee,
            deposit=deposit, deadline=deadline, bid_date=bid_date,
            matched_keywords=kw_result.get("matched_keywords", []))

    def _make_skip_record(self, title: str, content: str, raw: Dict, reason: str) -> Dict:
        """构建跳过记录。"""
        return {
            "title": title, "purchaser": raw.get("purchaser", ""),
            "purchaser_level": raw.get("purchaser_level", ""),
            "procurement_method": raw.get("procurement_method", "公开招标"),
            "budget": raw.get("budget"), "registration_fee": raw.get("registration_fee"),
            "deposit": raw.get("deposit"), "project_category": reason,
            "industry_type": "", "announce_date": raw.get("publish_date", ""),
            "deadline": raw.get("deadline", ""), "bid_date": raw.get("bid_date"),
            "qualification_requirements": content[:2000], "original_content": content,
            "score_weight": raw.get("score_weight"), "source_url": raw.get("source_url", ""),
            "notice_type": raw.get("notice_type", "招标公告"),
            "bid_number": raw.get("bid_number", ""), "is_ad": False,
            "matched_keywords": [], "province": raw.get("province", ""),
            "city": raw.get("city", ""), "industry": raw.get("purchaser", ""),
        }

    def _build_final_record(self, title: str, content: str, raw: Dict,
                            is_target: bool, project_category: str, industry_type: str = "",
                            procurement_method: str = "公开招标", budget=None,
                            registration_fee=None, deposit=None, deadline="",
                            bid_date=None, matched_keywords=None) -> Dict:
        """构建最终记录。"""
        if matched_keywords is None:
            matched_keywords = []
        return {
            "title": title, "purchaser": raw.get("purchaser", ""),
            "purchaser_level": raw.get("purchaser_level", ""),
            "procurement_method": procurement_method,
            "budget": budget, "registration_fee": registration_fee,
            "deposit": deposit, "project_category": project_category,
            "industry_type": industry_type,
            "announce_date": raw.get("publish_date", ""),
            "deadline": deadline, "bid_date": bid_date,
            "qualification_requirements": content[:2000], "original_content": content,
            "score_weight": raw.get("score_weight"), "source_url": raw.get("source_url", ""),
            "notice_type": raw.get("notice_type", "招标公告"),
            "bid_number": raw.get("bid_number", ""), "is_ad": is_target,
            "matched_keywords": matched_keywords,
            "province": raw.get("province", ""), "city": raw.get("city", ""),
            "industry": raw.get("purchaser", ""),
        }

    # ── 主流程 ──

    def _try_llm_extract(self, title: str, content: str, raw: Dict,
                          budget, deadline: str, bid_date, procurement_method: str):
        """尝试通过 LLM 提取预算、日期等字段。原地修改传入的变量。"""
        try:
            from app.services.llm_classifier import classify_and_extract
            unified = classify_and_extract(title, content)

            if unified.get("budget"):
                budget = unified["budget"]
            if unified.get("deadline"):
                deadline = unified["deadline"]
            if unified.get("bid_date"):
                bid_date = unified["bid_date"]
            if unified.get("procurement_method"):
                procurement_method = unified["procurement_method"]
        except Exception:
            pass  # LLM 不可用时静默跳过
        return budget, deadline, bid_date, procurement_method

    def run(self, save_to_db: bool = True, **kwargs) -> List[Dict]:
        """
        执行完整采集流程：列表翻页 → 详情抓取 → 解析 → 过滤 → 入库。

        Args:
            save_to_db: 是否自动入库（通过 announcements 表）
            **kwargs: 额外参数（如 province）

        Returns:
            采集到的广告类项目列表
        """
        all_results = []
        seen_urls = set()

        self.logger.info(f"===== {self.name} 开始采集 =====")

        # 初始进度报告
        self._report_progress(10, f"开始采集 {self.name}...")

        for page in range(1, self.max_pages + 1):
            self.logger.info(f"--- 列表页 第 {page} 页 ---")

            # 计算当前页的进度范围
            page_progress_start = 10 + (page - 1) * 80 // self.max_pages
            page_progress_end = 10 + page * 80 // self.max_pages
            self._report_progress(page_progress_start, f"正在处理第 {page}/{self.max_pages} 页...")
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
                        # 从列表项继承日期（如果 parse_detail 没返回）
                        if not parsed.get("publish_date"):
                            parsed["publish_date"] = item.get("publish_date", "")

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

    # 最小公告日期保护：早于此日期的过期公告不入库（防止历史旧公告混入）
    MIN_ANNOUNCE_DATE = "2025-01-01"  # 可通过 config 覆盖

    def _save_to_db(self, record: Dict):
        """将记录保存到数据库（同步版本，线程安全，短超时）。"""
        # 过期公告保护：announce_date 早于门槛则跳过
        _ad = record.get("announce_date") or ""
        if _ad and _ad < self.MIN_ANNOUNCE_DATE:
            self.logger.debug(f"  ⏭️ 过期公告跳过({_ad}): {record.get('title', '')[:40]}")
            return
        try:
            import sqlite3
            import os
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "biaozhongbao.db")
            conn = sqlite3.connect(db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            
            cur = conn.execute("SELECT id FROM announcements WHERE title = ? LIMIT 1", (record["title"],))
            if cur.fetchone():
                conn.close()
                return
            
            conn.execute("""
                INSERT INTO announcements (title, purchaser_id, purchaser_level, procurement_method,
                    budget, registration_fee, deposit, project_category, industry_type,
                    announce_date, deadline, qualification_requirements, original_content,
                    source_url, province, city, industry, data_source)
                VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["title"],
                record.get("purchaser_level", ""),
                record.get("procurement_method", "公开招标"),
                record.get("budget"),
                record.get("registration_fee"),
                record.get("deposit"),
                record.get("project_category", ""),
                record.get("industry_type", ""),
                _parse_date(record.get("announce_date", "")) or date.today(),
                _parse_datetime(record.get("deadline", "")),
                record.get("qualification_requirements", "")[:2000],
                record.get("original_content", ""),
                record.get("source_url", ""),
                record.get("province", ""),
                record.get("city", ""),
                record.get("industry", ""),
                self.source_key,
            ))
            conn.commit()
            conn.close()
            self.logger.info(f"  💾 入库: {record['title'][:50]}")
        except sqlite3.OperationalError as e:
            if "locked" in str(e) or "database is locked" in str(e):
                self.logger.debug(f"  🔒 DB锁定，跳过入库: {record['title'][:30]}")
            else:
                self.logger.error(f"入库失败 [{record.get('title','')[:30]}]: {e}")
        except Exception as e:
            self.logger.error(f"入库失败 [{record.get('title','')[:30]}]: {e}")


def _parse_date(s: str):
    from datetime import date
    import re
    if not s:
        return None  # 空日期返回 None，不造假日期
    # 多种格式
    for fmt in [
        r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})",
        r"(\d{4})(\d{2})(\d{2})",
    ]:
        m = re.match(fmt, s.strip())
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _parse_datetime(s: str):
    from datetime import datetime
    import re
    if not s:
        return None
    # 完整日期时间
    m = re.match(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[T\s]?(\d{1,2}):(\d{2})", s.strip())
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                        int(m.group(4)), int(m.group(5)))
    # 仅日期
    m = re.match(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", s.strip())
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 17, 0)
    return None
