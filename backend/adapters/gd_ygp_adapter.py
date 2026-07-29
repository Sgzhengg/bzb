"""
全国公共资源交易平台（广东省）— ygp.gdzwfw.gov.cn 爬虫适配器

网站特点:
  - 聚合全省各地市公共资源交易信息
  - 列表页可能是 JSON 接口返回（AJAX 加载）
  - 需要从列表跳转到原始公告页面（可能是各地市子站）
  - 项目信息更结构化，但需要解析 JSON 响应
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_adapter import BaseAdapter
from .pdf_parser import extract_text_from_pdf_bytes, extract_fields_from_pdf_text


class GdYgpAdapter(BaseAdapter):
    """全国公共资源交易平台（广东省）适配器"""

    def __init__(self, config: dict = None):
        default_config = {
            "name": "广东公共资源交易平台",
            "base_url": "https://ygp.gdzwfw.gov.cn",
            "min_delay": 4.0,
            "max_delay": 7.0,
            "max_retries": 3,
            "timeout": 30,
            "max_pages": 5,
            "search_keyword": "广东移动 广告",
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_source_name(self) -> str:
        return "gd_ygp"

    # ── 列表页 ──

    def fetch_list(self, page: int = 1) -> str:
        """
        抓取列表页。

        尝试多种 URL 模式：
        1. JSON API 接口
        2. 搜索参数 HTML 页面
        """
        # 模式1: JSON API（新版接口）
        api_urls = [
            f"{self.base_url}/ggzy-portal/api/search/news",
            f"{self.base_url}/api/search/announcement",
        ]
        for api_url in api_urls:
            try:
                params = {
                    "keyword": self.config.get("search_keyword", "广东移动"),
                    "pageNum": page,
                    "pageSize": 20,
                    "region": "广东",
                }
                status, text = self._request(api_url, params=params)
                if status == 200 and text.strip().startswith("{"):
                    return text  # JSON 格式
            except Exception:
                continue

        # 模式2: HTML 页面
        html_url = f"{self.base_url}/#/ggzy-portal/search/index"
        params = {"keyword": "广东移动", "page": page}
        status, html = self._request(html_url, params=params)
        return html

    def parse_list(self, response: str) -> List[Dict]:
        """
        解析列表响应（可能是 JSON 或 HTML）。
        """
        # ── JSON 格式 ──
        if response.strip().startswith("{"):
            return self._parse_json_list(response)

        # ── HTML 格式 ──
        return self._parse_html_list(response)

    def _parse_json_list(self, json_text: str) -> List[Dict]:
        """解析 JSON API 返回的列表。"""
        items = []
        try:
            data = json.loads(json_text)
            # 常见 JSON 结构: {"data": {"list": [...]}} 或 {"data": [...]}
            records = []
            if isinstance(data, dict):
                body = data.get("data", data)
                if isinstance(body, dict):
                    records = body.get("list", body.get("records", []))
                elif isinstance(body, list):
                    records = body
            elif isinstance(data, list):
                records = data

            for rec in records:
                title = rec.get("title", "") or rec.get("noticeName", "") or rec.get("name", "")
                if not title or not self._is_gd_mobile(title):
                    continue
                detail_url = rec.get("url", "") or rec.get("detailUrl", "") or rec.get("linkUrl", "")
                if detail_url and not detail_url.startswith("http"):
                    detail_url = urljoin(self.base_url, detail_url)
                items.append({
                    "title": title,
                    "publish_date": rec.get("publishTime", "") or rec.get("createTime", ""),
                    "detail_url": detail_url,
                    "notice_type": rec.get("noticeType", "") or self._guess_type(title),
                })
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON解析失败: {e}")

        self.logger.info(f"JSON列表解析: {len(items)} 条")
        return items

    def _parse_html_list(self, html: str) -> List[Dict]:
        """解析 HTML 列表页。"""
        soup = BeautifulSoup(html, "lxml")
        items = []

        # 各类列表容器
        for container in soup.select(
            ".news-list li, .notice-list li, .result-list li, "
            "tr[class*='item'], div[class*='notice-item']"
        ):
            link = container.find("a")
            if not link:
                continue
            title = link.get_text(strip=True)
            if not title or not self._is_gd_mobile(title):
                continue
            date_elem = container.find(["span", "time"], class_=re.compile(r"date|time", re.I))
            items.append({
                "title": title,
                "publish_date": date_elem.get_text(strip=True) if date_elem else "",
                "detail_url": urljoin(self.base_url, link.get("href", "")),
                "notice_type": self._guess_type(title),
            })

        self.logger.info(f"HTML列表解析: {len(items)} 条")
        return items

    # ── 详情页 ──

    def fetch_detail(self, url: str) -> Tuple[str, Optional[bytes]]:
        """
        抓取详情页。该平台可能跳转到子站，需跟踪重定向。
        """
        status, html = self._request(url)

        # 检测跳转后的真实页面
        soup = BeautifulSoup(html, "lxml")
        real_url = self._find_real_detail_url(soup)
        if real_url and real_url != url:
            self.logger.info(f"跟踪跳转: {url[:80]} → {real_url[:80]}")
            self._random_delay()
            status2, html2 = self._request(real_url)
            if status2 == 200:
                html = html2

        pdf_bytes = None
        pdf_urls = self._find_pdf_links(html)
        if pdf_urls:
            for pdf_url in pdf_urls[:2]:
                try:
                    self._random_delay()
                    import httpx
                    resp = httpx.get(pdf_url, timeout=30)
                    if resp.status_code == 200 and resp.content[:4] == b"%PDF":
                        pdf_bytes = resp.content
                        break
                except Exception as e:
                    self.logger.warning(f"PDF: {pdf_url[:80]} - {e}")

        return html, pdf_bytes

    def parse_detail(self, html: str, pdf_bytes: Optional[bytes] = None) -> Dict:
        """解析详情页。"""
        soup = BeautifulSoup(html, "lxml")

        title = self._extract_meta(soup, html, ["h1", "h2"], r"title")
        publish_date = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})", html)
        publish_date = publish_date.group(1) if publish_date else ""

        deadline = ""
        for pat in [r"截止[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s*\d{1,2}:\d{2})",
                     r"开标时间[：:]\s*(.+?)(?:\n|$)"]:
            m = re.search(pat, html)
            if m:
                deadline = m.group(1).strip()
                break

        purchaser = ""
        for pat in [r"(?:采购人|招标人|招标单位)[：:]\s*(.+?)(?:\n|$)",
                     r"业主单位[：:]\s*(.+?)(?:\n|$)"]:
            m = re.search(pat, html)
            if m:
                purchaser = m.group(1).strip()
                break

        notice_type = ""
        for kw in ["中标候选人", "中标结果", "中标公告", "成交公告", "招标公告", "变更公告"]:
            if kw in html:
                notice_type = kw
                break

        content_div = soup.find(["div", "article"], class_=re.compile(
            r"content|article|detail|info", re.I
        ))
        page_text = content_div.get_text(separator="\n", strip=True) if content_div else soup.get_text()

        budget = None
        for pat in [r"预算[：:]\s*(\d+\.?\d*)\s*万", r"(\d+\.?\d*)\s*万元"]:
            m = re.search(pat, page_text)
            if m:
                budget = float(m.group(1))
                break

        if pdf_bytes:
            pdf_text = extract_text_from_pdf_bytes(pdf_bytes)
            if pdf_text:
                pdf_fields = extract_fields_from_pdf_text(pdf_text)
                if not budget:
                    budget = pdf_fields.get("budget")
                page_text += "\n[PDF]\n" + pdf_text

        return {
            "title": title,
            "purchaser": purchaser or "中国移动通信集团广东有限公司",
            "purchaser_level": self._guess_level(title, purchaser),
            "bid_number": "",
            "notice_type": notice_type or "招标公告",
            "publish_date": publish_date,
            "deadline": deadline,
            "budget": budget,
            "content_text": page_text,
            "source_url": "",
            "attachments": self._find_pdf_links(html),
        }

    # ── 辅助 ──

    def _extract_meta(self, soup, html, tags, pattern):
        for tag in tags:
            for el in soup.find_all(tag):
                t = el.get_text(strip=True)
                if len(t) > 5:
                    return t
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else ""

    def _find_real_detail_url(self, soup):
        iframe = soup.find("iframe")
        if iframe and iframe.get("src"):
            return urljoin(self.base_url, iframe["src"])
        for a in soup.find_all("a", string=re.compile(r"原文|原始|查看详情|跳转")):
            return urljoin(self.base_url, a.get("href", ""))
        return None

    def _find_pdf_links(self, html):
        soup = BeautifulSoup(html, "lxml")
        return [urljoin(self.base_url, a["href"]) for a in soup.find_all("a", href=True)
                if a["href"].lower().endswith(".pdf")]

    def _guess_type(self, title):
        if any(kw in title for kw in ["中标", "成交", "中选", "结果"]):
            return "中标公告"
        if "候选人" in title:
            return "中标候选人公示"
        return "招标公告"

    def _guess_level(self, title, purchaser):
        combined = f"{title} {purchaser}"
        for city in ["广州", "深圳", "东莞", "佛山", "珠海", "中山", "惠州"]:
            if city in combined:
                return f"{city}分公司"
        return "省公司"

    @staticmethod
    def _is_gd_mobile(title: str) -> bool:
        return ("广东移动" in title or "中国移动广东" in title or
                ("移动" in title and "广东" in title))
