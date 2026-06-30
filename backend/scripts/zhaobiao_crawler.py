"""
标中宝 — 中国招标网 (zhaobiao.cn) 历史招标数据采集脚本

基于 Playwright 浏览器自动化，突破 JS Cookie 挑战反爬。
免费版限制: 最近6个月时间窗口，每次搜索最多 10 页。

用法:
    python scripts/zhaobiao_crawler.py                      # 全部关键词组合采集
    python scripts/zhaobiao_crawler.py --keyword "广东移动 广告"  # 单关键词
    python scripts/zhaobiao_crawler.py --max-pages 3         # 限制翻页
    python scripts/zhaobiao_crawler.py --save-db             # 直接入库
"""

import asyncio
import json
import os
import re
import sys
import time
import hashlib
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from urllib.parse import urljoin, quote

# 添加 backend 到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.keyword_filter import filter_advertisement_projects

logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================

BASE_URL = "https://s.zhaobiao.cn"
SEARCH_URL = f"{BASE_URL}/s"
DETAIL_BASE = "https://zb.zhaobiao.cn"

# 搜索关键词组合（与 historical_crawler/config.py 保持一致）
SEARCH_KEYWORD_COMBOS = [
    # 广告核心类
    "广东移动 广告",
    "广东移动 品牌",
    "广东移动 营销",
    "广东移动 投放",
    "广东移动 新媒体",
    "广东移动 设计",
    "广东移动 制作",
    # 宣传传播类
    "广东移动 宣传",
    "广东移动 新闻",
    "广东移动 传播",
    # 活动会展类
    "广东移动 活动",
    "广东移动 展会",
    "广东移动 展览",
    "广东移动 发布会",
    "广东移动 论坛",
    # 政企党群类
    "广东移动 党群",
    "广东移动 党建",
    "广东移动 集团客户",
    "广东移动 培训",
    # 中国移动广东（备选）
    "中国移动广东 广告",
    "中国移动广东 品牌",
    "中国移动广东 宣传",
    # 通用兜底
    "广东移动 中标",
]

# 输出配置
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
OUTPUT_FILENAME = "zhaobiao_results.json"
CHECKPOINT_FILE = "zhaobiao_checkpoint.json"

# 请求控制
MIN_DELAY = 2.0       # 最小延迟（秒）
MAX_DELAY = 4.0       # 最大延迟（秒）
MAX_PAGES = 10         # 每种关键词最大翻页数

# ============================================================
# 数据结构
# ============================================================

@dataclass
class BiddingItem:
    """招标公告条目"""
    id: str = ""                          # URL MD5 哈希
    title: str = ""
    notice_type: str = ""                 # 招标公告/中标公告/其他公告
    location: str = ""                    # 地点
    publish_date: str = ""                # 发布时间
    detail_url: str = ""                  # 详情页 URL
    source_url: str = ""                  # zb.zhaobiao.cn 链接
    budget: Optional[float] = None        # 预算金额（万元）
    deadline: Optional[str] = None        # 截止日期
    purchaser: str = ""                   # 采购方
    project_category: str = ""            # 赛道分类
    is_ad: bool = False                   # 是否广告类
    matched_keywords: List[str] = field(default_factory=list)
    raw_html: str = ""                    # 详情页 HTML（可选保留）


# ============================================================
# 断点管理器
# ============================================================

