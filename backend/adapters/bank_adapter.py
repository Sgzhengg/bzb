"""
银行采购平台适配器 — 建设银行龙集采 (ibuy.ccb.com) + 金采网 (cfcpn.com)

数据源:
  - 建设银行 ibuy.ccb.com (龙集采) — SPA, 需 Playwright 渲染
  - 金采网 cfcpn.com (聚合源) — SPA, 需 Playwright 渲染
  - 后续扩展: 工行/农行/中行/交行

设计:
  - 使用 Playwright 渲染 SPA 页面获取公告列表
  - 仅采集广告/宣传/品牌/营销类项目
  - 行业固定为"银行"，类别为"营销宣传"
"""

import re, time
from typing import List, Dict, Tuple, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_adapter import BaseAdapter


class BankAdapter(BaseAdapter):
    """银行采购平台统一适配器"""

    # 平台列表（可公开访问的银行采购平台）
    PLATFORMS = [
        {
            "name": "建设银行龙集采",
            "url": "https://ibuy.ccb.com/cms/index.html",
        },
        {
            "name": "交通银行智采平台",
            "url": "https://bocom-gys.bankcomm.com/espuser/login",
        },
    ]

    # 广告关键词（银行类）
    AD_KEYWORDS = [
        "广告", "宣传", "品牌", "营销", "活动策划", "物料设计",
        "物料制作", "视频制作", "新媒体", "公众号", "抖音",
        "推广", "促销", "礼品", "海报", "宣传片", "拍摄",
        "设计服务", "品牌推广", "营销活动", "广告服务",
        "媒体投放", "户外广告", "网络广告", "朋友圈广告",
        "短信营销", "信用卡营销", "积分活动", "客户活动",
    ]

    # 银行识别关键词
    BANK_KEYWORDS = [
        "银行", "建行", "工行", "农行", "中行", "交行", "招行",
        "工商银行", "建设银行", "农业银行", "中国银行", "交通银行",
        "招商银行", "浦发银行", "中信银行", "光大银行", "民生银行",
        "兴业银行", "平安银行", "华夏银行", "广发银行", "邮储银行",
        "北京银行", "上海银行", "宁波银行", "苏州银行",
    ]

    def __init__(self, config: dict = None):
        default_config = {
            "name": "银行采购平台",
            "base_url": "https://ibuy.ccb.com",
            "min_delay": 2.0,
            "max_delay": 4.0,
            "max_retries": 2,
            "timeout": 30,
            "max_pages": 1,
            "source_key": "bank",
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

        self._seen_urls = set()

    def get_source_name(self) -> str:
        return "bank"

    # ── Playwright 渲染 + 列表采集 ──

    def _render_page(self, url: str, wait_ms: int = 3000) -> str:
        """用 Playwright 渲染 SPA 页面，返回渲染后的 HTML。"""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=30000, wait_until="networkidle")
                page.wait_for_timeout(wait_ms)
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            self.logger.warning(f"Playwright 渲染失败: {e}")
            return ""

    def fetch_list(self, page: int = 1) -> str:
        """用 Playwright 渲染建设银行龙集采首页。"""
        return self._render_page("https://ibuy.ccb.com/cms/index.html", wait_ms=3000)

    def parse_list(self, html: str) -> List[Dict]:
        """解析龙集采首页 HTML，提取银行广告项目。"""
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        items = []

        # 遍历所有链接，匹配银行广告关键词
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if not title or len(title) < 10:
                continue
            if not self._is_bank(title):
                continue
            if not self._is_ad(title):
                continue

            # 查找父元素中的日期
            parent = a.find_parent(["li", "div", "tr", "td"])
            date = ""
            if parent:
                text = parent.get_text()
                m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
                if m:
                    date = m.group(1)

            detail_url = ""
            if href and href != "javascript:;" and href != "javascript:void(0);":
                detail_url = urljoin("https://ibuy.ccb.com", href)

            items.append({
                "title": title,
                "detail_url": detail_url,
                "publish_date": date,
                "notice_type": self._guess_type(title),
            })

        self.logger.info(f"龙集采 银行广告: {len(items)} 条")
        return items

    # ── 详情页 ──

    def fetch_detail(self, url: str) -> Tuple[str, Optional[bytes]]:
        """抓取详情页（SPA 也用 Playwright）。"""
        if not url:
            return "", None
        html = self._render_page(url, wait_ms=2000)
        return html, None

    def parse_detail(self, html: str, _pdf: Optional[bytes] = None) -> Dict:
        """解析详情页。"""
        if not html:
            return {"title": "", "content_text": "", "purchaser": "", "publish_date": ""}

        soup = BeautifulSoup(html, "html.parser")
        title = ""
        for sel in ["h1", "h2", ".title", "title"]:
            el = soup.select_one(sel)
            if el and len(el.get_text(strip=True)) > 5:
                title = el.get_text(strip=True)
                break

        body = soup.find("body")
        content = body.get_text(separator="\n", strip=True) if body else ""

        purchaser = self._extract_purchaser(content)
        m = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", content)
        publish_date = m.group(1) if m else ""

        return {
            "title": title,
            "purchaser": purchaser,
            "purchaser_level": "总行" if "总行" in (title + content) else "分行",
            "procurement_method": self._extract_method(content),
            "budget": self._extract_budget(content),
            "registration_fee": None,
            "deposit": None,
            "publish_date": publish_date,
            "deadline": self._extract_deadline(content),
            "content_text": content[:50000],
            "city": self._extract_city(title + content),
            "province": "",
        }

    # ── 辅助方法 ──

    @staticmethod
    def _is_bank(title: str) -> bool:
        return any(kw in title for kw in BankAdapter.BANK_KEYWORDS)

    @staticmethod
    def _is_ad(title: str) -> bool:
        return any(kw in title for kw in BankAdapter.AD_KEYWORDS)

    @staticmethod
    def _guess_type(title: str) -> str:
        if "结果" in title or "中标" in title:
            return "中标公告"
        if "征集" in title:
            return "供应商征集"
        if "变更" in title or "更正" in title:
            return "变更公告"
        return "招标公告"

    def _extract_purchaser(self, content: str) -> str:
        m = re.search(r"(?:采购[人方]|招标[人方])[：:]?\s*([^\s，。,\n]{4,40})", content)
        return m.group(1) if m else ""

    def _extract_budget(self, content: str) -> Optional[float]:
        for pat in [r"预算[：:]?\s*(\d+(?:\.\d+)?)\s*万", r"预算金额[：:]?\s*(\d+(?:\.\d+)?)\s*万"]:
            m = re.search(pat, content)
            if m:
                return float(m.group(1))
        return None

    def _extract_deadline(self, content: str) -> str:
        m = re.search(r"(?:截止|投标截止)[：:]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", content)
        return m.group(1) if m else ""

    def _extract_method(self, content: str) -> str:
        for m in ["公开招标", "竞争性磋商", "竞争性谈判", "单一来源", "询价"]:
            if m in content:
                return m
        return "公开招标"

    def _extract_city(self, content: str) -> str:
        cities = ["北京","上海","广州","深圳","天津","重庆","南京","杭州","成都","武汉",
                   "西安","郑州","济南","青岛","沈阳","大连","宁波","厦门","长沙","合肥",
                   "福州","昆明","贵阳","南宁","苏州","无锡","东莞","佛山","珠海","惠州"]
        for c in sorted(cities, key=len, reverse=True):
            if c in content[:500]:
                return c
        return ""

    # ── 主流程 ──

    def run(self, save_to_db: bool = True, **kwargs) -> List[Dict]:
        """遍历所有银行平台采集广告招标。"""
        all_results = []
        self._seen_urls = set()

        for platform in self.PLATFORMS:
            pname = platform["name"]
            purl = platform["url"]
            self.logger.info(f"===== {pname} =====")

            self._report_progress(10, f"正在加载{pname}...")
            html = self._render_page(purl, wait_ms=5000)

            if not html:
                self.logger.warning(f"{pname} 加载失败")
                continue

            self._report_progress(30, f"正在解析{pname}...")
            items = self.parse_list(html)
            self.logger.info(f"{pname} 解析到 {len(items)} 条银行广告")

            for i, item in enumerate(items):
                progress = 30 + (i + 1) * 60 // max(len(items), 1)
                self._report_progress(progress, f"{pname} {i+1}/{len(items)}...")

                url = item.get("detail_url", "")
                if url and url in self._seen_urls:
                    continue
                if url:
                    self._seen_urls.add(url)

                try:
                    html_d, _ = self.fetch_detail(url) if url else ("", None)
                    parsed = self.parse_detail(html_d)
                    parsed["source_url"] = url or purl
                    parsed["notice_type"] = item.get("notice_type", "招标公告")
                    if not parsed["title"]:
                        parsed["title"] = item["title"]

                    record = self._normalize_record(parsed)
                    if record.get("is_ad") or record.get("is_target", False):
                        record["industry_type"] = "银行"
                        record["project_category"] = "营销宣传"
                        all_results.append(record)
                        self.logger.info(f"  ✅ [{pname}] {record['title'][:60]}")

                        if save_to_db:
                            self._save_to_db(record)
                except Exception as e:
                    self.logger.warning(f"  处理失败: {e}")

        self._report_progress(100, f"银行广告采集完成: {len(all_results)} 条")
        self.logger.info(f"===== 银行广告采集完成: {len(all_results)} 条 =====")
        return all_results
