"""
各省公共资源交易平台通用适配器

通过省份配置驱动，支持多个省份的公共资源交易平台采集。

配置方式（adapter_config.yaml）：
  gx_ggzy:
    enabled: true
    module: "adapters.province_ggzy_adapter"
    class_name: "ProvinceGgzyAdapter"
    config:
      base_url: "http://gxggzy.gxzf.gov.cn"
      province: "广西"
      max_pages: 3
      source_key: "gx_ggzy"

省份平台差异通过 extract_list_items / extract_detail_text 子类覆盖处理。
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup

from .base_adapter import BaseAdapter


class ProvinceGgzyAdapter(BaseAdapter):
    """各省公共资源交易平台通用适配器"""

    def __init__(self, config: dict = None):
        default_config = {
            "name": "公共资源交易平台",
            "base_url": "",
            "province": "",
            "min_delay": 4.0,
            "max_delay": 7.0,
            "max_retries": 3,
            "timeout": 30,
            "max_pages": 3,
            "search_keyword": "",
            "search_region": "",
            "source_key": "ggzy",
            "search_url": "/search.html",          # 搜索接口路径（可覆盖）
            "list_selector": "ul.list-wrap li, .ewb-list li, table tr",  # 列表选择器
            "title_selector": "a",                  # 标题提取选择器
            "date_selector": ".time, span.date, td:nth-child(2)",  # 日期选择器
            "detail_link_selector": "a",            # 详情链接选择器
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_source_name(self) -> str:
        return self.config.get("source_key", "ggzy")

    # ── 列表页抓取 ──

    def fetch_list(self, page: int = 1) -> str:
        """抓取搜索列表页。优先用搜索接口，失败则用列表页。"""
        region = self.config.get("search_region", "")
        keyword = self.config.get("search_keyword", "广告")
        base_url = self.config.get("base_url", "")
        search_path = self.config.get("search_url", "/search.html")

        # 尝试搜索接口
        search_url = urljoin(base_url, search_path)
        params = {
            "keyword": f"{region} {keyword}",
            "pageNum": page,
            "pageSize": 20,
        }
        try:
            resp = self._request("GET", search_url, params=params)
            if resp and resp.status_code == 200:
                return resp.text
        except Exception:
            pass

        # 备选：直接翻列表页
        list_url = urljoin(base_url, f"/trade/bulletin/list.html?page={page}")
        try:
            resp = self._request("GET", list_url)
            if resp and resp.status_code == 200:
                return resp.text
        except Exception:
            pass

        return ""

    def parse_list(self, html: str) -> List[Dict]:
        """解析列表页，提取公告条目。"""
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        items = self.extract_list_items(soup)
        results = []
        for item in items:
            try:
                parsed = self._parse_list_item(item)
                if parsed and parsed.get("title"):
                    results.append(parsed)
            except Exception:
                continue
        return results

    def extract_list_items(self, soup: BeautifulSoup) -> list:
        """提取列表项DOM元素。子类可覆盖。"""
        selector = self.config.get("list_selector", "ul.list-wrap li, .ewb-list li, table tr")
        items = soup.select(selector)
        if not items:
            # 宽泛匹配：找含链接的 li 或 div
            items = soup.find_all(["li", "div", "tr"], recursive=True)
            items = [it for it in items if it.find("a") and it.get_text(strip=True)]
        return items

    def _parse_list_item(self, item) -> Optional[Dict]:
        """从列表项DOM提取标题、日期、链接。"""
        # 标题
        title_sel = self.config.get("title_selector", "a")
        title_el = item.select_one(title_sel) if title_sel else item.find("a")
        if not title_el:
            title_el = item.find("a")
        title = (title_el.get_text(strip=True) or "") if title_el else ""

        # 详情链接
        link_sel = self.config.get("detail_link_selector", "a")
        link_el = item.select_one(link_sel) if link_sel else title_el
        if not link_el:
            link_el = title_el
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = urljoin(self.config.get("base_url", ""), href)

        # 日期
        date = ""
        date_sel = self.config.get("date_selector", ".time, span.date, td:nth-child(2)")
        if date_sel:
            date_el = item.select_one(date_sel)
            if date_el:
                date = date_el.get_text(strip=True) or ""

        if not title:
            return None

        return {
            "title": title.strip(),
            "url": href,
            "date": date.strip(),
            "publish_date": date.strip(),
        }

    # ── 详情页 ──

    def fetch_detail(self, url: str) -> Tuple[str, Optional[bytes]]:
        """抓取详情页。"""
        title = ""
        content_text = ""
        try:
            resp = self._request("GET", url)
            if resp and resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                title_el = soup.find("h1") or soup.find(class_=re.compile(r"title", re.I))
                if title_el:
                    title = title_el.get_text(strip=True)
                # 提取正文
                body_el = (
                    soup.find(class_=re.compile(r"content|article|detail|text", re.I))
                    or soup.find("body")
                )
                if body_el:
                    content_text = body_el.get_text(separator="\n", strip=True)
        except Exception:
            pass
        return title, content_text.encode("utf-8") if content_text else None

    def parse_detail(self, html: str, pdf_bytes: Optional[bytes] = None) -> Dict:
        """解析详情页，提取全部字段。"""
        title = html or ""
        content_text = ""
        if pdf_bytes:
            try:
                content_text = pdf_bytes.decode("utf-8", errors="replace")
            except Exception:
                content_text = title
        if not content_text:
            content_text = title

        return {
            "title": title or self._current_item_title or "",
            "purchaser": self._extract_purchaser(content_text),
            "purchaser_level": "省公司" if "分公司" not in content_text else "地市公司",
            "procurement_method": self._extract_method(content_text),
            "budget": self._extract_budget_regex(content_text),
            "registration_fee": self._extract_reg_fee(content_text),
            "deposit": self._extract_deposit_regex(content_text),
            "publish_date": "",
            "deadline": self._extract_deadline(content_text),
            "content_text": content_text[:50000],
            "city": self._extract_city(content_text),
            "province": self.config.get("search_region", ""),
        }

    # ── 正则提取 ──

    def _extract_purchaser(self, content: str) -> str:
        m = re.search(r"(?:采购[人方]|招标[人方]|业主)[：:]?\s*([^\s，。,\n]{2,30})", content)
        return m.group(1) if m else ""

    def _extract_budget_regex(self, content: str) -> Optional[float]:
        patterns = [
            r"预算[总]?[金额]?[约]?[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"最高限价[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"采购[总]?金?额[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"项目预算[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"预算金额[：:]?\s*(\d+(?:\.\d+)?)\s*万",
        ]
        for pat in patterns:
            m = re.search(pat, content)
            if m:
                return float(m.group(1))
        return None

    def _extract_reg_fee(self, content: str) -> Optional[float]:
        m = re.search(r"(?:招标文件|采购文件|标书)[工]?本?费[：:]?\s*(\d+(?:\.\d+)?)\s*元?", content)
        if m:
            val = float(m.group(1))
            return val / 10000 if val > 1000 else val
        return None

    def _extract_deposit_regex(self, content: str) -> Optional[float]:
        m = re.search(r"(?:投标|询价|谈判|磋商|询比)?保证金[：:]?\s*(\d+(?:\.\d+)?)\s*万", content)
        if m:
            return float(m.group(1))
        m = re.search(r"(?:投标|询价|谈判|磋商|询比)?保证金[：:]?\s*(\d+(?:\.\d+)?)\s*元", content)
        if m:
            return float(m.group(1)) / 10000
        return None

    def _extract_deadline(self, content: str) -> str:
        m = re.search(r"(?:报名|投标|递交|应答|响应|申请)(?:截止|文件递交)[时间日期]?[：:]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", content)
        if m:
            return m.group(1)
        m = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*(?:\d{2}:\d{2})?", content)
        return m.group(1) if m else ""

    def _extract_method(self, content: str) -> str:
        if "公开招标" in content:
            return "公开招标"
        if "竞争性谈判" in content:
            return "竞争性谈判"
        if "询价" in content or "询比" in content:
            return "公开询比"
        if "单一来源" in content:
            return "单一来源"
        if "竞争性磋商" in content:
            return "竞争性谈判"
        return "公开招标"

    def _extract_city(self, content: str) -> str:
        cities = [
            "广州", "深圳", "东莞", "佛山", "珠海", "惠州", "中山",
            "江门", "汕头", "湛江", "茂名", "肇庆", "梅州", "汕尾",
            "河源", "阳江", "清远", "韶关", "潮州", "揭阳", "云浮",
            "南宁", "柳州", "桂林", "玉林", "梧州", "北海",
            "福州", "厦门", "泉州", "漳州", "龙岩",
            "杭州", "宁波", "温州", "嘉兴", "湖州",
            "长沙", "株洲", "湘潭", "衡阳",
            "合肥", "芜湖", "蚌埠",
            "济南", "青岛", "烟台", "潍坊",
            "海口", "三亚",
        ]
        for c in sorted(cities, key=len, reverse=True):
            if c in content:
                return c
        return ""

    def _extract_budget_with_llm(self, title: str, content: str) -> Optional[dict]:
        """LLM 兜底提取预算（复用联通适配器的同步包装）。"""
        try:
            import asyncio
            from app.services.llm_budget_extractor import extract_budget_with_llm

            async def _call():
                return await extract_budget_with_llm(title, content[:4000])

            return asyncio.run(_call())
        except Exception:
            return None

    # ── 执行采集 ──

    def run(self, save_to_db: bool = True, **kwargs) -> List[Dict]:
        """执行完整采集流程。"""
        province_filter = kwargs.get("province", "")
        all_results = []
        seen_urls = set()

        self.logger.info(f"===== {self.name} 开始采集 (省份={province_filter or self.config.get('search_region', '不限')}) =====")

        for page in range(1, self.max_pages + 1):
            try:
                html = self.fetch_list(page)
                if not html:
                    break
                items = self.parse_list(html)
                if not items:
                    self.logger.info(f"  第 {page} 页无结果，停止翻页")
                    break
                self.logger.info(f"  第 {page} 页: {len(items)} 条")

                for item in items:
                    url = item.get("url", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # 保存当前标题以便 parse_detail 使用
                    self._current_item_title = item.get("title", "")

                    # 抓取详情
                    try:
                        html_detail, pdf_bytes = self.fetch_detail(url)
                        parsed = self.parse_detail(html_detail, pdf_bytes)
                        parsed["source_url"] = url
                        parsed["publish_date"] = parsed.get("publish_date") or item.get("publish_date", "")
                        parsed["city"] = parsed.get("city") or item.get("city", "")
                        parsed["province"] = parsed.get("province") or self.config.get("search_region", "")

                        # LLM 兜底提取预算
                        if parsed.get("budget") is None and parsed.get("content_text") and len(parsed.get("content_text", "")) > 100:
                            try:
                                llm_data = self._extract_budget_with_llm(parsed["title"], parsed["content_text"])
                                if llm_data and llm_data.get("budget_wan"):
                                    parsed["budget"] = llm_data["budget_wan"]
                                    self.logger.info(f"  🤖 LLM提取预算: {parsed['budget']}万")
                            except Exception:
                                pass

                        record = self._normalize_record(parsed)
                        if record["is_ad"]:
                            all_results.append(record)
                            self.logger.info(f"  ✅ {record['title'][:60]} | {record.get('project_category', '')}")
                        else:
                            self.logger.debug(f"  ⏭️ 非广告: {record['title'][:60]}")

                        if save_to_db and record["is_ad"]:
                            self._save_to_db(record)

                    except Exception as e:
                        self.logger.warning(f"  详情失败: {url[:60]} - {e}")
                        continue

            except Exception as e:
                self.logger.error(f"  第 {page} 页失败: {e}")
                break

        self.logger.info(f"===== {self.name} 采集完成: {len(all_results)} 条 =====")
        return all_results