class CheckpointManager:
    def __init__(self, checkpoint_path: str):
        self.checkpoint_path = checkpoint_path
        self.processed_urls: Set[str] = set()
        self._load()

    def _load(self):
        if os.path.exists(self.checkpoint_path):
            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.processed_urls = set(data.get("processed_urls", []))
                logger.info(f"📂 加载断点: {len(self.processed_urls)} 条已采集")
            except (json.JSONDecodeError, IOError):
                self.processed_urls = set()

    def is_processed(self, url: str) -> bool:
        return self._hash(url) in self.processed_urls

    def mark_processed(self, url: str):
        self.processed_urls.add(self._hash(url))
        self._save()

    def _hash(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def _save(self):
        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        with open(self.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump({"processed_urls": list(self.processed_urls)}, f, ensure_ascii=False)


# ============================================================
# 爬虫核心
# ============================================================

class ZhaobiaoCrawler:
    """中国招标网 Playwright 爬虫"""

    def __init__(self, max_pages: int = MAX_PAGES):
        self.max_pages = max_pages
        self.results: List[BiddingItem] = []
        self.checkpoint = CheckpointManager(
            os.path.join(OUTPUT_DIR, CHECKPOINT_FILE)
        )
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def _ensure_browser(self):
        """初始化 Playwright 浏览器。"""
        if self.browser is None:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self.browser = await self._pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            self.context = await self.browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )
            self.page = await self.context.new_page()
            logger.info("🌐 Playwright 浏览器已启动")

    async def close(self):
        if self.browser:
            await self.browser.close()
            if hasattr(self, '_pw'):
                await self._pw.stop()

    def _random_delay(self):
        import random
        return random.uniform(MIN_DELAY, MAX_DELAY)

    # ── 搜索 ──

    def _is_gd_mobile(self, title: str, location: str = "") -> bool:
        """判断是否与广东移动相关。"""
        # 剥离 zhaobiao.cn 的 "((XX+XX... 相关在信息中)" 噪音标记
        import re
        clean_title = re.sub(r'\(\([^)]*?相关在信息中\)', '', title).strip()
        text = (clean_title + " " + location).replace(" ", "")

        # 精确匹配：标题/地点含广东移动或地市移动
        exact_kw = ["广东移动", "中国移动广东", "广州移动", "深圳移动",
                     "东莞移动", "佛山移动", "珠海移动", "中山移动", "惠州移动",
                     "汕头移动", "江门移动", "湛江移动", "茂名移动", "肇庆移动",
                     "梅州移动", "汕尾移动", "河源移动", "阳江移动", "清远移动",
                     "潮州移动", "揭阳移动", "云浮移动", "韶关移动",
                     "广东有限公司", "中国移动通信集团广东"]
        for kw in exact_kw:
            if kw.replace(" ", "") in text:
                return True
        # 地点必须在广东
        gd_regions = ["广东", "广州", "深圳", "东莞", "佛山", "珠海", "中山",
                       "惠州", "汕头", "江门", "湛江", "茂名", "肇庆", "梅州",
                       "汕尾", "河源", "阳江", "清远", "潮州", "揭阳", "云浮", "韶关"]
        if not any(r in text for r in gd_regions):
            return False
        # 广东地区 + 广告营销关键词
        ad_kw = ["广告", "品牌", "营销", "宣传", "活动", "设计", "制作", "新媒体",
                 "视频", "直播", "投放", "策划", "创意", "展会", "论坛", "发布会",
                 "党群", "党建", "工会", "培训", "集团客户", "物料"]
        return any(k in text for k in ad_kw)

    async def search(self, keyword: str) -> List[Dict]:
        """
        搜索并提取列表页结果（最近6个月窗口）。

        Returns:
            [{title, notice_type, location, publish_date, detail_url}, ...]
        """
        await self._ensure_browser()
        all_items = []

        # 导航到搜索页
        await self.page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # 输入关键词
        search_input = await self.page.query_selector('input[type="text"]')
        if not search_input:
            logger.error("未找到搜索输入框")
            return []

        await search_input.fill(keyword)
        await asyncio.sleep(0.5)
        await search_input.press("Enter")
        await asyncio.sleep(3)

        # 等待搜索结果加载
        title = await self.page.title()
        logger.info(f"搜索 '{keyword}' → {title}")

        # 点击"最近6月"（扩大时间窗口）
        try:
            six_month = await self.page.query_selector('a:has-text("最近6月")')
            if six_month:
                await six_month.click()
                await asyncio.sleep(2)
                logger.info("已切换至「最近6月」")
        except Exception:
            pass

        # 翻页采集
        raw_count = 0
        for page_num in range(1, self.max_pages + 1):
            if page_num > 1:
                await asyncio.sleep(self._random_delay())

            items = await self._extract_list_items()
            raw_count += len(items)
            logger.info(f"  第 {page_num} 页: 提取 {len(items)} 条")

            if not items:
                break

            for item in items:
                detail_url = item.get("detail_url", "")
                if detail_url and not self.checkpoint.is_processed(detail_url):
                    # 广东移动过滤
                    if self._is_gd_mobile(item.get("title", ""), item.get("location", "")):
                        all_items.append(item)
                    self.checkpoint.mark_processed(detail_url)

            # 翻页
            has_next = await self._go_next_page()
            if not has_next:
                break

        logger.info(f"✅ '{keyword}': {len(all_items)} 条广东移动相关（原始 {raw_count} 条）")
        return all_items

    async def _extract_list_items(self) -> List[Dict]:
        """从当前搜索结果页提取列表项。"""
        # 等待表格加载
        try:
            await self.page.wait_for_selector('table tr', timeout=10000)
            await asyncio.sleep(1)
        except Exception:
            pass

        return await self.page.evaluate("""() => {
            const items = [];
            const seen = new Set();

            // 搜索结果表格 — 标准结构: ""|类型|标题|地点|发布时间
            const rows = document.querySelectorAll('table tr');
            for (const row of rows) {
                const cells = row.querySelectorAll('td');
                if (cells.length < 3) continue;

                // 查找 zb.zhaobiao.cn 链接
                const link = row.querySelector('a[href*="zb.zhaobiao.cn"]');
                if (!link) continue;

                const title = (link.textContent || '').trim();
                const href = link.href || '';

                // 跳过非招标内容
                if (!title || title.length < 5) continue;
                if (href.includes('/login') || href.includes('user.')) continue;

                // 去重
                if (seen.has(href)) continue;
                seen.add(href);

                // 提取各列 (表格结构: 类型|标题|地点|发布时间, cells[0]=类型)
                const noticeType = (cells[0]?.textContent || '').trim();
                const location = cells.length >= 3 ? (cells[2]?.textContent || '').trim() : '';
                const pubDate = cells.length >= 4 ? (cells[3]?.textContent || '').trim() : (cells[cells.length-1]?.textContent || '').trim();

                items.push({
                    title: title,
                    notice_type: noticeType,
                    location: location,
                    publish_date: pubDate,
                    detail_url: href
                });
            }

            // 如果标准表格没找到，尝试 ul/li 结构
            if (items.length === 0) {
                const listContainers = document.querySelectorAll('.search-result, .result-list, .bid-list, ul.list-con, .public-list');
                for (const container of listContainers) {
                    const lis = container.querySelectorAll('li, .item');
                    for (const li of lis) {
                        const link = li.querySelector('a[href*="zb.zhaobiao.cn"]');
                        if (!link) continue;
                        const title = (link.textContent || '').trim();
                        if (title.length < 5) continue;
                        const href = link.href;
                        if (seen.has(href)) continue;
                        seen.add(href);

                        const text = (li.textContent || '').trim();
                        const dateMatch = text.match(/(\\d{4}-\\d{2}-\\d{2})/);
                        items.push({
                            title: title,
                            notice_type: '',
                            location: '',
                            publish_date: dateMatch ? dateMatch[1] : '',
                            detail_url: href
                        });
                    }
                    if (items.length > 0) break;
                }
            }

            return items;
        }""")

    async def _go_next_page(self) -> bool:
        """翻到下一页，返回是否有下一页。"""
        try:
            next_btn = await self.page.query_selector(
                'a:has-text("下一页"), a:has-text(">"), .pagination .next, '
                'a.page-next, a[class*="next"]'
            )
            if next_btn:
                await next_btn.click()
                await asyncio.sleep(2)
                return True
        except Exception:
            pass
        return False

    # ── 详情页 ──

    async def fetch_detail(self, item: Dict) -> Optional[BiddingItem]:
        """抓取详情页并提取字段。"""
        await self._ensure_browser()
        url = item.get("detail_url", "")
        if not url:
            return None

        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1.5)
            detail_data = await self._extract_detail()
        except Exception as e:
            logger.debug(f"详情页抓取失败 {url[:60]}: {e}")
            detail_data = {}

        # 关键词过滤
        title = item.get("title", "")
        content = detail_data.get("content", "")
        filter_result = filter_advertisement_projects(title, content)

        return BiddingItem(
            id=hashlib.md5(url.encode()).hexdigest(),
            title=title,
            notice_type=item.get("notice_type", ""),
            location=item.get("location", ""),
            publish_date=item.get("publish_date", ""),
            detail_url=url,
            source_url=url,
            budget=detail_data.get("budget"),
            deadline=detail_data.get("deadline"),
            purchaser=detail_data.get("purchaser", ""),
            project_category=filter_result.get("category", ""),
            is_ad=filter_result.get("is_ad", False),
            matched_keywords=filter_result.get("matched_keywords", []),
        )

    async def _extract_detail(self) -> Dict:
        """从详情页提取结构化字段。"""
        return await self.page.evaluate("""() => {
            const result = { content: '', budget: null, deadline: null, purchaser: '' };
            const body = document.body?.innerText || '';
            result.content = body.substring(0, 5000);

            // 预算金额提取
            const budgetPatterns = [
                /预算(?:金额|总价)?[：:]\\s*(\\d[\\d,.]*)\\s*万/,
                /采购预算[：:]\\s*(\\d[\\d,.]*)\\s*万/,
                /项目预算[：:]\\s*(\\d[\\d,.]*)\\s*万/,
                /预算(?:金额)?[：:]\\s*(\\d[\\d,.]*)\\s*元/,
            ];
            for (const p of budgetPatterns) {
                const m = body.match(p);
                if (m) {
                    let val = parseFloat(m[1].replace(/,/g, ''));
                    if (p.source.includes('元') && !p.source.includes('万元')) {
                        val = val / 10000; // 元转万元
                    }
                    result.budget = Math.round(val * 100) / 100;
                    break;
                }
            }

            // 截止日期提取
            const deadlinePatterns = [
                /投标截止(?:时间|日期)?[：:]\\s*(\\d{4}[-/]\\d{1,2}[-/]\\d{1,2})/,
                /响应文件递交截止[：:]\\s*(\\d{4}[-/]\\d{1,2}[-/]\\d{1,2})/,
                /开标时间[：:]\\s*(\\d{4}[-/]\\d{1,2}[-/]\\d{1,2})/,
                /递交截止[：:]\\s*(\\d{4}[-/]\\d{1,2}[-/]\\d{1,2})/,
            ];
            for (const p of deadlinePatterns) {
                const m = body.match(p);
                if (m) { result.deadline = m[1]; break; }
            }

            // 采购方提取
            const purchaserMatch = body.match(
                /(?:采购人|采购单位|招标人|招标单位)[：:]\\s*([^\\n]{4,40})/
            );
            if (purchaserMatch) {
                result.purchaser = purchaserMatch[1].trim();
            }

            return result;
        }""")

    # ── 主流程 ──

    async def run(
        self,
        keywords: Optional[List[str]] = None,
        fetch_details: bool = True,
        ad_filter: bool = True,
    ) -> List[BiddingItem]:
        """
        执行完整采集流程。

        Args:
            keywords: 关键词列表，默认使用全部 SEARCH_KEYWORD_COMBOS
            fetch_details: 是否抓取详情页
            ad_filter: 是否只保留广告类结果

        Returns:
            采集结果列表
        """
        if keywords is None:
            keywords = SEARCH_KEYWORD_COMBOS

        logger.info("=" * 60)
        logger.info(f"🕷️ 标中宝 - zhaobiao.cn 采集启动")
        logger.info(f"  关键词组合: {len(keywords)} 组")
        logger.info(f"  翻页上限:   {self.max_pages} 页/关键词")
        logger.info(f"  详情抓取:   {'ON' if fetch_details else 'OFF'}")
        logger.info(f"  广告过滤:   {'ON' if ad_filter else 'OFF'}")
        logger.info(f"  预估总量:   ~{len(keywords) * self.max_pages * 20} 条（去重前）")
        logger.info("=" * 60)

        all_list_items = []

        for i, kw in enumerate(keywords):
            logger.info(f"\n[{i+1}/{len(keywords)}] 搜索: {kw}")
            try:
                items = await self.search(kw)
                all_list_items.extend(items)
                logger.info(f"  累计列表项: {len(all_list_items)}")
            except Exception as e:
                logger.error(f"  搜索失败: {e}")

            if i < len(keywords) - 1:
                await asyncio.sleep(self._random_delay())

        logger.info(f"\n📋 列表采集完成: {len(all_list_items)} 条（去重后）")

        if not fetch_details:
            self.results = [
                BiddingItem(
                    id=hashlib.md5(it.get("detail_url", "").encode()).hexdigest(),
                    title=it.get("title", ""),
                    notice_type=it.get("notice_type", ""),
                    location=it.get("location", ""),
                    publish_date=it.get("publish_date", ""),
                    detail_url=it.get("detail_url", ""),
                    source_url=it.get("detail_url", ""),
                )
                for it in all_list_items
            ]
            self._save_results()
            return self.results

        # 抓取详情页
        logger.info(f"\n📄 开始抓取详情页...")
        detail_count = 0
        for i, item in enumerate(all_list_items):
            detail = await self.fetch_detail(item)
            if detail:
                self.results.append(detail)
                detail_count += 1

            if (i + 1) % 10 == 0:
                logger.info(f"  详情进度: {i+1}/{len(all_list_items)}")

            if i < len(all_list_items) - 1:
                await asyncio.sleep(self._random_delay() * 0.5)

        logger.info(f"  详情抓取完成: {detail_count} 条")

        # 广告过滤
        if ad_filter:
            before = len(self.results)
            self.results = [r for r in self.results if r.is_ad]
            logger.info(f"🔍 广告过滤: {before} → {len(self.results)} 条")

        self._save_results()
        self._print_stats()
        return self.results

    def _save_results(self):
        """保存结果到 JSON 文件。"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

        data = {
            "crawl_time": datetime.now().isoformat(),
            "total": len(self.results),
            "source": "zhaobiao.cn",
            "items": [
                {
                    "title": r.title,
                    "notice_type": r.notice_type,
                    "location": r.location,
                    "publish_date": r.publish_date,
                    "detail_url": r.detail_url,
                    "budget": r.budget,
                    "deadline": r.deadline,
                    "purchaser": r.purchaser,
                    "project_category": r.project_category,
                    "is_ad": r.is_ad,
                    "matched_keywords": r.matched_keywords,
                }
                for r in self.results
            ],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 结果已保存: {output_path} ({len(self.results)} 条)")

    def _print_stats(self):
        """打印采集统计。"""
        if not self.results:
            return

        categories = {}
        for r in self.results:
            cat = r.project_category or "未分类"
            categories[cat] = categories.get(cat, 0) + 1

        logger.info("\n📊 采集统计:")
        logger.info(f"  总计: {len(self.results)} 条广告类招标项目")
        logger.info("  赛道分布:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            logger.info(f"    {cat}: {count} 条")


# ============================================================
# 入口
# ============================================================

async def main():
    parser = argparse.ArgumentParser(description="标中宝 - zhaobiao.cn 招标数据采集")
    parser.add_argument("--keyword", type=str, help="单关键词搜索")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES, help="最大翻页数")
    parser.add_argument("--no-details", action="store_true", help="跳过详情页抓取")
    parser.add_argument("--no-filter", action="store_true", help="不过滤广告类")
    parser.add_argument("--list-only", action="store_true", help="仅列表不抓详情")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    keywords = [args.keyword] if args.keyword else None

    async with ZhaobiaoCrawler(max_pages=args.max_pages) as crawler:
        results = await crawler.run(
            keywords=keywords,
            fetch_details=not args.no_details and not args.list_only,
            ad_filter=not args.no_filter,
        )

    print(f"\n✅ 采集完成！共获取 {len(results)} 条广告类招标项目")
    print(f"📁 结果文件: {os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)}")


if __name__ == "__main__":
    asyncio.run(main())
