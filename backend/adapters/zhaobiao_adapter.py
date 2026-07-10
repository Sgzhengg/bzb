"""
中国招标网 (www.zhaobiao.cn) 爬虫适配器

网站结构分析:
  - 搜索URL: https://www.zhaobiao.cn/search/result.html
  - 列表: HTML 搜索结果, 每项含标题/地区/日期/链接
  - 详情: 独立页面, 含完整公告信息
  - 支持按关键词+地区+时间范围搜索
  - 支持分页参数

反爬策略:
  - User-Agent 轮换 (从基类继承)
  - 随机请求间隔 3-6 秒
  - 指数退避重试 (最多3次)
  - Referer 头设置
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from .base_adapter import BaseAdapter
from .pdf_parser import extract_text_from_pdf_bytes, extract_fields_from_pdf_text


class ZhaobiaoAdapter(BaseAdapter):
    """中国招标网 (www.zhaobiao.cn) 适配器"""

    BASE_URL = "https://s.zhaobiao.cn"
    SEARCH_URL = "https://s.zhaobiao.cn/s"

    # 广告类搜索关键词组合
    AD_KEYWORDS = [
        "广东移动 广告", "广东移动 品牌", "广东移动 宣传",
        "广东移动 活动", "广东移动 策划", "广东移动 创意",
        "广东移动 设计", "广东移动 媒介", "广东移动 投放",
        "广东移动 物料", "广东移动 制作", "广东移动 新媒体",
        "广东移动 视频", "广东移动 直播", "广东移动 营销",
        "中国移动广东 广告", "中国移动广东 品牌", "中国移动广东 宣传",
    ]

    def __init__(self, config: dict = None):
        default_config = {
            "name": "中国招标网",
            "base_url": self.BASE_URL,
            "min_delay": 3.0,
            "max_delay": 6.0,
            "max_retries": 3,
            "timeout": 30,
            "max_pages": 5,
            "search_keyword": "广东移动 广告",
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

        # 覆盖客户端以设置 Referer
        self._client = None

    def get_source_name(self) -> str:
        return "zhaobiao"

    def _get_client(self):
        import httpx
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                headers={
                    "User-Agent": self._next_ua(),
                    "Referer": self.BASE_URL + "/",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                },
            )
        return self._client

    # ── 列表页 ──

    def fetch_list(self, page: int = 1) -> str:
        """
        搜索列表页。

        尝试多种请求方式:
        1. GET 搜索 (params)
        2. POST 搜索 (form data)
        """
        keyword = self.config.get("search_keyword", "广东移动 广告")
        params = {
            "keyword": keyword,
            "page": page,
        }
        try:
            status, html = self._request(self.SEARCH_URL, params=params)
            if status == 200:
                return html
        except Exception:
            pass

        # POST 回退
        import httpx
        self._random_delay()
        client = self._get_client()
        resp = client.post(
            self.SEARCH_URL,
            data={"keyword": keyword, "page": str(page)},
            timeout=self.timeout,
        )
        if resp.status_code == 200:
            return resp.text

        return ""

    def parse_list(self, html: str) -> List[Dict]:
        """
        解析搜索结果 HTML。

        常见结构:
        - <div class="search-result-list"> 或 <ul class="result-list">
        - 每项: <div class="result-item"> 含 <a>标题</a> + <span>日期</span> + <span>地区</span>
        """
        soup = BeautifulSoup(html, "lxml")
        items = []

        # ── 选择器策略 ──
        selectors = [
            ".search-result-list .result-item",
            ".result-list li",
            ".search-list .item",
            "div[class*='search-result'] div[class*='item']",
            "ul.list-con li",
            ".project-list .project-item",
            ".bid-list tr",
        ]

        for selector in selectors:
            for container in soup.select(selector):
                item = self._parse_list_item(container)
                if item and self._is_gd_mobile(item["title"]):
                    items.append(item)
            if items:
                break

        # ── 通用回退: 遍历所有链接 ──
        if not items:
            for a in soup.find_all("a", href=True):
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if not title or not href or len(title) < 8:
                    continue
                # 过滤非招标链接
                if not any(kw in href for kw in ["/detail/", "/zhaobiao/", "/bid/", "detail", "zhaobiao"]):
                    continue
                if not self._is_gd_mobile(title):
                    continue

                # 尝试从父元素找日期
                parent = a.find_parent(["div", "li", "tr"])
                date_str = ""
                if parent:
                    date_el = parent.find(["span", "time", "em"], class_=re.compile(r"date|time|pub", re.I))
                    if date_el:
                        date_str = date_el.get_text(strip=True)

                items.append({
                    "title": title,
                    "publish_date": date_str,
                    "detail_url": urljoin(self.BASE_URL, href),
                    "notice_type": self._guess_type(title),
                })

        self.logger.info(f"zhaobiao.cn 列表解析: {len(items)} 条")
        return items

    def _parse_list_item(self, container) -> Optional[Dict]:
        """解析单个列表项。"""
        try:
            link = container.find("a", href=True)
            if not link:
                return None

            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or not href:
                return None

            # 日期
            date_el = container.find(["span", "time", "em", "p"],
                                     class_=re.compile(r"date|time|pub|create", re.I))
            date_str = date_el.get_text(strip=True) if date_el else ""

            # 地区/行业
            region_el = container.find(["span", "em"], class_=re.compile(r"region|area|city", re.I))
            region = region_el.get_text(strip=True) if region_el else ""

            return {
                "title": title,
                "publish_date": date_str,
                "detail_url": urljoin(self.BASE_URL, href),
                "notice_type": self._guess_type(title),
                "region": region,
            }
        except Exception:
            return None

    # ── 详情页 ──

    def fetch_detail(self, url: str) -> Tuple[str, Optional[bytes]]:
        """抓取详情页。"""
        status, html = self._request(url)

        pdf_bytes = None
        pdf_urls = self._find_pdf_links(html)
        if pdf_urls:
            import httpx
            for pdf_url in pdf_urls[:3]:
                try:
                    self._random_delay()
                    resp = httpx.get(pdf_url, timeout=30)
                    if resp.status_code == 200 and resp.content[:4] == b"%PDF":
                        pdf_bytes = resp.content
                        self.logger.info(f"PDF下载: {len(pdf_bytes)} 字节")
                        break
                except Exception:
                    continue

        return html, pdf_bytes

    def parse_detail(self, html: str, pdf_bytes: Optional[bytes] = None) -> Dict:
        """
        解析详情页，提取全部字段。
        """
        soup = BeautifulSoup(html, "lxml")

        # ── 标题 ──
        title = ""
        for selector in ["h1", ".detail-title", ".project-title", ".bid-title", "title"]:
            el = soup.select_one(selector)
            if el:
                title = el.get_text(strip=True)
                if len(title) > 5:
                    break

        # ── 页面纯文本（用于正则匹配） ──
        body = soup.find(["div", "article"], class_=re.compile(
            r"content|detail|info|main|con|article|project", re.I
        ))
        page_text = body.get_text(separator="\n", strip=True) if body else soup.get_text()
        page_text = page_text[:50000]  # 保留完整公告原文（上限5万字符）

        # ── 采购方 ──
        purchaser = self._extract_field(page_text, [
            r"(?:采购人|招标人|招标单位|业主单位|采购单位)[：:]\s*(.+?)(?:\n|$)",
            r"(?:采购人|招标人|招标单位|业主单位|采购单位)\s*[：:]\s*(.+?)(?:。|\n)",
        ]) or "中国移动通信集团广东有限公司"

        # ── 采购方层级 ──
        purchaser_level = self._guess_level(title, purchaser)

        # ── 发布日期 ──
        publish_date = ""
        m = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})", page_text)
        if m:
            publish_date = m.group(1)
        # 回退: meta 标签
        if not publish_date:
            meta = soup.find("meta", attrs={"name": re.compile(r"pubdate|publishdate|date", re.I)})
            if meta and meta.get("content"):
                publish_date = meta["content"][:10]

        # ── 截止日期 ──
        deadline = self._extract_field(page_text, [
            r"(?:投标截止|报名截止|递交截止|开标时间)[：:]\s*(.+?)(?:\n|$)",
            r"截止(?:时间|日期)[：:]\s*(.+?)(?:\n|$)",
        ])

        # ── 预算 ──
        budget = None
        for pat in [
            r"(?:预算|采购预算|项目预算|预算金额|控制价|最高限价)[：:是为]?\s*[¥￥]?\s*(\d[\d,.]*)\s*万",
            r"(?:预算|采购预算|项目预算|预算金额|控制价|最高限价)[：:是为]?\s*[¥￥]?\s*(\d{4,})\s*元",
            r"(\d+\.?\d*)\s*万元",
        ]:
            m = re.search(pat, page_text)
            if m:
                val = float(m.group(1).replace(",", ""))
                if "元" in m.group(0) and "万" not in m.group(0):
                    val = val / 10000
                budget = round(val, 2)
                break

        # ── 公告类型 ──
        notice_type = ""
        for kw in ["中标候选人", "中标结果", "中标公告", "成交公告", "招标公告", "竞争性谈判", "询价公告"]:
            if kw in page_text or kw in title:
                notice_type = kw
                break
        if not notice_type:
            notice_type = self._guess_type(title)

        # ── 项目编号 ──
        bid_number = ""
        m = re.search(r"(?:项目编号|招标编号|采购编号|标段编号)[：:]\s*([A-Za-z0-9\-_/]+)", page_text)
        if m:
            bid_number = m.group(1)

        # ── 行业分类 ──
        industry = "移动"
        if "电信" in page_text:
            industry = "电信"
        if "联通" in page_text:
            industry = "移动"

        # ── 联系方式 ──
        contact_info = self._extract_field(page_text, [
            r"(?:联系人|联系电话)[：:]\s*(.+?)(?:\n|$)",
            r"(?:联系方式)[：:]\s*(.+?)(?:\n\n|\Z)",
        ])

        # ── PDF 补充 ──
        pdf_text = ""
        if pdf_bytes:
            pdf_text = extract_text_from_pdf_bytes(pdf_bytes)
            if pdf_text:
                pdf_fields = extract_fields_from_pdf_text(pdf_text)
                if not budget:
                    budget = pdf_fields.get("budget")
                if not deadline:
                    m = re.search(r"截止[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})", pdf_text)
                    if m:
                        deadline = m.group(1)
                page_text += "\n[PDF附件]\n" + pdf_text

        return {
            "title": title,
            "purchaser": purchaser,
            "purchaser_level": purchaser_level,
            "bid_number": bid_number,
            "notice_type": notice_type,
            "publish_date": publish_date,
            "deadline": deadline,
            "budget": budget,
            "content_text": page_text,
            "source_url": "",
            "attachments": self._find_pdf_links(html),
            "industry": industry,
            "contact_info": contact_info,
        }

    # ── 辅助方法 ──

    def _extract_field(self, text: str, patterns: list) -> str:
        """多个模式尝试提取字段值。"""
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                val = m.group(1).strip()
                val = re.sub(r"<[^>]+>", "", val)
                return val
        return ""

    def _find_pdf_links(self, html: str) -> list:
        soup = BeautifulSoup(html, "lxml")
        return [urljoin(self.BASE_URL, a["href"])
                for a in soup.find_all("a", href=True)
                if a["href"].lower().endswith(".pdf")]

    def _guess_type(self, title: str) -> str:
        if "候选人" in title:
            return "中标候选人公示"
        if any(kw in title for kw in ["中标", "成交", "中选", "结果"]):
            return "中标公告"
        if "变更" in title or "澄清" in title:
            return "变更公告"
        return "招标公告"

    def _guess_level(self, title: str, purchaser: str) -> str:
        combined = f"{title} {purchaser}"
        for city in ["广州", "深圳", "东莞", "佛山", "珠海", "中山", "惠州",
                       "汕头", "江门", "湛江", "茂名", "肇庆", "梅州"]:
            if city in combined:
                return f"{city}分公司"
        return "省公司"

    @staticmethod
    def _is_gd_mobile(title: str) -> bool:
        return ("广东移动" in title or "中国移动广东" in title or
                ("移动" in title and "广东" in title))

    # ── 多关键词搜索模式 ──

    def run_multi_keyword(self, save_to_db: bool = True) -> List[Dict]:
        """
        使用多个广告类关键词组合搜索，合并去重结果。
        """
        all_results = []
        seen_urls = set()

        self.logger.info(f"===== {self.name} 多关键词搜索 =====")

        for kw in self.AD_KEYWORDS:
            self.config["search_keyword"] = kw
            self.logger.info(f"--- 搜索: {kw} ---")

            for page in range(1, self.max_pages + 1):
                try:
                    html = self.fetch_list(page=page)
                    if not html:
                        break
                    items = self.parse_list(html)
                    if not items:
                        break

                    for item in items:
                        url = item.get("detail_url", "")
                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)

                        try:
                            html_d, pdf = self.fetch_detail(url)
                            parsed = self.parse_detail(html_d, pdf)
                            parsed["source_url"] = url
                            record = self._normalize_record(parsed)

                            if record["is_ad"]:
                                all_results.append(record)
                                if save_to_db:
                                    self._save_to_db(record)
                        except Exception as e:
                            self.logger.error(f"详情: {url[:80]} - {e}")

                except Exception as e:
                    self.logger.error(f"搜索'{kw}'第{page}页失败: {e}")
                    break

        self.logger.info(f"===== {self.name} 完成: {len(all_results)} 条广告类 =====")
        self.close()
        return all_results
