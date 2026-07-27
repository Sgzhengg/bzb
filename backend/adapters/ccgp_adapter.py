"""
中国政府采购网 (ccgp.gov.cn) 爬虫适配器

财政部唯一指定政府采购信息发布平台，覆盖中央+地方全部政府单位采购公告。

网站结构：
  - 分类列表页: /cggg/zygg/{type}/  (中央)  /cggg/dfgg/{type}/ (地方)
  - 类型: gkzb(招标) jzxcs(竞争性磋商) jzxtpgg(竞争性谈判) xjgg(询价) dylygg(单一来源) zbgg(中标)
  - 分页: index_2.htm, index_3.htm ...
  - 详情页: /{type}/202607/t20260727_27014015.htm

注意：网站有反爬限制（频率检测），需严格控制请求间隔。
"""

import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_adapter import BaseAdapter


class CcgpAdapter(BaseAdapter):
    """中国政府采购网适配器"""

    def __init__(self, config: dict = None):
        default_config = {
            "name": "中国政府采购网",
            "base_url": "https://www.ccgp.gov.cn",
            "min_delay": 6.0,        # 比运营商更慢，防反爬
            "max_delay": 10.0,
            "max_retries": 3,
            "timeout": 30,
            "max_pages": 3,
            "source_key": "ccgp",
            # 要抓取的公告类型
            "categories": [
                "gkzb",      # 公开招标
                "jzxcs",     # 竞争性磋商
                "jzxtpgg",   # 竞争性谈判
                "xjgg",      # 询价
                "dylygg",    # 单一来源
            ],
            "scope": "all",  # all=中央+地方, central=仅中央, local=仅地方
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_source_name(self) -> str:
        return self.config.get("source_key", "ccgp")

    # ── 列表页 ──

    def _get_list_url(self, category: str, page: int, scope: str = "central") -> str:
        """构建分类列表页 URL。"""
        scope_path = "zygg" if scope == "central" else "dfgg"
        base = f"{self.base_url}/cggg/{scope_path}/{category}/"
        if page > 1:
            return urljoin(base, f"index_{page}.htm")
        return base

    def fetch_list(self, page: int = 1) -> str:
        """抓取列表页。由于ccgp按分类展示，此方法由 run() 内部调用分类列表。"""
        return ""

    def _fetch_list_page(self, url: str) -> str:
        """安全抓取列表页，检测反爬。"""
        for attempt in range(self.max_retries):
            try:
                status, text = self._request(url)
                if status == 200:
                    if "频繁访问" in text or "过于频繁" in text:
                        self.logger.warning(f"  触发反爬，等待30秒后重试")
                        import time
                        time.sleep(30)
                        continue
                    return text
                return ""
            except Exception as e:
                self.logger.warning(f"  请求失败(尝试{attempt+1}): {e}")
        return ""

    def parse_list(self, html: str) -> List[Dict]:
        """解析分类列表页。"""
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        items = []
        # ccgp 列表页结构：<ul class="c_list"> 或 <div class="vF_list">
        for ul in soup.select("ul.c_list, ul.vF_list, div.c_list ul"):
            for li in ul.find_all("li"):
                a = li.find("a")
                if not a:
                    continue
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if href and not href.startswith("http"):
                    href = urljoin(self.base_url, href)
                # 日期通常在 span 或 em 标签中
                date_el = li.find("span", class_=re.compile(r"date|time")) or li.find("em")
                date = date_el.get_text(strip=True) if date_el else ""
                if title:
                    items.append({
                        "title": title,
                        "url": href,
                        "date": date,
                        "publish_date": date,
                    })
        # 宽泛匹配：直接找所有含链接的 li
        if not items:
            for li in soup.find_all("li"):
                a = li.find("a")
                if not a or not a.get("href"):
                    continue
                href = a.get("href", "")
                if href.startswith("http") and "ccgp.gov.cn" in href and "cggg" in href:
                    title = a.get_text(strip=True)
                    date_el = li.find("span") or li.find("em")
                    date = date_el.get_text(strip=True) if date_el else ""
                    items.append({
                        "title": title,
                        "url": href,
                        "date": date,
                        "publish_date": date,
                    })
        return items

    # ── 详情页 ──

    def fetch_detail(self, url: str) -> Tuple[str, Optional[bytes]]:
        """抓取详情页。"""
        title = ""
        content_text = ""
        try:
            status, text = self._request(url)
            if status == 200:
                if "频繁访问" in text:
                    self.logger.warning("  详情页触发反爬")
                    import time
                    time.sleep(30)
                    return title, None
                soup = BeautifulSoup(text, "html.parser")
                h1 = soup.find("h1") or soup.find(class_=re.compile(r"title", re.I))
                if h1:
                    title = h1.get_text(strip=True)
                body = (
                    soup.find(class_=re.compile(r"content|article|detail|text|main_con", re.I))
                    or soup.find("body")
                )
                if body:
                    content_text = body.get_text(separator="\n", strip=True)
        except Exception as e:
            self.logger.warning(f"  详情失败: {e}")
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
            "title": title or "",
            "purchaser": self._extract_purchaser(content_text),
            "purchaser_level": "中央" if "部" in content_text[:200] else "地方",
            "procurement_method": self._extract_method(content_text),
            "budget": self._extract_budget_regex(content_text),
            "registration_fee": None,
            "deposit": self._extract_deposit_regex(content_text),
            "publish_date": "",
            "deadline": self._extract_deadline(content_text),
            "content_text": content_text[:50000],
            "city": self._extract_city(content_text),
            "province": "",
        }

    # ── 字段提取 ──

    def _extract_purchaser(self, content: str) -> str:
        m = re.search(r"(?:采购[人方]|招标[人方]|采购单位|采购人名称)[：:]?\s*([^\s，。,\n]{2,30})", content)
        return m.group(1) if m else ""

    def _extract_budget_regex(self, content: str) -> Optional[float]:
        patterns = [
            r"预算[总]?[金额]?[约]?[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"最高限价[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"采购[总]?金?额[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"项目预算[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"预算金额[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"预算[：:]?\s*(\d+(?:\.\d+)?)\s*万元",
        ]
        for pat in patterns:
            m = re.search(pat, content)
            if m:
                return float(m.group(1))
        return None

    def _extract_deposit_regex(self, content: str) -> Optional[float]:
        m = re.search(r"(?:投标|履约)?保证金[：:]?\s*(\d+(?:\.\d+)?)\s*万", content)
        if m:
            return float(m.group(1))
        m = re.search(r"(?:投标|履约)?保证金[：:]?\s*(\d+(?:\.\d+)?)\s*元", content)
        if m:
            val = float(m.group(1))
            return val / 10000 if val > 1000 else val
        return None

    def _extract_deadline(self, content: str) -> str:
        m = re.search(r"(?:投标|递交|提交|响应|应答)(?:文件)?(?:截止|时间|日期)[：:]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", content)
        if m:
            return m.group(1)
        m = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*\d{2}:\d{2}", content)
        return m.group(1) if m else ""

    def _extract_method(self, content: str) -> str:
        if "竞争性磋商" in content:
            return "竞争性磋商"
        if "竞争性谈判" in content:
            return "竞争性谈判"
        if "公开招标" in content:
            return "公开招标"
        if "询价" in content:
            return "询价"
        if "单一来源" in content:
            return "单一来源"
        return "公开招标"

    def _extract_city(self, content: str) -> str:
        # 从采购人/标题中提取城市
        cities = [
            "北京", "上海", "广州", "深圳", "天津", "重庆",
            "南京", "杭州", "成都", "武汉", "西安", "郑州",
            "济南", "青岛", "沈阳", "大连", "宁波", "厦门",
            "长沙", "合肥", "福州", "昆明", "贵阳", "南宁",
            "海口", "三亚", "珠海", "东莞", "佛山", "苏州",
            "无锡", "常州", "徐州", "温州", "嘉兴", "绍兴",
            "烟台", "潍坊", "临沂", "洛阳", "襄阳", "宜昌",
            "泉州", "漳州", "南昌", "太原", "石家庄", "哈尔滨",
            "长春", "兰州", "呼和浩特", "乌鲁木齐", "拉萨",
        ]
        for c in sorted(cities, key=len, reverse=True):
            if c in content[:500]:
                return c
        return ""

    def _extract_budget_with_llm(self, title: str, content: str) -> Optional[dict]:
        """LLM 兜底提取预算。"""
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
        """执行完整采集流程（按公告类型分别抓取）。"""
        province_filter = kwargs.get("province", "")
        all_results = []
        seen_urls = set()

        scope = self.config.get("scope", "all")
        categories = self.config.get("categories", ["gkzb", "jzxcs", "jzxtpgg"])
        scopes = ["central", "local"] if scope == "all" else [scope]

        self.logger.info(f"===== {self.name} 开始采集 (范围={'中央+地方' if scope == 'all' else scope}) =====")

        for s in scopes:
            for cat in categories:
                cat_name = {"gkzb": "公开招标", "jzxcs": "竞争性磋商", "jzxtpgg": "竞争性谈判",
                            "xjgg": "询价", "dylygg": "单一来源", "zbgg": "中标公告"}.get(cat, cat)
                scope_name = "中央" if s == "central" else "地方"
                self.logger.info(f"--- {scope_name}{cat_name} ---")

                for page in range(1, self.max_pages + 1):
                    list_url = self._get_list_url(cat, page, s)
                    html = self._fetch_list_page(list_url)
                    if not html:
                        break

                    items = self.parse_list(html)
                    if not items:
                        self.logger.info(f"  第 {page} 页无结果")
                        break

                    self.logger.info(f"  第 {page} 页: {len(items)} 条")

                    for item in items:
                        url = item.get("url", "")
                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)

                        try:
                            html_d, pdf_b = self.fetch_detail(url)
                            parsed = self.parse_detail(html_d, pdf_b)
                            parsed["source_url"] = url
                            parsed["purchaser_level"] = "中央" if s == "central" else "地方"
                            parsed["province"] = parsed.get("province") or kwargs.get("date_from", "")

                            # LLM 兜底提取预算
                            if parsed.get("budget") is None and parsed.get("content_text") and len(parsed.get("content_text", "")) > 100:
                                try:
                                    llm_data = self._extract_budget_with_llm(parsed["title"], parsed["content_text"])
                                    if llm_data and llm_data.get("budget_wan"):
                                        parsed["budget"] = llm_data["budget_wan"]
                                except Exception:
                                    pass

                            record = self._normalize_record(parsed)
                            if record["is_ad"]:
                                all_results.append(record)
                                self.logger.info(f"  ✅ {record['title'][:50]} | {record.get('project_category', '')}")
                            else:
                                self.logger.debug(f"  ⏭️ 非广告: {record['title'][:50]}")

                            if save_to_db and record["is_ad"]:
                                self._save_to_db(record)

                        except Exception as e:
                            self.logger.warning(f"  详情失败: {url[:60]} - {e}")
                            continue

        self.logger.info(f"===== {self.name} 采集完成: {len(all_results)} 条 =====")
        return all_results
