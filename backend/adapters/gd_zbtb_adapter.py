"""
广东省招标投标监管网 (zbtb.gd.gov.cn) 爬虫适配器

网站结构分析:
  - 列表页: /cms/xxgk/ 或搜索接口返回 HTML
  - 列表项: <li> 或 <table> 包含标题、日期、链接
  - 详情页: HTML 页面，部分信息在 PDF 附件中
  - 搜索参数: 可通过 POST 搜索或 GET 带参数查询
"""

import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_adapter import BaseAdapter
from .pdf_parser import extract_text_from_pdf_bytes, extract_fields_from_pdf_text


class GzZbtbAdapter(BaseAdapter):
    """广东省招标投标监管网适配器"""

    def __init__(self, config: dict = None):
        default_config = {
            "name": "广东招标投标监管网",
            "base_url": "https://zbtb.gd.gov.cn",
            "min_delay": 4.0,
            "max_delay": 7.0,
            "max_retries": 3,
            "timeout": 30,
            "max_pages": 5,
            # 搜索参数
            "search_keyword": "广东移动",
            "search_region": "广东",
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

        # 新版搜索API（2026年更新）
        self.search_url = urljoin(self.base_url, "/api/search/announcement")

    def get_source_name(self) -> str:
        return "gd_zbtb"

    # ── 列表页 ──

    def fetch_list(self, page: int = 1) -> str:
        """抓取搜索结果列表页。"""
        params = {
            "keyword": self.config.get("search_keyword", "广东移动"),
            "page": page,
            "pageSize": 20,
        }
        status, html = self._request(self.search_url, params=params)
        return html

    def parse_list(self, html: str) -> List[Dict]:
        """解析列表页 HTML，提取公告摘要。"""
        soup = BeautifulSoup(html, "lxml")
        items = []

        # ── 策略1: 标准表格结构 ──
        for row in soup.select("table tbody tr, .list-table tr, .xxgk-table tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            item = self._parse_row(cells)
            if item and self._is_gd_mobile_related(item["title"]):
                items.append(item)

        # ── 策略2: <li> 列表结构 ──
        if not items:
            for li in soup.select("ul.list li, .xxgk-list li, .news-list li"):
                link = li.find("a")
                if not link:
                    continue
                title = link.get_text(strip=True)
                if not title or not self._is_gd_mobile_related(title):
                    continue
                date_span = li.find(["span", "em"], class_=re.compile(r"date|time", re.I))
                date_str = date_span.get_text(strip=True) if date_span else ""
                items.append({
                    "title": title,
                    "publish_date": date_str,
                    "detail_url": urljoin(self.base_url, link.get("href", "")),
                    "notice_type": self._guess_type(title),
                })

        # ── 策略3: 通用链接遍历 ──
        if not items:
            for a in soup.find_all("a", href=True):
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if not title or not href:
                    continue
                if self._is_gd_mobile_related(title) and any(
                    ext in href for ext in [".html", ".shtml", "detail", "content", "info"]
                ):
                    items.append({
                        "title": title,
                        "publish_date": "",
                        "detail_url": urljoin(self.base_url, href),
                        "notice_type": self._guess_type(title),
                    })

        self.logger.info(f"列表解析: {len(items)} 条广东移动相关公告")
        return items

    def _parse_row(self, cells) -> Optional[Dict]:
        """从表格行解析公告条目。"""
        try:
            link = cells[0].find("a")
            if not link:
                return None
            title = link.get_text(strip=True)
            href = link.get("href", "")
            date_str = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            return {
                "title": title,
                "publish_date": date_str,
                "detail_url": urljoin(self.base_url, href),
                "notice_type": self._guess_type(title),
            }
        except Exception:
            return None

    # ── 详情页 ──

    def fetch_detail(self, url: str) -> Tuple[str, Optional[bytes]]:
        """抓取详情页。返回 (HTML, PDF_bytes_or_None)。"""
        status, html = self._request(url)
        pdf_bytes = None

        # 检测并下载 PDF 附件
        pdf_urls = self._find_pdf_links(html)
        if pdf_urls:
            self.logger.info(f"发现 {len(pdf_urls)} 个PDF附件")
            for pdf_url in pdf_urls[:2]:  # 最多下载2个
                try:
                    self._random_delay()
                    status2, content = self._request(pdf_url)
                    if isinstance(content, str):
                        import httpx
                        resp = httpx.get(pdf_url, timeout=30)
                        if resp.status_code == 200:
                            pdf_bytes = resp.content
                    elif isinstance(content, bytes):
                        pdf_bytes = content
                    break
                except Exception as e:
                    self.logger.warning(f"PDF下载失败: {pdf_url[:80]} - {e}")

        return html, pdf_bytes

    def parse_detail(self, html: str, pdf_bytes: Optional[bytes] = None) -> Dict:
        """解析详情页。"""
        soup = BeautifulSoup(html, "lxml")

        # 基础字段
        title = self._extract_title(soup)
        publish_date = self._extract_date(soup, html)
        deadline = self._extract_deadline(soup, html)
        purchaser = self._extract_purchaser(soup, html)
        notice_type = self._extract_notice_type(soup, html)
        bid_number = self._extract_bid_number(soup, html)

        # 正文文本（HTML可见部分）
        content_div = soup.find(["div", "article"], class_=re.compile(
            r"content|article|detail|info|xxgk_con", re.I
        ))
        page_text = content_div.get_text(separator="\n", strip=True) if content_div else soup.get_text()

        # 预算
        budget = None
        for pat in [r"预算[：:]\s*(\d+\.?\d*)\s*万", r"(\d+\.?\d*)\s*万元"]:
            m = re.search(pat, page_text)
            if m:
                budget = float(m.group(1))
                break

        # PDF 文本补充
        pdf_text = ""
        if pdf_bytes:
            pdf_text = extract_text_from_pdf_bytes(pdf_bytes)
            if pdf_text:
                pdf_fields = extract_fields_from_pdf_text(pdf_text)
                if not budget:
                    budget = pdf_fields.get("budget")
                page_text += "\n[PDF附件]\n" + pdf_text

        return {
            "title": title,
            "purchaser": purchaser,
            "purchaser_level": self._guess_level(title, purchaser),
            "bid_number": bid_number,
            "notice_type": notice_type,
            "publish_date": publish_date,
            "deadline": deadline,
            "budget": budget,
            "content_text": page_text,
            "source_url": "",
            "attachments": self._find_pdf_links(html),
        }

    # ── 提取辅助方法 ──

    def _extract_title(self, soup: BeautifulSoup) -> str:
        for tag in soup.find_all(["h1", "h2", "h3"], class_=re.compile(r"title|bt", re.I)):
            t = tag.get_text(strip=True)
            if len(t) > 5:
                return t
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else ""

    def _extract_date(self, soup: BeautifulSoup, html: str) -> str:
        m = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})", html)
        return m.group(1) if m else ""

    def _extract_deadline(self, soup: BeautifulSoup, html: str) -> str:
        for pat in [r"截止[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s*\d{1,2}:\d{2})",
                     r"投标截止[：:]\s*(.+?)(?:\n|$)",
                     r"递交截止[：:]\s*(.+?)(?:\n|$)"]:
            m = re.search(pat, html)
            if m:
                return m.group(1).strip()
        return ""

    def _extract_purchaser(self, soup: BeautifulSoup, html: str) -> str:
        for pat in [r"采购人[：:]\s*(.+?)(?:\n|$)", r"招标人[：:]\s*(.+?)(?:\n|$)",
                     r"业主[：:]\s*(.+?)(?:\n|$)"]:
            m = re.search(pat, html)
            if m:
                val = m.group(1).strip()
                val = re.sub(r"<[^>]+>", "", val)  # 去除HTML标签
                return val
        return "中国移动通信集团广东有限公司"

    def _extract_notice_type(self, soup: BeautifulSoup, html: str) -> str:
        if "中标" in html or "成交" in html:
            return "中标公告"
        if "候选人" in html:
            return "中标候选人公示"
        if "变更" in html or "澄清" in html:
            return "变更公告"
        return "招标公告"

    def _extract_bid_number(self, soup: BeautifulSoup, html: str) -> str:
        m = re.search(r"(?:项目编号|招标编号|采购编号)[：:]\s*([A-Za-z0-9\-]+)", html)
        return m.group(1) if m else ""

    def _find_pdf_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "lxml")
        pdfs = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                pdfs.append(urljoin(self.base_url, href))
        return pdfs

    def _guess_type(self, title: str) -> str:
        if any(kw in title for kw in ["中标", "成交", "中选", "结果"]):
            return "中标公告"
        if "候选人" in title:
            return "中标候选人公示"
        return "招标公告"

    def _guess_level(self, title: str, purchaser: str) -> str:
        combined = f"{title} {purchaser}"
        cities = ["广州", "深圳", "东莞", "佛山", "珠海", "中山", "惠州",
                   "汕头", "江门", "湛江", "茂名", "肇庆", "梅州"]
        for city in cities:
            if city in combined:
                return f"{city}分公司"
        return "省公司"

    @staticmethod
    def _is_gd_mobile_related(title: str) -> bool:
        return ("广东移动" in title or "中国移动广东" in title or
                ("移动" in title and "广东" in title))
